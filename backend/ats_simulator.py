import re
from typing import Dict, List


def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9+ ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def check_resume_quality(resume_json: Dict, job_analysis: Dict) -> Dict:
    """Basic ATS-simulator + recruiter readability gate.

    This does NOT parse the PDF (keeps dependencies minimal). Instead it checks the
    generated resume_json which directly feeds the PDF generator.

    Returns:
    - passed (bool)
    - ats_gate_score (0-100)
    - keyword_coverage (0-100)
    - issues (list[str])
    - suggestions (list[str])
    """

    issues: List[str] = []
    suggestions: List[str] = []

    role_key = job_analysis.get("role_key")
    priority_skills = job_analysis.get("priority_skills", []) or []
    job_skills = job_analysis.get("job_skills", []) or []

    # Section presence
    for section in ("summary", "skills", "projects", "education"):
        if not resume_json.get(section):
            issues.append(f"Missing section: {section}")

    projects = resume_json.get("projects", []) or []
    if len(projects) < 1:
        issues.append("No projects found. Indian fresher screening is project-heavy.")
    if len(projects) > 5:
        suggestions.append("Consider limiting projects to 2–4 most relevant for one-page clarity.")

    # Keyword coverage (skills only)
    resume_skills = [s.lower() for s in (resume_json.get("skills") or [])]
    job_skills_l = [s.lower() for s in job_skills]

    matched = sorted(list(set(resume_skills) & set(job_skills_l)))
    coverage = int((len(matched) / len(job_skills_l)) * 100) if job_skills_l else 0

    if priority_skills:
        pr = [p.lower() for p in priority_skills]
        missing_pr = [p for p in pr if p not in resume_skills]
        if missing_pr:
            issues.append("Missing priority skills from SKILLS: " + ", ".join(missing_pr[:5]))
            suggestions.append("If you genuinely know these, add them under Skills or Familiarity/Exposure.")

    # One-page heuristic: approximate content length
    text_blob = " ".join([
        resume_json.get("summary") or "",
        ", ".join(resume_json.get("skills") or []),
        " ".join(resume_json.get("projects") or []),
        " ".join(resume_json.get("experience") or []),
        " ".join(resume_json.get("education") or []),
        " ".join(resume_json.get("familiarity_exposure") or []),
    ])
    wc = len([w for w in text_blob.split() if w.strip()])
    if wc > 420:
        issues.append("Resume content likely exceeds one page (too much text).")
        suggestions.append("Shorten bullets to 1–2 lines and keep only most relevant projects.")

    # Gate score: combine coverage and section completeness.
    section_score = 0
    section_score += 20 if resume_json.get("summary") else 0
    section_score += 20 if resume_json.get("skills") else 0
    section_score += 20 if resume_json.get("projects") else 0
    section_score += 20 if resume_json.get("education") else 0
    section_score += 20 if (resume_json.get("experience") is not None) else 0

    ats_gate_score = min(100, int(0.65 * coverage + 0.35 * section_score))

    passed = ats_gate_score >= 75 and coverage >= 55 and len(issues) == 0

    if not passed:
        suggestions.append("Improve keyword alignment by reordering skills and adding honest Familiarity/Exposure.")

    return {
        "passed": passed,
        "ats_gate_score": ats_gate_score,
        "keyword_coverage": coverage,
        "issues": issues,
        "suggestions": suggestions,
    }
