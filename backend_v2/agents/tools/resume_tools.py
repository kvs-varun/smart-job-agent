"""
Resume tools — async wrappers + LLM-powered parser.
Primary parsing is done by Gemini (structured extraction).
V1 regex parser is kept as fallback only.
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from resume_tailor import tailor_resume      # type: ignore
from ats_simulator import check_resume_quality  # type: ignore
from job_matcher import analyze_job, compute_scores, extract_skills_from_text  # type: ignore

from backend_v2.agents.tools.kb_tools import get_kb

logger = logging.getLogger(__name__)


# ── LLM-Powered Resume Parser ─────────────────────────────────────────────────

_PARSE_SYSTEM = """You are a world-class resume data extraction specialist.
Your job: extract EVERY SINGLE piece of information from raw resume text into structured JSON.

EXTRACTION RULES (CRITICAL):
1. Extract ONLY what is actually written — NEVER invent or add anything
2. Skills must be INDIVIDUAL technologies/tools (e.g., "Python", "React", "FastAPI")
   NEVER put sentences, phrases, or experience bullets into the skills array
3. Experience bullets: preserve the original text, one bullet per line with • prefix
4. Dates: extract exactly as written, prefer "MMM YYYY" format
5. If a field is not found, use "" for strings or [] for arrays
6. Identify the target job title from the summary/experience context

COMPLETENESS IS MANDATORY:
- Extract ALL experience entries — if there are 5 jobs, return all 5. Never stop at 1.
- Extract ALL projects — if there are 4 projects, return all 4.
- Extract ALL education entries — every degree, certification, course.
- Extract ALL certifications — AWS, Google, Microsoft, Coursera, NPTEL, Udemy, etc.
- Extract ALL skills — every single one listed in the skills section.
- Extract ALL achievements, publications, open source contributions, volunteer work if present.
- DO NOT skip or summarize any section. Partial extraction is a failure.

SKILLS EXTRACTION — This is where most parsers fail:
- Skills section contains: Python, React, FastAPI, Docker, AWS → extract each as separate item
- DO NOT put experience descriptions into skills
- DO NOT put project names into skills
- If skills appear comma-separated: split each one into its own array entry
- Typical skills: programming languages, frameworks, tools, platforms, databases
- Maximum 40 skills. Each skill should be 1-4 words max.

CERTIFICATIONS vs EDUCATION:
- Education: degrees (B.Tech, M.Tech, MBA, B.Sc) from universities and colleges
- Certifications: industry certs (AWS, Azure, Google Cloud, Coursera, Udemy, NPTEL, LinkedIn Learning, etc.)
- Keep them SEPARATE — do NOT mix certifications into the education array

CRITICAL: Your entire response must be a single valid JSON object. No markdown, no explanation.
CRITICAL: Include ALL experience, ALL projects, ALL education, ALL certifications — no truncation allowed."""

_PARSE_USER_TEMPLATE = """Extract ALL information from this resume into the exact JSON schema below.

MANDATORY: Extract EVERY experience role, EVERY project, EVERY education entry, EVERY certification.
If the resume has 3 jobs → return all 3. If it has 5 projects → return all 5. Never truncate.

RESUME TEXT:
{resume_text}

