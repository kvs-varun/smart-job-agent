import os
from typing import Dict

try:
    from .agent_reasoner import analyze_match, generate_resume_actions
    from .ats_resume_generator import generate_ats_pdf
    from .job_matcher import match_resume_to_job
    from .resume_loader import load_resume_text_from_upload
    from .resume_parser import parse_resume_text
    from .resume_tailor import tailor_resume
except ImportError:
    from agent_reasoner import analyze_match, generate_resume_actions
    from ats_resume_generator import generate_ats_pdf
    from job_matcher import match_resume_to_job
    from resume_loader import load_resume_text_from_upload
    from resume_parser import parse_resume_text
    from resume_tailor import tailor_resume


def run_agent_pipeline(resume_text: str, job_description: str, output_dir: str) -> Dict:
    """Orchestrate parsing, analysis, tailoring and ATS PDF generation.

    Returns a dict ready to JSON-serialize.
    """

    structured = parse_resume_text(resume_text)

    match = match_resume_to_job(resume_text, job_description)
    analysis = match.get("analysis", {})
    actions = match.get("recommended_actions", [])

    tailored = tailor_resume(structured, analysis)

    pdf_path = generate_ats_pdf(
        tailored_resume=tailored,
        output_dir=output_dir,
        filename_prefix="ats_resume",
        candidate_name=None,
    )

    return {
        "match_percentage": analysis.get("match_percentage", 0),
        "missing_skills": analysis.get("missing_skills", []),
        "recommended_actions": actions,
        "pdf_path": pdf_path,
        "analysis": analysis,
    }


def run_agent_pipeline_from_file(uploaded_file_path: str, original_filename: str, job_description: str, output_dir: str) -> Dict:
    """Pipeline variant for uploaded resume files (PDF/DOCX)."""

    resume_text = load_resume_text_from_upload(uploaded_file_path, original_filename)
    return run_agent_pipeline(resume_text=resume_text, job_description=job_description, output_dir=output_dir)
