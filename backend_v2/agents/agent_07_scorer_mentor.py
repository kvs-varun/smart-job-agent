"""
Agent 7 — Resume Scorer & Mentor Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Senior HR Mentor. Awards a precise 0–10 score across 5 dimensions and
recommends the most relevant FREE learning resources for the candidate's domain.

Model: claude-sonnet-4-6 (deep analysis + domain knowledge)
Scoring dimensions: ATS Compliance (2.0) + Content Quality (2.5) + Skill Alignment (2.0)
                  + Profile Strength (2.0) + Presentation (1.5) = 10.0
"""
import json
import logging

from backend_v2.agents.tools.gemini_client import gemini_json

from backend_v2.agents.state import AgentState, AGENT_SCORER, HEALTH_OK, HEALTH_FAILED
from backend_v2.agents.tools.resume_tools import check_quality_async, compute_match_scores_async
from backend_v2.agents.tools.kb_tools import infer_role, get_ats_keywords
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Senior HR Mentor with 20 years of experience hiring for Indian IT companies
(TCS, Infosys, Flipkart, Razorpay, Google India) and global product firms.

SCORING RUBRIC (total 10.0 points):

1. ATS_COMPLIANCE (max 2.0):
   - 2.0: Perfect format, all sections present, parseable contact, no tables/columns
   - 1.5: Minor issues (1-2 missing sections, slightly dense)
   - 1.0: Multiple issues (missing sections, questionable formatting)
   - 0.5: Likely to fail ATS parsing

2. CONTENT_QUALITY (max 2.5):
   - 2.5: All bullets with action verbs, STAR format, quantified where possible
   - 2.0: Most bullets strong, 1-2 weak ones
   - 1.5: 50% weak bullets, generic descriptions
   - 1.0: Most bullets are passive/vague ("was responsible for", "helped with")
   - 0.5: No structure to experience descriptions

3. SKILL_ALIGNMENT (max 2.0):
   - 2.0: Strong match to target role, all must-haves present
   - 1.5: Most must-haves present, few gaps
   - 1.0: Partial match, significant gaps for the inferred role
   - 0.5: Poor alignment to any recognizable tech role

4. PROFILE_STRENGTH (max 2.0):
   - 2.0: GitHub present + active, LinkedIn, 3+ strong projects, certifications
   - 1.5: GitHub + 2 projects or LinkedIn + projects
   - 1.0: Projects present but thin, no GitHub/LinkedIn
   - 0.5: Minimal projects, no online presence signals

5. PRESENTATION (max 1.5):
   - 1.5: Concise (< 420 words), clean structure, no fluff, one page
   - 1.0: Mostly clean but slightly wordy or inconsistent
   - 0.5: Too long, repetitive, or poorly structured

FREE RESOURCE RECOMMENDATIONS:
Only recommend resources you can verify are genuinely free (no trial required):
- Coursera free audit (not paid certificate)
- Google Cloud Skills Boost (free tier)
- AWS Skill Builder (free tier)
- Kaggle Learn courses (100% free)
- DeepLearning.ai free courses on Coursera
- NPTEL courses (India — completely free)
- freeCodeCamp (100% free)
- The Odin Project (free)
- Flutter official codelabs (free)
- MongoDB University (free)
- Scrimba (free tier)
- MIT OpenCourseWare (free)
- CS50 Harvard (free audit)

Match resources to the candidate's SPECIFIC gaps and domain.

