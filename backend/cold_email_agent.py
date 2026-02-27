import os
import re
from typing import Dict

try:
    from .knowledge_base import KnowledgeBase
except ImportError:
    from knowledge_base import KnowledgeBase


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def _truncate_words(text: str, max_words: int) -> str:
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    if len(words) <= max_words:
        return (" ".join(words)).strip()
    return (" ".join(words[:max_words])).strip()


def _truncate_chars(text: str, max_chars: int) -> str:
    t = (text or "")
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def _fill_template(template: str, values: Dict[str, str]) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def generate_outreach(
    resume_json: Dict,
    job_analysis: Dict,
    company_name: str,
    role_title: str,
    your_name: str,
    recruiter_name: str = "Hiring Team",
    template_key: str = "default",
) -> Dict:
    """Generate constrained outreach (email + LinkedIn) using local knowledge templates.

    Constraints enforced:
    - Email body <= 150 words
    - LinkedIn message <= 300 chars
    - Professional, Indian fresher-appropriate tone
    - Includes 10–15 min coffee chat CTA
    """

    knowledge_dir = os.path.join(os.path.dirname(__file__), "knowledge")
    kb = KnowledgeBase(knowledge_dir)

    templates = kb.cold_email_templates()
    constraints = templates.get("constraints", {})
    max_words = int(constraints.get("cold_email_max_words", 150))
    max_chars = int(constraints.get("linkedin_max_chars", 300))

    t = templates.get("templates", {})
    cold = t.get("cold_email", {})
    subject_t = cold.get("subject", "Application for {{role}} — {{candidate_name}}")
    body_t = cold.get("body", "")
    linkedin_t = t.get("linkedin", "")

    matched = job_analysis.get("matched_skills", []) or job_analysis.get("scores", {}).get("matched_skills", []) or []
    projects = resume_json.get("projects", []) or []

    skill_cluster = ", ".join([s for s in matched[:3] if s]) or "relevant skills"
    project_highlight = projects[0] if projects else "a role-relevant project"

    values = {
        "recruiter_name": (recruiter_name or "Hiring Team").strip() or "Hiring Team",
        "company": (company_name or "the company").strip() or "the company",
        "role": (role_title or "the role").strip() or "the role",
        "candidate_name": (your_name or resume_json.get("name") or "Your Name").strip() or "Your Name",
        "skill_cluster": skill_cluster,
        "project_highlight": project_highlight,
        "your_name": (your_name or resume_json.get("name") or "Your Name").strip() or "Your Name",
    }

    subject = _fill_template(subject_t, values).strip()
    email_body = _fill_template(body_t, values).strip()

    # Add a soft, professional CTA if not present.
    cta = "If you have 10–15 minutes this week, I’d be grateful for a quick coffee chat/call to learn more about the role."
    if "10" not in email_body and "15" not in email_body:
        email_body = email_body + "\n\n" + cta

    # Enforce word limit.
    if _word_count(email_body) > max_words:
        email_body = _truncate_words(email_body, max_words)

    linkedin_message = _fill_template(linkedin_t, values).strip()
    # Ensure CTA in LinkedIn within limit.
    if "10" not in linkedin_message and "15" not in linkedin_message:
        linkedin_message = (linkedin_message + " 10–15 min chat?").strip()
    linkedin_message = _truncate_chars(linkedin_message, max_chars)

    return {
        "subject": subject,
        "email_body": email_body,
        "linkedin_message": linkedin_message,
        "constraints": {"email_max_words": max_words, "linkedin_max_chars": max_chars},
    }


def generate_cold_outreach_messages(
    job_description: str,
    company_name: str,
    role_title: str,
    candidate_name: str,
    key_projects: str = "",
) -> Dict:
    """Generate human-written templates for Indian job market outreach.

    This is NOT an LLM call. It's a safe, deterministic template generator.
    You can later plug in an LLM behind a feature flag.
    """

    company = (company_name or "the company").strip() or "the company"
    role = (role_title or "the role").strip() or "the role"
    name = (candidate_name or "Your Name").strip() or "Your Name"

    project_line = ""
    if key_projects.strip():
        project_line = f"I have worked on: {key_projects.strip()}. "

    email = (
        f"Subject: Application for {role} — {name}\n\n"
        f"Hi Hiring Team at {company},\n\n"
        f"I’m {name}, a fresher software engineer. I’m reaching out regarding the {role} position. "
        f"{project_line}"
        f"Based on the job description, I believe my skills and projects align with your requirements. "
        f"I’ve attached my resume and would be grateful for an opportunity to interview.\n\n"
        f"Thank you for your time.\n"
        f"Regards,\n{name}\n"
        f"Phone: +91-XXXXXXXXXX\n"
        f"Email: your.email@example.com\n"
    )

    linkedin_connect = (
        f"Hi, I’m {name}. I came across the {role} opening at {company}. "
        f"I’m a fresher with project experience and would love to connect and learn more about the role."
    )

    referral = (
        f"Hi, I’m {name}. I’m applying for the {role} role at {company}. "
        f"If you’re comfortable, could you please refer me? I can share my tailored resume and relevant projects."
    )

    return {
        "cold_email": email,
        "linkedin_message": linkedin_connect,
        "referral_request": referral,
        "notes": "Edit these templates with real links (GitHub/Portfolio/LinkedIn) before sending.",
    }
