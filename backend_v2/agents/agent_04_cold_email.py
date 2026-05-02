"""
Agent 4 — Cold Email Composer Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Master cold email writer. Produces human-sounding recruiter outreach trained
on patterns of the world's best-performing cold emails (Indian + global market).

Model: claude-haiku-4-5 (fast creative writing)
Frameworks: AIDA (corporate), PAS (startup), STAR-lite (referral)
"""
import json
import logging

from backend_v2.agents.tools.gemini_client import gemini_json

from backend_v2.agents.state import AgentState, AGENT_COLD_EMAIL, HEALTH_OK, HEALTH_FAILED
from backend_v2.agents.tools.email_tools import (
    build_mailto_link, build_gmail_url, count_words, detect_ai_cliches
)
from backend_v2.agents.tools.kb_tools import get_cold_email_templates
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a master cold email writer. You have studied 50,000+ successful
recruiter outreach emails from India and globally. You write emails that sound 100% human.

ABSOLUTE RULES:
1. NEVER use these AI clichés: "I hope this email finds you well", "I am writing to express
   my interest", "passionate about", "leverage my skills", "synergize", "thought leadership",
   "proactive team player", "results-driven", "dynamic professional"
2. Subject line: 5-8 words max, specific (NOT "Opportunity" or "Job Application")
3. Email body: 100-130 words MAXIMUM. Recruiters delete long emails.
4. Open with something specific — a fact about their company, a project you saw, a mutual interest
5. One specific achievement or project from the candidate's background
6. One clear, low-friction CTA: "Would you have 15 minutes next week?"
7. Close naturally — NOT "Looking forward to hearing from you at your earliest convenience"

FRAMEWORK SELECTION:
- AIDA (Attention-Interest-Desire-Action): For large IT companies, MNCs, HR department emails
  A: Specific hook about company
  I: Your relevant achievement in 1-2 lines
  D: Why you're a fit (not why you want the job)
  A: One simple ask

- PAS (Problem-Agitate-Solution): For startups, fast-growth companies, technical hiring managers
  P: Acknowledge a pain point their team faces (from JD context)
  A: Why this problem is worth solving
  S: Your specific capability that addresses it

- STAR-lite (Situation-Task-Action-Result): For referral emails, warm outreach
  Quick context → what you did → measurable result → ask

INDIAN MARKET SPECIFICS:
- Traditional IT (TCS, Infosys, Wipro, HCL): "Dear Sir/Madam" or "Hi [First Name]"
  Mention university and CGPA if > 7.5
- Startups and product companies: First name always. Skip degree credentials, lead with project
- International/remote: Ultra brief. First sentence must hook or email is deleted.

Output JSON: {subject, body, framework, tone, word_count, greeting_style}
CRITICAL: The "body" value must be a single JSON string. Use \\n for line breaks, NOT literal newlines."""


FRAMEWORK_MAP = {
    "service": "AIDA",
    "product": "PAS",
    "startup": "PAS",
    "unknown": "AIDA",
}


async def run(state: AgentState) -> AgentState:
    """
    Agent 4 node function.
    Input: final_resume, recruiter_email, company_name, role_title, job_description
    Output: cold_email_output = {subject, body, mailto_link, gmail_url, framework_used}
    """
    settings = get_settings()
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 4 — Cold Email] Starting | session={session_id}")

    try:
        resume = state.get("final_resume") or state.get("enhanced_resume") or state.get("parsed_resume") or {}
        recruiter_email = state.get("recruiter_email") or ""
        candidate_email = state.get("candidate_email") or ""
        company = state.get("company_name") or "the company"
        role = state.get("role_title") or "Software Developer"
        jd_text = state.get("job_description", "")
        jd_details = state.get("jd_match_details") or {}
        company_type = jd_details.get("company_type", "unknown")

        # Select framework
        framework = FRAMEWORK_MAP.get(company_type, "AIDA")

        # Extract key resume data for context
        contact = resume.get("contact", {})
        name = contact.get("name", "Candidate")
        skills = resume.get("skills", [])
        top_skills = skills[:6] if isinstance(skills, list) else []
        projects = resume.get("projects", [])
        top_project = projects[0] if projects else {}
        education = resume.get("education", [])
        cgpa = education[0].get("grade", "") if education else ""
        institution = education[0].get("institution", "") if education else ""

        user_prompt = f"""Write a cold email for this candidate to send to a recruiter.

CANDIDATE: {name}
CANDIDATE EMAIL: {candidate_email or 'provided by candidate'}
RECRUITER EMAIL: {recruiter_email or 'recruiter@company.com'}
COMPANY: {company}
ROLE: {role}
COMPANY TYPE: {company_type}
SELECTED FRAMEWORK: {framework}