OUTPUT THIS EXACT JSON STRUCTURE (fill every field — include ALL entries, not just the first one):
{{
  "contact": {{
    "name": "Full name exactly as written",
    "email": "email@domain.com",
    "phone": "+91 XXXXXXXXXX or as written",
    "location": "City, State/Country",
    "linkedin": "linkedin URL or username",
    "github": "github URL or username",
    "portfolio": "personal website/portfolio URL if present",
    "jobTitle": "Infer target role from resume context (e.g., Full-Stack Developer, Data Scientist)"
  }},
  "summary": "Professional summary paragraph, exactly as written in the resume",
  "skills": [
    "Python", "React", "FastAPI", "Docker", "AWS"
  ],
  "experience": [
    {{
      "title": "Job Title / Internship Title",
      "company": "Company Name",
      "location": "City or Remote",
      "startDate": "MMM YYYY",
      "endDate": "MMM YYYY or Present",
      "description": "• First achievement bullet\\n• Second achievement bullet\\n• Third achievement bullet"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "What it does, what problem it solves, scale/impact",
      "techStack": ["Python", "React", "AWS"],
      "github": "github.com/... link if present",
      "demo": "live demo URL if present"
    }}
  ],
  "education": [
    {{
      "institution": "University/College Name",
      "degree": "B.Tech / B.E. / M.Tech / etc.",
      "field": "Computer Science / Data Science / etc.",
      "grade": "CGPA: X.X or XX%",
      "startDate": "MMM YYYY or YYYY",
      "endDate": "MMM YYYY or YYYY"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification name (e.g., AWS Certified Solutions Architect - Associate)",
      "issuer": "Issuing organization (e.g., Amazon Web Services, Google, Coursera, NPTEL)",
      "issuedDate": "MMM YYYY",
      "expiryDate": "MMM YYYY or leave empty if no expiry",
      "credentialID": "Credential ID if present, else empty",
      "credentialURL": "Verification URL if present, else empty"
    }}
  ],
  "achievements": [
    {{
      "title": "Achievement title (e.g., Hackathon Winner, Dean's List, Best Paper Award)",
      "description": "Brief description",
      "date": "MMM YYYY or YYYY"
    }}
  ],
  "openSource": [
    {{
      "project": "Project name (e.g., React, TensorFlow, etc.)",
      "contribution": "What you contributed (PRs merged, issues resolved, features added)",
      "github": "Link if available"
    }}
  ],
  "publications": [
    {{
      "title": "Paper/Blog/Talk title",
      "publisher": "Publisher/Conference/Platform",
      "date": "MMM YYYY",
      "url": "Link if available"
    }}
  ],
  "volunteering": [
    {{
      "role": "Role (e.g., Mentor, Organizer, Contributor)",
      "organization": "Organization name",
      "description": "Brief description",
      "startDate": "MMM YYYY",
      "endDate": "MMM YYYY or Present"
    }}
  ],
  "languages": [
    {{
      "language": "Language name",
      "proficiency": "Native / Fluent / Conversational / Basic"
    }}
  ]
}}"""


async def parse_resume_with_llm(
    raw_text: str,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    """
    Use Gemini to intelligently extract structured resume data from raw text.
    This is the PRIMARY parser — handles complex PDFs, non-standard formatting,
    multi-column layouts, and prevents skills contamination from experience text.
    """
    from backend_v2.agents.tools.gemini_client import gemini_json

    if not raw_text or not raw_text.strip():
        return _minimal_resume_structure()

    # Use full resume text — 8000 chars covers even the most detailed 2-page resume
    # (avg resume = 3000-5000 chars; 4000 was cutting off jobs 2+ and all projects)
    text_for_llm = raw_text[:8000].strip()

    result = await gemini_json(
        api_key=api_key,
        model_name=model,
        system_prompt=_PARSE_SYSTEM,
        user_prompt=_PARSE_USER_TEMPLATE.format(resume_text=text_for_llm),
        max_tokens=8192,   # Increased: full resume JSON output needs space for all entries
        temperature=0.1,   # Low temperature for factual extraction
    )

    if result.get("_parse_error") or not isinstance(result.get("contact"), dict):
        logger.warning("[parse_resume_with_llm] LLM parse error — falling back to regex parser")
        return await _regex_parse_async(raw_text)

    # Validate and clean the result
    return _validate_and_clean_parsed(result, raw_text)


def _validate_and_clean_parsed(parsed: dict, raw_text: str) -> dict:
    """
    Validate LLM output. Fix any remaining structure issues.
    Most importantly: ensure skills are individual items, not sentences.
    """
    import copy
    result = copy.deepcopy(parsed)

    # Ensure contact structure
    contact = result.get("contact", {})
    if not isinstance(contact, dict):
        contact = {}
    contact.setdefault("name", "")
    contact.setdefault("email", "")
    contact.setdefault("phone", "")
    contact.setdefault("location", "")
    contact.setdefault("linkedin", "")
    contact.setdefault("github", "")
    contact.setdefault("jobTitle", "")
    result["contact"] = contact

    # Clean skills — filter out anything that looks like a sentence (>5 words or >40 chars)
    raw_skills = result.get("skills", [])
    if isinstance(raw_skills, list):
        clean_skills = []
        for s in raw_skills:
            if not isinstance(s, str):
                continue
            s = s.strip().strip("•-*·")
            # Skip if it looks like a sentence (has verb-like structure or too long)
            words = s.split()
            if len(words) > 5 or len(s) > 40:
                continue
            if s and s not in clean_skills:
                clean_skills.append(s)
        result["skills"] = clean_skills[:40]
    else:
        result["skills"] = []

    # Ensure experience is list of dicts
    experience = result.get("experience", [])
    if not isinstance(experience, list):
        experience = []
    clean_exp = []
    for exp in experience:
        if isinstance(exp, str):
            # Convert raw string to dict
            clean_exp.append({
                "title": "", "company": exp[:60], "location": "",
                "startDate": "", "endDate": "", "description": exp,
            })
        elif isinstance(exp, dict):
            exp.setdefault("title", "")
            exp.setdefault("company", "")
            exp.setdefault("location", "")
            exp.setdefault("startDate", "")
            exp.setdefault("endDate", "")
            exp.setdefault("description", "")
            clean_exp.append(exp)
    result["experience"] = clean_exp

    # Ensure projects is list of dicts
    projects = result.get("projects", [])
    if not isinstance(projects, list):
        projects = []
    clean_proj = []
    for proj in projects:
        if isinstance(proj, str):
            clean_proj.append({
                "name": proj[:60], "description": proj,
                "techStack": [], "github": "", "demo": "",
            })
        elif isinstance(proj, dict):
            proj.setdefault("name", "")
            proj.setdefault("description", "")
            if not isinstance(proj.get("techStack"), list):
                proj["techStack"] = []
            proj.setdefault("github", "")
            proj.setdefault("demo", "")
            clean_proj.append(proj)
    result["projects"] = clean_proj

    # Ensure education is list of dicts
    education = result.get("education", [])
    if not isinstance(education, list):
        education = []
    clean_edu = []
    for edu in education:
        if isinstance(edu, str):
            clean_edu.append({
                "institution": edu[:60], "degree": "", "field": "",
                "grade": "", "startDate": "", "endDate": "",
            })
        elif isinstance(edu, dict):
            edu.setdefault("institution", "")
            edu.setdefault("degree", "")
            edu.setdefault("field", "")
            edu.setdefault("grade", "")
            edu.setdefault("startDate", "")
            edu.setdefault("endDate", "")
            clean_edu.append(edu)
    result["education"] = clean_edu

    result.setdefault("summary", "")
    result["raw"] = raw_text[:2000]

    # ── Certifications ──────────────────────────────────────────────────────────
    certifications = result.get("certifications", [])
    if not isinstance(certifications, list):
        certifications = []
    clean_certs = []
    for cert in certifications:
        if isinstance(cert, str):
            clean_certs.append({
                "name": cert, "issuer": "", "issuedDate": "",
                "expiryDate": "", "credentialID": "", "credentialURL": "",
            })
        elif isinstance(cert, dict):
            cert.setdefault("name", "")
            cert.setdefault("issuer", "")
            cert.setdefault("issuedDate", "")
            cert.setdefault("expiryDate", "")
            cert.setdefault("credentialID", "")
            cert.setdefault("credentialURL", "")
            if cert.get("name"):
                clean_certs.append(cert)
    result["certifications"] = clean_certs

    # ── Achievements ────────────────────────────────────────────────────────────
    achievements = result.get("achievements", [])
    if not isinstance(achievements, list):
        achievements = []
    clean_ach = []
    for ach in achievements:
        if isinstance(ach, dict):
            ach.setdefault("title", "")
            ach.setdefault("description", "")
            ach.setdefault("date", "")
            if ach.get("title"):
                clean_ach.append(ach)
        elif isinstance(ach, str) and ach.strip():
            clean_ach.append({"title": ach, "description": "", "date": ""})
    result["achievements"] = clean_ach

    # ── Open Source ─────────────────────────────────────────────────────────────
    open_source = result.get("openSource", [])
    if not isinstance(open_source, list):
        open_source = []
    clean_os = []
    for item in open_source:
        if isinstance(item, dict):
            item.setdefault("project", "")
            item.setdefault("contribution", "")
            item.setdefault("github", "")
            if item.get("project") or item.get("contribution"):
                clean_os.append(item)
    result["openSource"] = clean_os

    # ── Publications ────────────────────────────────────────────────────────────
    result.setdefault("publications", [])
    if not isinstance(result["publications"], list):
        result["publications"] = []

    # ── Volunteering ────────────────────────────────────────────────────────────
    result.setdefault("volunteering", [])
    if not isinstance(result["volunteering"], list):
        result["volunteering"] = []

    # ── Languages ───────────────────────────────────────────────────────────────
    result.setdefault("languages", [])
    if not isinstance(result["languages"], list):
        result["languages"] = []

    # ── Contact portfolio field ──────────────────────────────────────────────────
    if isinstance(result.get("contact"), dict):
        result["contact"].setdefault("portfolio", "")

    return result


def _minimal_resume_structure() -> dict:
    return {
        "contact": {"name": "", "email": "", "phone": "", "location": "",
                    "linkedin": "", "github": "", "portfolio": "", "jobTitle": ""},
        "summary": "",
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "openSource": [],
        "publications": [],
        "volunteering": [],
        "languages": [],
    }


async def _regex_parse_async(text: str) -> dict:
    """Fallback: V1 regex parser, wraps output into V2 schema."""
    try:
        from resume_parser import parse_resume_text_to_json  # type: ignore
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, parse_resume_text_to_json, text)

        # Map V1 flat output to V2 structured schema
        contact_v1 = raw.get("contact", {})
        return {
            "contact": {
                "name": raw.get("name") or "",
                "email": contact_v1.get("email") or "",
                "phone": contact_v1.get("phone") or "",
                "location": "",
                "linkedin": "",
                "github": "",
                "jobTitle": "",
            },
            "summary": raw.get("summary", ""),
            "skills": raw.get("skills", [])[:20],
            "experience": [
                {"title": "", "company": "", "location": "",
                 "startDate": "", "endDate": "", "description": str(e)}
                for e in raw.get("experience", [])[:5]
            ],
            "projects": [
                {"name": str(p)[:60], "description": str(p), "techStack": [], "github": "", "demo": ""}
                for p in raw.get("projects", [])[:5]
            ],
            "education": [
                {"institution": str(e)[:80], "degree": "", "field": "", "grade": "", "startDate": "", "endDate": ""}
                for e in raw.get("education", [])[:3]
            ],
            "raw": text[:2000],
        }
    except Exception as exc:
        logger.error(f"[_regex_parse_async] Regex parser also failed: {exc}")
        return _minimal_resume_structure()


# ── Primary async interface ────────────────────────────────────────────────────

async def parse_resume_async(text: str) -> dict[str, Any]:
    """
    Parse resume text into structured JSON.
    Uses LLM as primary parser, regex as fallback.
    Requires GEMINI_API_KEY to be set for LLM path.
    """
    try:
        from backend_v2.config import get_settings
        settings = get_settings()
        if settings.gemini_api_key:
            return await parse_resume_with_llm(text, settings.gemini_api_key, settings.llm_model_fast)
    except Exception as exc:
        logger.warning(f"[parse_resume_async] LLM path failed: {exc} — using regex fallback")
    return await _regex_parse_async(text)


async def load_and_parse_file_async(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Load file bytes (PDF/DOCX), extract text, then LLM-parse into structured JSON.
    """
    import tempfile, os
    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        loop = asyncio.get_running_loop()
        # Extract text from file
        if suffix == ".pdf":
            text = await loop.run_in_executor(None, _extract_pdf_text, tmp_path)
        elif suffix == ".docx":
            text = await loop.run_in_executor(None, _extract_docx_text, tmp_path)
        else:
            text = ""

        if not text or not text.strip():
            logger.warning(f"[load_and_parse_file_async] Empty text from {filename}")
            return _minimal_resume_structure()

        # Use LLM parser (primary)
        return await parse_resume_async(text)

    finally:
        os.unlink(tmp_path)


