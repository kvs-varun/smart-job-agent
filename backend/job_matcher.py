from typing import Dict

try:
    from .agent_reasoner import analyze_match, generate_resume_actions
    from .knowledge_base import KnowledgeBase
except ImportError:
    from agent_reasoner import analyze_match, generate_resume_actions
    from knowledge_base import KnowledgeBase


def extract_skills_from_text(text: str, knowledge_base: KnowledgeBase, role_hint: str) -> list:
    """Extract skills from text using KB keywords + existing rule-based fallback."""

    text_l = (text or "").lower()
    kw = knowledge_base.get_keywords_for_role(role_hint)
    terms = [t.lower() for t in (kw.get("must_have", []) + kw.get("good_to_have", []) + kw.get("tools", []))]
    expanded = knowledge_base.expand_synonyms(terms, role_hint)

    found = []
    for t in expanded:
        if t.lower() in text_l:
            found.append(t.lower())

    # Fallback: existing known_skills list (agent_reasoner)
    fallback = analyze_match(text or "", text or "").get("resume_skills", [])
    for s in fallback:
        if s.lower() in text_l:
            found.append(s.lower())

    # de-dupe
    out = []
    seen = set()
    for s in found:
        k = s.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def analyze_job(job_text: str, knowledge_base: KnowledgeBase, role_hint: str) -> Dict:
    """Analyze job description: extract job skills and infer priorities."""

    job_skills = extract_skills_from_text(job_text, knowledge_base, role_hint)

    # Priority: must-have skills present in JD
    kw = knowledge_base.get_keywords_for_role(role_hint)
    must = [k.lower() for k in kw.get("must_have", [])]
    priority = [s for s in job_skills if s in must]

    return {
        "role_key": role_hint,
        "job_skills": job_skills,
        "priority_skills": priority,
        "experience_req": None,
    }


def compute_scores(resume_json: Dict, job_analysis: Dict) -> Dict:
    """Compute match percentage + a separate ATS alignment score."""

    resume_text = (resume_json.get("raw") or "")
    resume_skills = [s.lower() for s in (resume_json.get("skills") or [])]
    job_skills = [s.lower() for s in (job_analysis.get("job_skills") or [])]

    matched = sorted(list(set(resume_skills) & set(job_skills)))
    missing = sorted(list(set(job_skills) - set(resume_skills)))

    match_percentage = int((len(matched) / len(job_skills)) * 100) if job_skills else 0

    # ATS alignment is broader: includes presence of sections and density.
    section_bonus = 0
    for key in ("summary", "skills", "projects", "education"):
        if resume_json.get(key):
            section_bonus += 10
    # cap 40
    section_bonus = min(section_bonus, 40)

    ats_alignment_score = min(100, int(0.6 * match_percentage + 0.4 * section_bonus))

    recommendations = []
    if missing:
        recommendations.append("Add missing skills only under Familiarity/Exposure if you have genuinely studied/used them.")
    if not resume_json.get("projects"):
        recommendations.append("Add 1-2 strong projects; Indian fresher screening is project-heavy.")

    return {
        "match_percentage": match_percentage,
        "ats_alignment_score": ats_alignment_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "recommendations": recommendations,
    }


def match_resume_to_job(resume_text: str, job_description: str) -> Dict:
    """Thin wrapper around the existing rule-based matcher.

    Kept as a separate module so you can later swap in a better matcher
    (e.g., taxonomy-based keyword extraction) without changing routes.
    """

    analysis = analyze_match(resume_text, job_description)
    actions = generate_resume_actions(analysis)
    return {"analysis": analysis, "recommended_actions": actions}
