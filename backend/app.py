from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid
import time

try:
    from flask_cors import CORS
except Exception:
    CORS = None

try:
    from .agent_controller import run_agent_pipeline, run_agent_pipeline_from_file
    from .agent_reasoner import analyze_match, generate_resume_actions
    from .cold_email_agent import generate_cold_outreach_messages
    from .application_tracker import add_application, list_applications, update_application_status
    from .agent_pipeline import process_resume_from_text, process_resume_from_upload
    from .resume_parser import parse_resume_text_to_json
    from .resume_loader import extract_text_from_upload
    from .analytics import track_event, summarize_events
except ImportError:
    from agent_controller import run_agent_pipeline, run_agent_pipeline_from_file
    from agent_reasoner import analyze_match, generate_resume_actions
    from cold_email_agent import generate_cold_outreach_messages
    from application_tracker import add_application, list_applications, update_application_status
    from agent_pipeline import process_resume_from_text, process_resume_from_upload
    from resume_parser import parse_resume_text_to_json
    from resume_loader import extract_text_from_upload
    from analytics import track_event, summarize_events
app = Flask(__name__)

if CORS:
    CORS(app)


_RATE = {}


@app.before_request
def _rate_limit():
    # Minimal per-IP throttle for local dev.
    ip = request.remote_addr or "unknown"
    now = time.time()
    window_s = 5
    limit = 20
    bucket = _RATE.get(ip, [])
    bucket = [t for t in bucket if now - t < window_s]
    if len(bucket) >= limit:
        return jsonify({"error": "rate_limited", "detail": "Too many requests. Please slow down."}), 429
    bucket.append(now)
    _RATE[ip] = bucket


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/agent/observe", methods=["POST"])
def observe():
    data = request.json

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    resume = data.get("resumeText")
    job = data.get("jobDescription")

    if not resume or not job:
        return jsonify({"error": "resumeText and jobDescription are required"}), 400

    analysis = analyze_match(resume, job)
    actions = generate_resume_actions(analysis)

    return jsonify({
        "message": "Agent analysis complete",
        "analysis": analysis,
        "recommended_actions": actions
    })




@app.route("/agent/generate-resume", methods=["POST"])
def generate_resume():
    data = request.json

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    resume = data.get("resumeText")
    job = data.get("jobDescription")

    if not resume or not job:
        return jsonify({"error": "resumeText and jobDescription are required"}), 400

    role_pref = data.get("role_preference", "auto")
    try:
        track_event(
            db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
            event_type="generate_attempt",
            payload={"input": "text", "role_preference": role_pref},
        )
    except Exception:
        pass
    report = process_resume_from_text(resume_text=resume, job_text=job, role_preference=role_pref)
    return jsonify({"message": "ATS resume generated", **report})


@app.route("/agent/download/<path:filename>", methods=["GET"])
def download_resume(filename: str):
    # Security: only serve files from known generated directories.
    static_generated_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
    legacy_generated_dir = os.path.join(os.path.dirname(__file__), "generated")
    try:
        track_event(
            db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
            event_type="pdf_download",
            payload={"filename": filename},
        )
    except Exception:
        pass

    # Prefer new location.
    if os.path.exists(os.path.join(static_generated_dir, filename)):
        return send_from_directory(static_generated_dir, filename, as_attachment=True)

    # Backward-compatible fallback.
    return send_from_directory(legacy_generated_dir, filename, as_attachment=True)


@app.route("/static-generated/<path:filename>", methods=["GET"])
def download_static_generated(filename: str):
    # Attachment helper (some browsers open PDFs inline under /static).
    static_generated_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
    return send_from_directory(static_generated_dir, filename, as_attachment=True)


@app.route("/agent/preview-resume-upload", methods=["POST"])
def preview_resume_upload():
    job = request.form.get("jobDescription") or ""
    role_pref = request.form.get("role_preference", "auto")
    f = request.files.get("resumeFile")

    if not f:
        return jsonify({"error": "resumeFile is required"}), 400

    resume_text = extract_text_from_upload(f)
    resume_json = parse_resume_text_to_json(resume_text)

    # Lightweight analysis for preview (no PDF generation here)
    report = process_resume_from_text(resume_text=resume_text, job_text=job, role_preference=role_pref)
    return jsonify({
        "message": "Preview parsed",
        "resume_preview": {
            "name": resume_json.get("name"),
            "contact": resume_json.get("contact"),
            "summary": resume_json.get("summary"),
            "skills": resume_json.get("skills"),
            "projects": resume_json.get("projects"),
            "education": resume_json.get("education"),
            "experience": resume_json.get("experience"),
            "parse_warnings": resume_json.get("parse_warnings", []),
        },
        "analysis": report.get("analysis"),
    })


@app.route("/agent/preview-resume-text", methods=["POST"])
def preview_resume_text():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    resume = data.get("resumeText")
    job = data.get("jobDescription", "")
    role_pref = data.get("role_preference", "auto")
    if not resume:
        return jsonify({"error": "resumeText is required"}), 400

    resume_json = parse_resume_text_to_json(resume)
    report = process_resume_from_text(resume_text=resume, job_text=job, role_preference=role_pref)
    return jsonify({
        "message": "Preview parsed",
        "resume_preview": {
            "name": resume_json.get("name"),
            "contact": resume_json.get("contact"),
            "summary": resume_json.get("summary"),
            "skills": resume_json.get("skills"),
            "projects": resume_json.get("projects"),
            "education": resume_json.get("education"),
            "experience": resume_json.get("experience"),
            "parse_warnings": resume_json.get("parse_warnings", []),
        },
        "analysis": report.get("analysis"),
    })


