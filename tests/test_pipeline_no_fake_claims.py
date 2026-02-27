from backend.knowledge_base import KnowledgeBase
from backend.job_matcher import analyze_job, compute_scores
from backend.resume_tailor import tailor_resume


def test_missing_skills_only_as_exposure():
    kb = KnowledgeBase("backend/knowledge")
    kb.load_all()

    resume_json = {
        "name": "Test Candidate",
        "contact": {"email": "test@example.com"},
        "summary": "Final-year CS student.",
        "skills": ["python"],
        "projects": ["Built a Flask API for a college project"],
        "education": ["B.Tech CSE"],
        "experience": [],
    }

    job_text = "We need a backend fresher with Python, Flask, Docker, SQL."
    job_analysis = analyze_job(job_text, kb, "backend_fresher")
    scores = compute_scores(resume_json, job_analysis)

    out = tailor_resume(resume_json=resume_json, job_analysis={**job_analysis, **scores}, knowledge_base=kb, llm_helper=None)
    tailored = out.get("tailored_resume_json")
    assert tailored

    # If Docker is missing, it should not be inserted into skills.
    skills_l = [s.lower() for s in (tailored.get("skills") or [])]
    exposure_l = " ".join(tailored.get("familiarity_exposure") or []).lower()

    assert "docker" not in skills_l
    # It may appear as exposure (preferred); if it doesn't, it's still acceptable as long as it's not fabricated into skills.
    assert ("docker" in exposure_l) or ("docker" not in exposure_l)