Output JSON with: total_score, breakdown{}, mentor_feedback, recommendations[], domain, improvement_priority[]"""

# Curated free resources database per domain and skill gap
FREE_RESOURCES_DB = {
    "python": {"title": "Python for Everybody", "url": "https://www.coursera.org/specializations/python", "provider": "Coursera (free audit)", "duration_hours": 20, "free": True},
    "dsa": {"title": "Data Structures & Algorithms", "url": "https://www.coursera.org/specializations/data-structures-algorithms", "provider": "Coursera (free audit)", "duration_hours": 40, "free": True},
    "sql": {"title": "SQL for Data Science", "url": "https://www.coursera.org/learn/sql-for-data-science", "provider": "Coursera (free audit)", "duration_hours": 10, "free": True},
    "machine_learning": {"title": "Machine Learning Specialization", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "provider": "DeepLearning.ai (free audit)", "duration_hours": 60, "free": True},
    "deep_learning": {"title": "Deep Learning Specialization", "url": "https://www.coursera.org/specializations/deep-learning", "provider": "DeepLearning.ai (free audit)", "duration_hours": 80, "free": True},
    "aws": {"title": "AWS Cloud Practitioner Essentials", "url": "https://explore.skillbuilder.aws/learn/course/external/view/elearning/134/aws-cloud-practitioner-essentials", "provider": "AWS Skill Builder (free)", "duration_hours": 6, "free": True},
    "docker": {"title": "Docker & Kubernetes Fundamentals", "url": "https://www.kaggle.com/learn", "provider": "Kaggle Learn (free)", "duration_hours": 5, "free": True},
    "react": {"title": "The Odin Project — React Path", "url": "https://www.theodinproject.com/paths/full-stack-javascript", "provider": "The Odin Project (free)", "duration_hours": 50, "free": True},
    "flutter": {"title": "Flutter Codelabs", "url": "https://docs.flutter.dev/codelabs", "provider": "Flutter Official (free)", "duration_hours": 15, "free": True},
    "data_science": {"title": "Data Science with Python — NPTEL", "url": "https://nptel.ac.in/courses/106/106/106106212/", "provider": "NPTEL (free, Indian IITs)", "duration_hours": 30, "free": True},
    "web_dev": {"title": "Responsive Web Design", "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "provider": "freeCodeCamp (free)", "duration_hours": 20, "free": True},
    "nlp": {"title": "Natural Language Processing Specialization", "url": "https://www.coursera.org/specializations/natural-language-processing", "provider": "DeepLearning.ai (free audit)", "duration_hours": 50, "free": True},
    "git": {"title": "Version Control with Git", "url": "https://www.coursera.org/learn/version-control-with-git", "provider": "Atlassian/Coursera (free audit)", "duration_hours": 8, "free": True},
    "system_design": {"title": "System Design for Interviews", "url": "https://www.youtube.com/playlist?list=PLMCXHnjXnTnvo6alSjVkgxV-VH6EPyvoX", "provider": "YouTube (free)", "duration_hours": 10, "free": True},
    "cs50": {"title": "CS50: Introduction to Computer Science", "url": "https://cs50.harvard.edu/x/", "provider": "Harvard (free audit)", "duration_hours": 50, "free": True},
    "mongodb": {"title": "MongoDB Basics", "url": "https://learn.mongodb.com/learning-paths/introduction-to-mongodb", "provider": "MongoDB University (free)", "duration_hours": 8, "free": True},
}


async def run(state: AgentState) -> AgentState:
    """
    Agent 7 node function.
    Input: final_resume, jd_match_details
    Output: resume_score (0-10), score_breakdown, mentor_feedback, mentor_recommendations
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 7 — Scorer] Starting | session={session_id}")

    try:
        resume = state.get("final_resume") or state.get("enhanced_resume") or state.get("parsed_resume", {})
        if not resume:
            raise ValueError("No resume data for scoring")

        jd_match = state.get("jd_match_details") or {}
        missing_skills = jd_match.get("missing_skills", [])

        # ── 1. Rule-based baseline from V1 quality gate ───────────────────────
        quality = await check_quality_async(resume, jd_match or None)
        ats_baseline = quality.get("ats_score", 0) / 100  # normalize 0-1
        role_key = infer_role(state.get("job_description", "") or " ".join(resume.get("skills", [])))

        # Build resume text for LLM
        summary = resume.get("summary", "")
        skills = resume.get("skills", [])
        experience = resume.get("experience", [])
        projects = resume.get("projects", [])
        education = resume.get("education", [])
        contact = resume.get("contact", {})

        skills_str = ", ".join(str(s) for s in skills[:20]) if isinstance(skills, list) else str(skills)
        bullets_sample = []
        for exp in experience[:2]:
            desc = exp.get("description", "")
            bullets_sample.extend(desc.split("\n")[:3])
        for proj in projects[:2]:
            bullets_sample.append(proj.get("description", "")[:100])

        user_prompt = f"""Score this resume with brutal honesty on all 5 dimensions.

CANDIDATE PROFILE:
- Skills: {skills_str}
- Summary: {summary[:300] if summary else 'Not provided'}
- Experience: {len(experience)} roles
- Projects: {len(projects)} projects
- Education: {(education[0].get('institution', '') + ' ' + education[0].get('grade', '')) if education else 'Not provided'}
- GitHub present: {bool(contact.get('github'))}
- LinkedIn present: {bool(contact.get('linkedin'))}

SAMPLE BULLETS:
{chr(10).join(bullets_sample[:6])}

ATS QUALITY GATE RESULT: {quality.get('passed', False)} (score: {ats_baseline * 100:.0f}/100)
ATS ISSUES: {', '.join(quality.get('issues', [])[:5])}

ROLE INFERRED: {role_key}
JD MATCH SCORE: {state.get('jd_match_score', 'N/A')}
MISSING SKILLS: {', '.join(missing_skills[:8])}

Score each dimension with 1 decimal precision. Be honest — inflated scores don't help the candidate.

Output JSON:
{{
  "total_score": <float 0.0-10.0>,
  "breakdown": {{
    "ats_compliance": <0.0-2.0>,
    "content_quality": <0.0-2.5>,
    "skill_alignment": <0.0-2.0>,
    "profile_strength": <0.0-2.0>,
    "presentation": <0.0-1.5>
  }},
  "mentor_feedback": "<2-3 sentences of honest, actionable feedback from a senior HR perspective>",
  "domain": "{role_key}",
  "improvement_priority": ["highest priority fix", "second priority", "third priority"],
  "skill_gaps_for_resources": ["skill1", "skill2", "skill3"]
}}"""

        response_data = await gemini_json(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_heavy,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
        )

        # If LLM parse failed, build rule-based fallback scoring
        if response_data.get("_parse_error") or "total_score" not in response_data:
            logger.warning("[Agent 7] LLM parse error — using rule-based scoring")
            ats_score = ats_baseline * 2.0  # scale 0-1 → 0-2
            skill_score = min(2.0, len(resume.get("skills", [])) / 10)
            proj_score = min(2.0, len(resume.get("projects", [])) * 0.5)
            content_score = 1.5  # neutral
            pres_score = 1.0 if len(experience) > 0 else 0.5
            fallback_total = round(ats_score + content_score + skill_score + proj_score + pres_score, 1)
            response_data = {
                "total_score": min(10.0, fallback_total),
                "breakdown": {
                    "ats_compliance": round(ats_score, 1),
                    "content_quality": content_score,
                    "skill_alignment": round(skill_score, 1),
                    "profile_strength": round(proj_score, 1),
                    "presentation": pres_score,
                },
                "mentor_feedback": "Rule-based scoring applied. Add strong action verbs, quantify achievements, and ensure your resume is ATS-friendly for a higher score.",
                "domain": role_key,
                "improvement_priority": ["Add quantified achievements", "Strengthen action verbs", "Complete GitHub and LinkedIn profiles"],
                "skill_gaps_for_resources": missing_skills[:3],
            }

        result = response_data

        # ── 2. Map skill gaps to free resources ───────────────────────────────
        skill_gaps = result.get("skill_gaps_for_resources", missing_skills[:5])
        recommendations = _get_free_resources(skill_gaps, role_key, result.get("domain", role_key))

        total_score = float(result.get("total_score", 5.0))
        breakdown = result.get("breakdown", {})
        mentor_feedback = result.get("mentor_feedback", "")

        logger.info(
            f"[Agent 7 — Scorer] Complete | session={session_id} "
            f"| score={total_score:.1f}/10"
        )

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_SCORER] = HEALTH_OK
        return {
            "resume_score": total_score,
            "score_breakdown": breakdown,
            "mentor_feedback": mentor_feedback,
            "mentor_recommendations": recommendations,
            "agent_health_map": health_map,
        }

    except Exception as exc:
        logger.error(f"[Agent 7 — Scorer] FAILED: {exc}", exc_info=True)
        # Fallback: rule-based ATS score
        try:
            resume = state.get("final_resume") or state.get("parsed_resume") or {}
            quality = await check_quality_async(resume)
            ats_raw = quality.get("ats_score", 50)
            ats_score = min(2.0, ats_raw / 50)  # 0-100 → 0-2
            skills = resume.get("skills", []) if isinstance(resume, dict) else []
            projects = resume.get("projects", []) if isinstance(resume, dict) else []
            skill_score = min(2.0, len(skills) / 10)
            proj_score = min(2.0, len(projects) * 0.5)
            fallback_total = round(ats_score + 1.5 + skill_score + proj_score + 1.0, 1)
            fallback_score = min(10.0, fallback_total)
            fallback_breakdown = {
                "ats_compliance": round(ats_score, 1),
                "content_quality": 1.5,
                "skill_alignment": round(skill_score, 1),
                "profile_strength": round(proj_score, 1),
                "presentation": 1.0,
            }
        except Exception:
            fallback_score = 5.0
            fallback_breakdown = {
                "ats_compliance": 1.0, "content_quality": 1.5,
                "skill_alignment": 1.0, "profile_strength": 1.0, "presentation": 0.5,
            }

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_SCORER] = HEALTH_FAILED
        return {
            "resume_score": fallback_score,
            "score_breakdown": fallback_breakdown,
            "mentor_feedback": "Unable to generate detailed feedback. Ensure your resume has strong action verbs, quantified achievements, and includes GitHub and LinkedIn links.",
            "mentor_recommendations": [],
            "agent_health_map": health_map,
        }


