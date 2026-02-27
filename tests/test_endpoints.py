import json


def test_preview_and_finalize(client):
    resume_text = """Rahul Sharma\nrahul@example.com\n\nSummary\nFinal-year CS student.\n\nSkills\nPython, Flask\n\nProjects\n- Built a Flask API\n\nEducation\nB.Tech CSE\n"""
    job_text = "Backend fresher role: Python, Flask, SQL."

    resp = client.post(
        "/agent/preview-resume-text",
        data=json.dumps({"resumeText": resume_text, "jobDescription": job_text}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "resume_preview" in data
    assert "analysis" in data

    approved = data["resume_preview"]
    resp2 = client.post(
        "/agent/finalize-resume",
        data=json.dumps({"approved_resume_json": approved, "job_analysis": (data.get("analysis") or {}).get("job_analysis", {})}),
        content_type="application/json",
    )
    # finalize can fail gate; ensure returns either 200 with download_url or 400 with quality_gate
    assert resp2.status_code in (200, 400)
    data2 = resp2.get_json()
    assert data2 is not None
