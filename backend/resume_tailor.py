from typing import Dict, List


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it.strip())
    return out


def tailor_resume(structured_resume: Dict, analysis_result: Dict) -> Dict:
    """Tailor a structured resume to a job analysis result.

    Principles:
    - Reorder skills to put matched skills first.
    - Emphasize matched skills in summary with honest phrasing.
    - Missing skills are ONLY added as "learning exposure" suggestions.
      We do not claim proficiency the user didn't state.

    Returns a new dict (does not mutate input).
    """

    matched = analysis_result.get("matched_skills", [])
    missing = analysis_result.get("missing_skills", [])

    resume_skills = structured_resume.get("skills", []) or []

    matched_set = {s.lower() for s in matched}

    matched_skills = [s for s in resume_skills if s.lower() in matched_set]
    other_skills = [s for s in resume_skills if s.lower() not in matched_set]

    reordered_skills = _dedupe_keep_order(matched_skills + other_skills)

    summary = (structured_resume.get("summary") or "").strip()
    if not summary:
        # Fresher-friendly default objective.
        summary = "Entry-level software engineer seeking an opportunity to apply strong fundamentals and project experience."

    if matched:
        top_matched = ", ".join(matched[:6])
        summary = f"{summary} Relevant skills for this role: {top_matched}."

    learning_exposure: List[str] = []
    if missing:
        learning_exposure = [
            f"Learning exposure / currently upskilling: {', '.join(missing[:8])}"
        ]

    tailored = {
        **structured_resume,
        "summary": summary,
        "skills": reordered_skills,
        "learning_exposure": learning_exposure,
    }

    return tailored