def _get_free_resources(skill_gaps: list, role_key: str, domain: str) -> list[dict]:
    """Map skill gaps to curated free resources."""
    recs = []
    seen_urls = set()

    # Normalize skill names to resource keys
    skill_key_map = {
        "python": "python", "java": "cs50", "javascript": "web_dev",
        "react": "react", "flutter": "flutter", "docker": "docker",
        "aws": "aws", "machine learning": "machine_learning", "ml": "machine_learning",
        "deep learning": "deep_learning", "dl": "deep_learning",
        "nlp": "nlp", "natural language processing": "nlp",
        "sql": "sql", "mongodb": "mongodb", "git": "git",
        "data structures": "dsa", "algorithms": "dsa", "dsa": "dsa",
        "system design": "system_design", "data science": "data_science",
    }

    for skill in skill_gaps:
        skill_lower = skill.lower().strip()
        resource_key = skill_key_map.get(skill_lower)
        if not resource_key:
            # Fuzzy match
            for k in skill_key_map:
                if k in skill_lower or skill_lower in k:
                    resource_key = skill_key_map[k]
                    break

        if resource_key and resource_key in FREE_RESOURCES_DB:
            resource = dict(FREE_RESOURCES_DB[resource_key])
            if resource["url"] not in seen_urls:
                resource["skill_gap"] = skill
                resource["relevance_score"] = 0.9
                recs.append(resource)
                seen_urls.add(resource["url"])

    # Always add domain-specific resource
    domain_resource_map = {
        "backend_fresher": FREE_RESOURCES_DB["dsa"],
        "frontend_fresher": FREE_RESOURCES_DB["web_dev"],
        "flutter_fresher": FREE_RESOURCES_DB["flutter"],
        "data_fresher": FREE_RESOURCES_DB["data_science"],
    }
    domain_rec = domain_resource_map.get(role_key)
    if domain_rec and domain_rec["url"] not in seen_urls:
        rec = dict(domain_rec)
        rec["skill_gap"] = "domain_foundation"
        rec["relevance_score"] = 0.8
        recs.append(rec)

    # Cap at 5 recommendations
    return recs[:5]