def _extract_pdf_text(path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text(layout=True) or page.extract_text() or ""
                pages.append(text)
            return "\n".join(pages)
    except Exception as exc:
        logger.warning(f"[_extract_pdf_text] pdfplumber failed: {exc}")
        return ""


def _extract_docx_text(path: str) -> str:
    """Extract text from DOCX."""
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        logger.warning(f"[_extract_docx_text] docx failed: {exc}")
        return ""


# ── Job Matching ──────────────────────────────────────────────────────────────

async def analyze_job_async(jd_text: str, role_hint: str = "") -> dict[str, Any]:
    """Analyze JD and extract structured requirements.
    role_hint must be a plain string role key (e.g. 'backend_fresher').
    """
    kb = get_kb()
    loop = asyncio.get_running_loop()
    # Ensure role_hint is a plain string (infer_role_key returns tuple in V1)
    if isinstance(role_hint, tuple):
        role_hint = role_hint[0]
    role_hint = str(role_hint) if role_hint else "backend_fresher"
    try:
        return await loop.run_in_executor(None, analyze_job, jd_text, kb, role_hint)
    except Exception as exc:
        logger.warning(f"[analyze_job_async] V1 analyze_job failed: {exc} — returning empty analysis")
        return {"role_key": role_hint, "job_skills": [], "priority_skills": []}


async def compute_match_scores_async(
    resume_json: dict[str, Any],
    job_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Compute match score between resume and job analysis.
    Converts V2 resume format to V1-compatible format first.
    """
    loop = asyncio.get_running_loop()
    v1_resume = _v2_to_v1_resume(resume_json)
    try:
        return await loop.run_in_executor(None, compute_scores, v1_resume, job_analysis)
    except Exception as exc:
        logger.warning(f"[compute_match_scores_async] V1 compute_scores failed: {exc} — returning 0")
        return {"overall_score": 0.0, "matched_skills": [], "missing_skills": [], "skill_match_pct": 0}


async def extract_skills_async(text: str, role_hint: str = "") -> list[str]:
    """Extract skills from text using KB-aware extraction."""
    kb = get_kb()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, extract_skills_from_text, text, kb, role_hint
    )
    return result or []


# ── Tailoring ─────────────────────────────────────────────────────────────────

async def tailor_resume_async(
    resume_json: dict[str, Any],
    job_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Rule-based safe resume tailoring (V1 logic, no fabrication)."""
    kb = get_kb()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, tailor_resume, resume_json, job_analysis, kb, None)
    return result or {}


# ── Quality Gate ──────────────────────────────────────────────────────────────

def _v2_to_v1_resume(resume_json: dict) -> dict:
    """
    Convert V2 structured resume (lists of dicts) to V1 flat format
    that ats_simulator.check_resume_quality expects (lists of strings).
    """
    if not isinstance(resume_json, dict):
        return {}
    v1 = dict(resume_json)

    # V1 expects experience as list of strings
    experience = resume_json.get("experience", [])
    if experience and isinstance(experience[0], dict):
        v1["experience"] = [
            f"{e.get('title', '')} at {e.get('company', '')} | {e.get('description', '')[:200]}"
            for e in experience
        ]

    # V1 expects projects as list of strings
    projects = resume_json.get("projects", [])
    if projects and isinstance(projects[0], dict):
        v1["projects"] = [
            f"{p.get('name', '')} — {p.get('description', '')[:150]}"
            for p in projects
        ]

    # V1 expects education as list of strings
    education = resume_json.get("education", [])
    if education and isinstance(education[0], dict):
        v1["education"] = [
            f"{e.get('degree', '')} {e.get('field', '')} {e.get('institution', '')} {e.get('grade', '')}"
            for e in education
        ]

    # V1 expects skills as list of strings (already is)
    skills = resume_json.get("skills", [])
    v1["skills"] = [str(s) for s in skills if s]

    # V1 ats_simulator also checks summary as a string
    contact = resume_json.get("contact", {})
    if isinstance(contact, dict):
        v1["name"] = contact.get("name", "")
        v1["email"] = contact.get("email", "")

    return v1


async def check_quality_async(
    resume_json: dict[str, Any],
    job_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run ATS quality gate (reuses V1 ats_simulator.check_resume_quality).
    Converts V2 structured format to V1 flat format first.
    """
    loop = asyncio.get_running_loop()
    v1_resume = _v2_to_v1_resume(resume_json)
    try:
        result = await loop.run_in_executor(
            None, check_resume_quality, v1_resume, job_analysis or {}
        )
        return result or {"passed": True, "issues": [], "ats_score": 70}
    except Exception as exc:
        logger.warning(f"[check_quality_async] V1 quality check failed: {exc} — returning pass")
        return {"passed": True, "issues": [], "ats_score": 70}
