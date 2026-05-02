"""
Agent 3 — JD Match Strategist Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: The most intelligent agent in the system. Acts as a master hiring strategist.
Performs deep JD-resume alignment analysis with brutally honest probability assessment.
Issues CAUTION for low-match scenarios (< 60%). Still helps if candidate proceeds.

Model: claude-sonnet-4-6 (deepest reasoning required)
"""
import json
import logging

from backend_v2.agents.tools.gemini_client import gemini_json

from backend_v2.agents.state import AgentState, AGENT_JD_MATCH, HEALTH_OK, HEALTH_FAILED
from backend_v2.agents.tools.resume_tools import (
    analyze_job_async,
    compute_match_scores_async,
)
from backend_v2.agents.tools.kb_tools import infer_role, get_indian_hiring_patterns
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

CAUTION_THRESHOLD = 60.0   # Below this → issue CAUTION warning

SYSTEM_PROMPT = """You are the world's most experienced AI hiring strategist with deep knowledge of:
- Indian IT recruitment at TCS, Infosys, Wipro, Cognizant (service companies)
- Product companies: Razorpay, CRED, Zepto, Meesho, Swiggy, Ola
- FAANG India: Google, Microsoft, Amazon, Meta, Apple
- Global remote companies, startups, and consulting firms

You perform surgical JD-resume matching and give BRUTALLY HONEST assessments.

YOUR ANALYSIS FRAMEWORK:

1. HARD REQUIREMENTS CHECK: Identify mandatory requirements from JD (years of experience,
   specific technologies marked as "required" or "must have"). Flag any the candidate lacks.

2. SKILL ALIGNMENT SCORE:
   - Primary skills match (60% weight): must-have technologies present in resume
   - Secondary skills match (30% weight): good-to-have technologies
   - Cultural fit signals (10% weight): project scale, work style, domain keywords

3. EXPERIENCE GAP ANALYSIS: Is the required experience level realistic for this candidate?
   Freshers applying to senior roles, wrong domain, etc.

4. INDIAN MARKET SPECIFIC:
   - TCS/Infosys/Wipro: check CGPA (they often require >60% / >6.0), batch year
   - Startups: look for problem-solving signals, project scale, GitHub activity
   - Product companies: look for DS&A signals, system design concepts, open source

5. CAUTION THRESHOLD: If overall match < 60%, issue a CAUTION with:
   - Exact probability estimate of getting a callback (honest, not discouraging)
   - Top 3 hard gaps that will cause automatic rejection
   - Whether to proceed recommendation (not a refusal — candidate decides)

6. TAILORING PLAN: Regardless of score, provide specific steps to maximize this application:
   - Which keywords to naturally integrate
   - Which project to highlight most prominently
   - Summary rewrite suggestion targeting this specific JD

Output JSON with: match_score (0-100), skill_match_pct, keyword_coverage_pct,
matched_skills[], missing_skills[], hard_gaps[], caution_issued (bool),
callback_probability_pct (honest estimate), caution_message (if applicable),
tailoring_plan[], recommendations[]"""


async def run(state: AgentState) -> AgentState:
    """
    Agent 3 node function for LangGraph.
    Input: final_resume, job_description
    Output: jd_match_score, jd_match_details, caution_issued, tailoring_plan
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 3 — JD Strategist] Starting | session={session_id}")

    try:
        final_resume = state.get("final_resume") or state.get("enhanced_resume") or state.get("tailored_resume")
        jd_text = state.get("job_description", "")

        if not jd_text:
            logger.info("[Agent 3] No JD provided — skipping match analysis")
            health_map = dict(state.get("agent_health_map") or {})
            health_map[AGENT_JD_MATCH] = HEALTH_OK
            return {"agent_health_map": health_map}

        if not final_resume:
            raise ValueError("No resume data for JD matching")

        # ── 1. V1 rule-based scoring (fast baseline, always runs) ────────────────
        role_key = infer_role(jd_text)
        baseline_score = 0.0
        matched: list = []
        missing: list = []
        scores: dict = {}
        try:
            job_analysis = await analyze_job_async(jd_text, role_key)
            scores = await compute_match_scores_async(final_resume, job_analysis)
            matched = scores.get("matched_skills", [])
            missing = scores.get("missing_skills", [])
            raw_score = float(scores.get("overall_score", 0))
            if raw_score == 0.0 and matched:
                # V1 tool returned matched skills but overall_score is 0 — compute from ratio
                total = len(matched) + len(missing)
                raw_score = len(matched) / total if total > 0 else 0.0
            baseline_score = raw_score * 100
        except Exception as exc_baseline:
            logger.warning(f"[Agent 3] Rule-based baseline failed: {exc_baseline}")

        def _rule_based_report() -> dict:
            return {
                "match_score": baseline_score,
                "skill_match_pct": float(scores.get("skill_match_pct", baseline_score)),
                "keyword_coverage_pct": baseline_score,
                "matched_skills": matched,
                "missing_skills": missing,
                "hard_gaps": missing[:3],
                "caution_issued": baseline_score < CAUTION_THRESHOLD,
                "callback_probability_pct": baseline_score * 0.8,
                "caution_message": (
                    f"Match score {baseline_score:.0f}% is below the recommended 60% threshold. "
                    "Consider strengthening your skills before applying."
                    if baseline_score < CAUTION_THRESHOLD else None
                ),
                "company_type": "unknown",
                "tailoring_plan": [],
                "recommendations": [f"Add {s} to your resume" for s in missing[:3]],
                "strengths": matched[:3],
                "verdict": f"Rule-based analysis: {baseline_score:.0f}% skill match to JD requirements.",
            }

        # ── 2. LLM deep analysis ──────────────────────────────────────────────
        resume_text = _resume_to_plain_text(final_resume)

        user_prompt = f"""Perform a deep JD-resume match analysis.