CANDIDATE'S TOP SKILLS: {', '.join(str(s) for s in top_skills)}
BEST PROJECT: {top_project.get('name', '')} — {top_project.get('description', '')[:100]}
  Tech: {', '.join(top_project.get('techStack', [])[:5]) if isinstance(top_project.get('techStack'), list) else ''}
EDUCATION: {institution} — CGPA: {cgpa}

JD CONTEXT (use to make email specific):
{jd_text[:500] if jd_text else 'No JD provided — write a general outreach email'}

JD MATCH VERDICT: {jd_details.get('verdict', '')}
CANDIDATE STRENGTHS: {', '.join(jd_details.get('strengths', [])[:3])}

Write the cold email using the {framework} framework.
Body must be 100-130 words. Subject 5-8 words.
Sound like a real human wrote this — no AI clichés.
Do NOT start with "I hope", "I am writing", or "My name is".

Return JSON: {{"subject": "...", "body": "...", "framework": "{framework}", "tone": "...", "word_count": 0, "greeting_style": "..."}}"""

        email_data = await gemini_json(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_fast,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
        )

        # If Gemini returned parse error, fall back to V1 immediately
        if email_data.get("_parse_error") or not email_data.get("body"):
            logger.warning("[Agent 4] LLM parse error — using V1 fallback")
            health_map = dict(state.get("agent_health_map") or {})
            health_map[AGENT_COLD_EMAIL] = HEALTH_OK
            return {
                "cold_email_output": _v1_fallback_email(state),
                "agent_health_map": health_map,
            }

        subject = email_data.get("subject") or f"Application: {role} at {company}"
        body = email_data.get("body", "")

        # Quality checks
        cliches_found = detect_ai_cliches(body)
        if cliches_found:
            logger.warning(f"[Agent 4] AI clichés detected: {cliches_found}")

        word_count = count_words(body)
        mailto = build_mailto_link(
            to=recruiter_email,
            subject=subject,
            body=body,
            from_email=candidate_email,
        )
        gmail_url = build_gmail_url(to=recruiter_email, subject=subject, body=body)

        output = {
            "subject": subject,
            "body": body,
            "framework": framework,
            "tone": email_data.get("tone", "professional"),
            "word_count": word_count,
            "greeting_style": email_data.get("greeting_style", ""),
            "mailto_link": mailto,
            "gmail_url": gmail_url,
            "cliches_found": cliches_found,
        }

        logger.info(
            f"[Agent 4 — Cold Email] Complete | session={session_id} "
            f"| framework={framework} | words={word_count}"
        )

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_COLD_EMAIL] = HEALTH_OK
        return {
            "cold_email_output": output,
            "agent_health_map": health_map,
        }

    except Exception as exc:
        logger.error(f"[Agent 4 — Cold Email] FAILED: {exc}", exc_info=True)
        # Fallback: use V1 template-based email
        try:
            output = _v1_fallback_email(state)
        except Exception:
            role = state.get("role_title") or "role"
        output = {"subject": f"Application for {role}",
                      "body": "Please find my resume attached. I am interested in this role.",
                      "mailto_link": "", "gmail_url": ""}

        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_COLD_EMAIL] = HEALTH_FAILED
        return {
            "cold_email_output": output,
            "agent_health_map": health_map,
        }


def _v1_fallback_email(state: AgentState) -> dict:
    """V1 cold_email_agent fallback when LLM fails."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
    from cold_email_agent import generate_outreach  # type: ignore

    resume = state.get("final_resume") or state.get("parsed_resume") or {}
    jd_details = state.get("jd_match_details") or {}
    try:
        result = generate_outreach(
            resume_json=resume,
            job_analysis=jd_details,
            company_name=state.get("company_name", "Company"),
            role_title=state.get("role_title", "Developer"),
            your_name=(resume.get("contact") or {}).get("name", "Candidate"),
            recruiter_name=state.get("recruiter_name", "Hiring Team"),
        )
        subject = result.get("email_subject", "Job Application")
        body = result.get("email_body", "")
    except Exception:
        contact = resume.get("contact") or {}
        name = contact.get("name", "Candidate")
        role = state.get("role_title", "Developer")
        company = state.get("company_name", "your company")
        subject = f"{role} Application — {name}"
        body = (
            f"Hi,\n\nI came across the {role} opening at {company} and believe my background "
            f"is a strong fit. I have hands-on experience with "
            f"{', '.join(str(s) for s in resume.get('skills', [])[:4])}.\n\n"
            f"Would you have 15 minutes to connect this week?\n\nBest,\n{name}"
        )
    recruiter_email = state.get("recruiter_email", "")
    candidate_email = state.get("candidate_email") or ""
    recruiter_email = recruiter_email or ""
    return {
        "subject": subject,
        "body": body,
        "framework": "template_fallback",
        "word_count": len(body.split()),
        "mailto_link": build_mailto_link(recruiter_email, subject, body, candidate_email),
        "gmail_url": build_gmail_url(recruiter_email, subject, body),
    }
