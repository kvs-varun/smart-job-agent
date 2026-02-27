import os
from typing import Dict, Optional

try:
    from .knowledge_base import KnowledgeBase
    from .resume_parser import parse_resume_text_to_json
    from .resume_loader import extract_text_from_upload
    from .job_matcher import analyze_job, compute_scores
    from .resume_tailor import tailor_resume
    from .ats_resume_generator import generate_ats_pdf
except ImportError:
    from knowledge_base import KnowledgeBase
    from resume_parser import parse_resume_text_to_json
    from resume_loader import extract_text_from_upload
    from job_matcher import analyze_job, compute_scores
    from resume_tailor import tailor_resume
    from ats_resume_generator import generate_ats_pdf


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

    tailor_out = tailor_resume(
        resume_json=resume_json,
        job_analysis={**job_analysis, **scores},
        knowledge_base=kb,
        llm_helper=None,
    )

    tailored_resume_json = tailor_out.get("tailored_resume_json")
    change_log = tailor_out.get("change_log")

    output_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
    pdf_path = generate_ats_pdf(tailored_resume_json, output_dir=output_dir, filename_prefix="ats_resume", candidate_name=resume_json.get("name"))

    download_url = f"/static/generated/{os.path.basename(pdf_path)}"

    return {
        "analysis": {
            "role_key": role_key,
            "role_confidence": role_conf,
            "job_analysis": job_analysis,
            "scores": scores,
            "parse_warnings": resume_json.get("parse_warnings", []),
        },
        "tailored_resume_json": tailored_resume_json,
        "change_log": change_log,
        "download_url": download_url,
        "pdf_path": pdf_path,
    }


def process_resume_from_upload(file_storage, job_text: str, role_preference: str = "auto") -> Dict:
    """Knowledge-augmented pipeline from uploaded resume file (PDF/DOCX)."""

    extracted = extract_text_from_upload(file_storage)
    return process_resume_from_text(extracted, job_text, role_preference=role_preference)
