from typing import Dict

try:
    from .agent_reasoner import analyze_match, generate_resume_actions
except ImportError:
    from agent_reasoner import analyze_match, generate_resume_actions


def match_resume_to_job(resume_text: str, job_description: str) -> Dict:
    """Thin wrapper around the existing rule-based matcher.

    Kept as a separate module so you can later swap in a better matcher
    (e.g., taxonomy-based keyword extraction) without changing routes.
    """

    analysis = analyze_match(resume_text, job_description)
    actions = generate_resume_actions(analysis)
    return {"analysis": analysis, "recommended_actions": actions}