@app.route("/agent/finalize-resume", methods=["POST"])
def finalize_resume():
    """Finalize PDF only from user-approved resume_json.

    This endpoint does not perform additional rewriting. It only:
    - runs quality gate on the provided JSON
    - generates the PDF
    """

    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    approved = data.get("approved_resume_json")
    if not approved or not isinstance(approved, dict):
        return jsonify({"error": "approved_resume_json (object) is required"}), 400

    # Reuse pipeline generator for PDF path rules.
    try:
        from .ats_resume_generator import generate_ats_pdf
        from .ats_simulator import check_resume_quality
    except ImportError:
        from ats_resume_generator import generate_ats_pdf
        from ats_simulator import check_resume_quality

    job_analysis = data.get("job_analysis", {}) or {}

    gate = check_resume_quality(approved, job_analysis)
    if not gate.get("passed"):
        return jsonify({"error": "quality_gate_failed", "quality_gate": gate}), 400

    output_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
    pdf_path = generate_ats_pdf(
        approved,
        output_dir=output_dir,
        filename_prefix="ats_resume_final",
        candidate_name=approved.get("name"),
    )
    download_url = f"/static/generated/{os.path.basename(pdf_path)}"

    return jsonify({
        "message": "Final PDF generated",
        "download_url": download_url,
        "pdf_path": pdf_path,
        "quality_gate": gate,
    })


@app.route("/agent/generate-resume-upload", methods=["POST"])
def generate_resume_upload():
    # multipart/form-data: resumeFile + jobDescription
    job = request.form.get("jobDescription")
    f = request.files.get("resumeFile")

    if not job or not f:
        return jsonify({"error": "resumeFile and jobDescription are required"}), 400

    uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(f.filename or 'resume')}"
    uploaded_path = os.path.join(uploads_dir, safe_name)
    f.save(uploaded_path)

    role_pref = request.form.get("role_preference", "auto")
    try:
        track_event(
            db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
            event_type="generate_attempt",
            payload={"input": "upload", "role_preference": role_pref, "filename": f.filename},
        )
    except Exception:
        pass
    report = process_resume_from_upload(file_storage=f, job_text=job, role_preference=role_pref)
    return jsonify({"message": "ATS resume generated from upload", **report})


@app.route("/agent/generate-cold-email", methods=["POST"])
def generate_cold_email():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    job = data.get("jobDescription", "")
    company = data.get("companyName", "")
    role = data.get("roleTitle", "")
    candidate = data.get("candidateName", "")
    projects = data.get("keyProjects", "")

    if not job or not company or not role:
        return jsonify({"error": "jobDescription, companyName, and roleTitle are required"}), 400

    messages = generate_cold_outreach_messages(
        job_description=job,
        company_name=company,
        role_title=role,
        candidate_name=candidate,
        key_projects=projects,
    )

    try:
        track_event(
            db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
            event_type="outreach_generated",
            payload={"company": company, "role": role},
        )
    except Exception:
        pass

    return jsonify({"message": "Outreach generated", "outreach": messages})


@app.route("/analytics/summary", methods=["GET"])
def analytics_summary():
    token = os.getenv("SMART_JOB_AGENT_ANALYTICS_TOKEN")
    if token:
        given = request.headers.get("X-Analytics-Token")
        if given != token:
            return jsonify({"error": "unauthorized"}), 401

    db_path = os.path.join(os.path.dirname(__file__), "data", "events.json")
    return jsonify(summarize_events(db_path))


@app.route("/tracker/add", methods=["POST"])
def tracker_add():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    company = data.get("company")
    role = data.get("role")
    if not company or not role:
        return jsonify({"error": "company and role are required"}), 400

    db_path = os.path.join(os.path.dirname(__file__), "data", "applications.json")
    rec = add_application(
        db_path=db_path,
        company=company,
        role=role,
        job_url=data.get("job_url", ""),
        resume_filename=data.get("resume_filename", ""),
        status=data.get("status", "applied"),
        notes=data.get("notes", ""),
    )

    return jsonify({"message": "Application saved", "record": rec})


@app.route("/tracker/list", methods=["GET"])
def tracker_list():
    db_path = os.path.join(os.path.dirname(__file__), "data", "applications.json")
    return jsonify({"applications": list_applications(db_path)})


@app.route("/tracker/update", methods=["POST"])
def tracker_update():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    application_id = data.get("id")
    status = data.get("status")
    if not application_id or not status:
        return jsonify({"error": "id and status are required"}), 400

    db_path = os.path.join(os.path.dirname(__file__), "data", "applications.json")
    try:
        rec = update_application_status(db_path, application_id, status, follow_up=data.get("follow_up"))
        return jsonify({"message": "Application updated", "record": rec})
    except KeyError:
        return jsonify({"error": "application id not found"}), 404


if __name__ == "__main__":
    app.run(port=5000, debug=True)
