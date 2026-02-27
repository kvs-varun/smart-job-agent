import os

from backend.ats_resume_generator import generate_ats_pdf


def test_generate_pdf_creates_file(tmp_path):
    resume_json = {
        "name": "Test Candidate",
        "contact": {"email": "test@example.com"},
        "summary": "Final-year CS student seeking fresher role.",
        "skills": ["python", "flask"],
        "projects": ["Built a Flask API for a college project"],
        "education": ["B.Tech CSE"],
        "experience": [],
        "familiarity_exposure": ["Familiarity/Exposure: Docker — reviewed via coursework"]
    }
    out_dir = tmp_path / "gen"
    path = generate_ats_pdf(resume_json, output_dir=str(out_dir), candidate_name=resume_json.get("name"))
    assert os.path.exists(path)
    assert path.lower().endswith(".pdf")
    assert os.path.getsize(path) > 500
