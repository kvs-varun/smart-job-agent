from typing import Dict, List, Optional


def _word_count(text: str) -> int:
    return len([w for w in (text or "").split() if w.strip()])


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


def _rewrite_bullet_rule_based(bullet: str, priority_skills: List[str], action_verbs: List[str]) -> str:
    b = (bullet or "").strip()
    if not b:
        return b

    # If bullet already starts with a strong verb, keep it.
    if b.split() and b.split()[0].rstrip(",.").capitalize() in action_verbs:
        return b

    verb = action_verbs[0] if action_verbs else "Built"

    # Front-load one priority skill if it's present anywhere.
    b_l = b.lower()
    front = None
    for s in priority_skills[:5]:
        if s.lower() in b_l:
            front = s
            break

    if front:
        return f"{verb} {front}-focused feature: {b[0].lower() + b[1:] if len(b) > 1 else b}"

    return f"{verb} {b[0].lower() + b[1:] if len(b) > 1 else b}"


def tailor_resume(
    resume_json: Dict,
    job_analysis: Dict,
    knowledge_base=None,
    llm_helper=None,
) -> Dict:
    """Knowledge-augmented, safe resume tailoring.

    Returns:
    - tailored_resume_json
    - change_log (list of {change, why, rule})

    Backward compatibility:
    - If called with (structured_resume, analysis_result) from old code, it will still work.
    """

    # Backward compatibility: old signature tailor_resume(structured_resume, analysis_result)
    if knowledge_base is None and llm_helper is None and "matched_skills" in job_analysis:
        structured_resume = resume_json
        analysis_result = job_analysis
        matched = analysis_result.get("matched_skills", [])
        missing = analysis_result.get("missing_skills", [])

        resume_skills = structured_resume.get("skills", []) or []
        matched_set = {s.lower() for s in matched}
        matched_skills = [s for s in resume_skills if s.lower() in matched_set]
        other_skills = [s for s in resume_skills if s.lower() not in matched_set]
        reordered_skills = _dedupe_keep_order(matched_skills + other_skills)

        summary = (structured_resume.get("summary") or "").strip()
        if not summary:
            summary = "Entry-level software engineer seeking an opportunity to apply strong fundamentals and project experience."
        if matched:
            top_matched = ", ".join(matched[:6])
            summary = f"{summary} Relevant skills for this role: {top_matched}."

        learning_exposure: List[str] = []
        if missing:
            learning_exposure = [f"Learning exposure / currently upskilling: {', '.join(missing[:8])}"]

        return {
            **structured_resume,
            "summary": summary,
            "skills": reordered_skills,
            "learning_exposure": learning_exposure,
        }

    change_log: List[Dict] = []

    matched = job_analysis.get("matched_skills", []) or []
    missing = job_analysis.get("missing_skills", []) or []
    priority_skills = job_analysis.get("priority_skills", []) or []

    practices = knowledge_base.resume_best_practices() if knowledge_base else {}
    action_verbs = practices.get("bullet_style", {}).get("action_verbs", []) or ["Built", "Developed", "Implemented"]

    # Reorder skills: matched first.
    resume_skills = resume_json.get("skills", []) or []
    matched_set = {s.lower() for s in matched}
    matched_skills = [s for s in resume_skills if s.lower() in matched_set]
    other_skills = [s for s in resume_skills if s.lower() not in matched_set]
    reordered_skills = _dedupe_keep_order(matched_skills + other_skills)
    if reordered_skills != resume_skills:
        change_log.append({
            "change": "Reordered SKILLS to place job-matched skills first.",
            "why": "Recruiters and ATS scan top skills early.",
            "rule": "resume_best_practices.structure.recommended_order_fresher + keyword alignment",
        })

    # Summary: add relevant skills line if missing.
    summary = (resume_json.get("summary") or "").strip()
    if not summary:
        summary = "Entry-level software engineer seeking an opportunity to apply strong fundamentals and project experience."
        change_log.append({
            "change": "Added a conservative SUMMARY because it was missing.",
            "why": "ATS-friendly resumes use a short summary for fresher context.",
            "rule": "resume_best_practices.structure.recommended_order_fresher",
        })

    if matched:
        top = ", ".join(matched[:6])
        if top and top.lower() not in summary.lower():
            summary = f"{summary} Relevant skills for this role: {top}."
            change_log.append({
                "change": "Appended relevant matched skills to SUMMARY.",
                "why": "Improves keyword alignment without inventing experience.",
                "rule": "ATS keyword alignment",
            })

    # Rewrite project bullets (rule-based for now).
    projects = resume_json.get("projects", []) or []
    rewritten_projects = []
    for p in projects:
        new_p = _rewrite_bullet_rule_based(p, priority_skills or matched, action_verbs)
        rewritten_projects.append(new_p)
        if new_p != p:
            change_log.append({
                "change": "Rephrased a project bullet to start with an action verb.",
                "why": "Indian fresher screening prefers concise, action-led bullets.",
                "rule": "resume_best_practices.bullet_style.action_verbs",
            })

    # Missing skills: add ONLY as familiarity/exposure.
    familiarity_exposure: List[str] = []
    for s in missing[:8]:
        familiarity_exposure.append(f"Familiarity/Exposure: {s} — currently learning and practicing via projects/courses")

    if familiarity_exposure:
        change_log.append({
            "change": "Added missing JD skills under Familiarity/Exposure (not as claimed experience).",
            "why": "Ethical tailoring: show learning intent without false claims.",
            "rule": "integrity_rules: missing skills exposure only",
        })

    tailored_resume_json = {
        **resume_json,
        "summary": summary,
        "skills": reordered_skills,
        "projects": rewritten_projects,
        "familiarity_exposure": familiarity_exposure,
    }

    return {"tailored_resume_json": tailored_resume_json, "change_log": change_log}
