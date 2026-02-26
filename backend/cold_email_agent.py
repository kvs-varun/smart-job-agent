from typing import Dict


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
