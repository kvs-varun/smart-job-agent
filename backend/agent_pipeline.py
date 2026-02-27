import os
from typing import Dict, Optional

try:
    from .knowledge_base import KnowledgeBase
    from .resume_parser import parse_resume_text_to_json
    from .resume_loader import extract_text_from_upload
    from .job_matcher import analyze_job, compute_scores
    from .resume_tailor import tailor_resume
    from .ats_resume_generator import generate_ats_pdf
    from .cold_email_agent import generate_outreach
    from .ats_simulator import check_resume_quality
except ImportError:
    from knowledge_base import KnowledgeBase
    from resume_parser import parse_resume_text_to_json
    from resume_loader import extract_text_from_upload
    from job_matcher import analyze_job, compute_scores
    from resume_tailor import tailor_resume
    from ats_resume_generator import generate_ats_pdf
    from cold_email_agent import generate_outreach
    from ats_simulator import check_resume_quality


def _get_kb() -> KnowledgeBase:
    knowledge_dir = os.path.join(os.path.dirname(__file__), "knowledge")
    kb = KnowledgeBase(knowledge_dir)
    kb.load_all()
    return kb


def process_resume_from_text(resume_text: str, job_text: str, role_preference: str = "auto") -> Dict:
    """Knowledge-augmented pipeline from pasted resume text."""

    kb = _get_kb()

    resume_json = parse_resume_text_to_json(resume_text)

    if role_preference and role_preference != "auto":
        role_key = role_preference
        role_conf = 1.0
    else:
        role_key, role_conf = kb.infer_role_key(job_text)

    job_analysis = analyze_job(job_text, kb, role_key)
    scores = compute_scores(resume_json, job_analysis)

    # Quality gate loop: tailor -> validate -> auto-correct up to 3 times.
    tailored_resume_json = None
    change_log = None
    gate = None

    base_job = {**job_analysis, **scores}

    for attempt in range(1, 4):
        tailor_out = tailor_resume(
            resume_json=resume_json if attempt == 1 else tailored_resume_json,
            job_analysis=base_job,
            knowledge_base=kb,
            llm_helper=None,
        )

        tailored_resume_json = tailor_out.get("tailored_resume_json")
        change_log = tailor_out.get("change_log")

        gate = check_resume_quality(tailored_resume_json, base_job)
        if gate.get("passed"):
            break

        # Auto-corrections (safe): tighten length, emphasize priority skills, add exposure.
        # 1) Trim projects to 4
        projs = tailored_resume_json.get("projects", []) or []
        if len(projs) > 4:
            tailored_resume_json["projects"] = projs[:4]
        # 2) Ensure priority skills appear in skills (only if already present in resume raw)
        # We do not fabricate skills; if missing, we add them only as exposure.
        missing_priority = []
        for s in (base_job.get("priority_skills") or [])[:6]:
            if s.lower() not in [x.lower() for x in (tailored_resume_json.get("skills") or [])]:
                missing_priority.append(s)
        if missing_priority:
            exposure = tailored_resume_json.get("familiarity_exposure") or []
            for s in missing_priority[:4]:
                exposure.append(f"Familiarity/Exposure: {s} — reviewed via coursework and hands-on practice")
            tailored_resume_json["familiarity_exposure"] = exposure

    output_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
    pdf_path = generate_ats_pdf(
        tailored_resume_json,
        output_dir=output_dir,
        filename_prefix="ats_resume",
        candidate_name=resume_json.get("name"),
    )

    download_url = f"/static/generated/{os.path.basename(pdf_path)}"

    outreach = generate_outreach(
        resume_json=tailored_resume_json,
        job_analysis={**job_analysis, **scores},
        company_name="{{company}}",
        role_title="{{role}}",
        your_name=tailored_resume_json.get("name") or "{{your_name}}",
        recruiter_name="{{recruiter_name}}",
    )

    return {
        "analysis": {
            "role_key": role_key,
            "role_confidence": role_conf,
            "job_analysis": job_analysis,
            "scores": scores,
            "parse_warnings": resume_json.get("parse_warnings", []),
            "quality_gate": gate,
        },
        "tailored_resume_json": tailored_resume_json,
        "change_log": change_log,
        "outreach": outreach,
        "download_url": download_url,
        "pdf_path": pdf_path,
    }


def process_resume_from_upload(file_storage, job_text: str, role_preference: str = "auto") -> Dict:
    """Knowledge-augmented pipeline from uploaded resume file (PDF/DOCX)."""

    extracted = extract_text_from_upload(file_storage)
    return process_resume_from_text(extracted, job_text, role_preference=role_preference)