JOB DESCRIPTION:
{jd_text[:2000]}

CANDIDATE RESUME:
{resume_text[:2000]}

BASELINE SCORE FROM RULE-BASED ANALYSIS: {baseline_score:.1f}/100
MATCHED SKILLS (rule-based): {', '.join(matched[:15])}
MISSING SKILLS (rule-based): {', '.join(missing[:10])}

INDIAN MARKET CONTEXT:
- Check if company is service (TCS/Infosys style) vs product vs startup
- Service companies: CGPA check, batch year check, communication skills
- Product/startup: technical depth, project impact, problem-solving signals

Return compact JSON (keep each string value under 100 chars):
{{
  "match_score": <0-100>,
  "skill_match_pct": <0-100>,
  "keyword_coverage_pct": <0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "hard_gaps": ["gap1", "gap2"],
  "caution_issued": <true if match_score < 60>,
  "callback_probability_pct": <0-100>,
  "caution_message": "<brief if caution, else null>",
  "company_type": "service|product|startup|unknown",
  "tailoring_plan": [{{"action": "...", "section": "...", "specific_change": "..."}}],
  "recommendations": ["rec1", "rec2"],
  "strengths": ["strength1", "strength2"],
  "verdict": "<1 sentence summary>"
}}"""

        report = _rule_based_report()  # default to rule-based
        try:
            llm_report = await gemini_json(
                api_key=settings.gemini_api_key,
                model_name=settings.llm_model_fast,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=2048,
                disable_thinking=True,
            )
            if not llm_report.get("_parse_error") and "match_score" in llm_report:
                report = llm_report
            else:
                logger.warning("[Agent 3] LLM parse error — using rule-based scores only")
        except Exception as exc_llm:
            logger.warning(f"[Agent 3] LLM call failed: {exc_llm} — using rule-based scores")

        match_score = float(report.get("match_score", baseline_score))
        caution_issued = match_score < CAUTION_THRESHOLD or bool(report.get("caution_issued", False))

        logger.info(
            f"[Agent 3 — JD Strategist] Complete | session={session_id} "
            f"| score={match_score:.1f} | caution={caution_issued}"
        )

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_JD_MATCH] = HEALTH_OK
        return {
            "jd_match_score": match_score,
            "jd_match_details": report,
            "caution_issued": caution_issued,
            "tailoring_plan": report.get("tailoring_plan", []),
            "agent_health_map": health_map,
        }

    except Exception as exc:
        logger.error(f"[Agent 3 — JD Strategist] FAILED: {exc}", exc_info=True)
        fallback_report = {
            "match_score": 0.0, "skill_match_pct": 0.0, "keyword_coverage_pct": 0.0,
            "matched_skills": [], "missing_skills": [], "hard_gaps": [],
            "caution_issued": True, "callback_probability_pct": 0.0,
            "caution_message": "Could not complete JD analysis. Please retry.",
            "company_type": "unknown", "tailoring_plan": [], "recommendations": [],
            "strengths": [], "verdict": "Analysis unavailable due to error.",
        }
        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_JD_MATCH] = HEALTH_FAILED
        return {
            "jd_match_score": 0.0,
            "jd_match_details": fallback_report,
            "caution_issued": True,
            "tailoring_plan": [],
            "agent_health_map": health_map,
        }


def _resume_to_plain_text(resume: dict) -> str:
    """Convert resume JSON to readable plain text for LLM analysis."""
    parts = []
    c = resume.get("contact", {})
    if c.get("name"):
        parts.append(f"Name: {c['name']} | Role: {c.get('jobTitle', '')}")

    if resume.get("summary"):
        parts.append(f"Summary: {resume['summary']}")

    if resume.get("skills"):
        skills = resume["skills"]
        if isinstance(skills, list):
            parts.append(f"Skills: {', '.join(str(s) for s in skills[:30])}")

    for exp in resume.get("experience", [])[:3]:
        parts.append(
            f"Experience: {exp.get('title', '')} at {exp.get('company', '')} "
            f"({exp.get('startDate', '')}–{exp.get('endDate', 'Present')}) | "
            f"{exp.get('description', '')[:200]}"
        )

    for proj in resume.get("projects", [])[:3]:
        tech = proj.get("techStack", [])
        tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
        parts.append(
            f"Project: {proj.get('name', '')} | Tech: {tech_str} | "
            f"{proj.get('description', '')[:150]}"
        )

    for edu in resume.get("education", [])[:2]:
        parts.append(
            f"Education: {edu.get('degree', '')} in {edu.get('field', '')} "
            f"from {edu.get('institution', '')} | Grade: {edu.get('grade', '')}"
        )

    return "\n".join(parts)
