from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid
import time
import re

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
    from .billing_stub import billing_bp
    from .llm_helper import call_llm
except ImportError:
    from agent_controller import run_agent_pipeline, run_agent_pipeline_from_file
    from agent_reasoner import analyze_match, generate_resume_actions
    from cold_email_agent import generate_cold_outreach_messages
    from application_tracker import add_application, list_applications, update_application_status
    from agent_pipeline import process_resume_from_text, process_resume_from_upload
    from resume_parser import parse_resume_text_to_json
    from resume_loader import extract_text_from_upload
    from analytics import track_event, summarize_events
    from billing_stub import billing_bp
    from llm_helper import call_llm
app = Flask(__name__)

if CORS:
    CORS(app)

app.register_blueprint(billing_bp)


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


def _tokenize_keywords(text: str):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", (text or "").lower())
    stop = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "by",
        "as",
        "is",
        "are",
        "be",
        "this",
        "that",
        "from",
        "at",
        "it",
        "we",
        "you",
        "your",
        "our",
    }
    return [w for w in words if w not in stop and len(w) >= 3]


def _top_keywords(text: str, limit: int = 40):
    freq = {}
    for w in _tokenize_keywords(text):
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:limit]]


@app.route("/agent/analyze-resume-jd-match", methods=["POST"])
def analyze_resume_jd_match():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    resume_text = data.get("resumeText") or ""
    job_text = data.get("jobDescription") or ""
    if not resume_text.strip() or not job_text.strip():
        return jsonify({"error": "resumeText and jobDescription are required"}), 400

    try:
        track_event(
            db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
            event_type="jd_match_semantic_attempt",
            payload={"has_resume": bool(resume_text.strip()), "has_jd": bool(job_text.strip())},
        )
    except Exception:
        pass

    # Base rule-based analysis (always available)
    analysis = analyze_match(resume_text, job_text)
    matched_skills = sorted(set(analysis.get("matched_skills", []) or []))
    missing_skills = sorted(set(analysis.get("missing_skills", []) or []))

    jd_keywords = _top_keywords(job_text, limit=50)
    resume_keywords = set(_tokenize_keywords(resume_text))
    keyword_gaps = [k for k in jd_keywords if k not in resume_keywords][:30]

    # Score: blend skill match % and keyword coverage.
    skill_score = int(analysis.get("match_percentage", 0) or 0)
    keyword_cov = 0
    if jd_keywords:
        keyword_cov = int(round(100 * (len([k for k in jd_keywords if k in resume_keywords]) / len(jd_keywords))))
    final_score = int(round(0.7 * skill_score + 0.3 * keyword_cov))
    final_score = max(0, min(100, final_score))

    improvements = []
    if missing_skills:
        improvements.append({
            "priority": "high",
            "title": "Address missing skills",
            "detail": f"You are missing {min(len(missing_skills), 8)}+ key skills from the JD. Add only skills you genuinely have (or add 'Exposure' context).",
            "items": missing_skills[:12],
        })
    if keyword_gaps:
        improvements.append({
            "priority": "medium",
            "title": "Close keyword gaps",
            "detail": "Consider weaving these keywords into relevant bullets, projects, and skills (without keyword stuffing).",
            "items": keyword_gaps[:15],
        })
    if not resume_text.lower().count("impact") and "%" not in resume_text:
        improvements.append({
            "priority": "low",
            "title": "Add measurable impact",
            "detail": "Add numbers (latency, throughput, cost, time saved, adoption) where truthful to strengthen ATS + recruiter scan.",
            "items": [],
        })

    report = {
        "message": "JD match analysis ready",
        "match_score": final_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "score": final_score,
        "score_breakdown": {
            "skill_match": skill_score,
            "keyword_coverage": keyword_cov,
        },
        "skills": {
            "matched": matched_skills,
            "missing": missing_skills,
            "bonus": [],
        },
        "keyword_gaps": keyword_gaps,
        "improvements": improvements,
        "explanations": {
            "notes": [
                "This report is rule-based by default and works without an API key.",
                "If LLM_API_KEY is configured, we may enrich the analysis with semantic grouping.",
            ]
        },
        "llm": {"used": False, "reason": None},
    }

    # Optional LLM enrichment
    llm = call_llm(
        system=(
            "You are an expert ATS + recruiter resume analyst. "
            "Given a resume and job description, produce a compact JSON with: "
            "(1) grouped missing skills (by category), (2) top 10 keyword gaps, "
            "(3) 5 prioritized improvements. "
            "Do not fabricate experience. Only suggest phrasing, structure, and emphasis."
        ),
        user=(
            "Return ONLY JSON.\n\n"
            f"RESUME:\n{resume_text[:8000]}\n\n"
            f"JOB_DESCRIPTION:\n{job_text[:8000]}"
        ),
        temperature=0.2,
        max_tokens=800,
    )

    if llm.get("ok") and llm.get("text"):
        report["llm"]["used"] = True
        report["llm"]["reason"] = "ok"
        report["llm"]["raw"] = llm.get("text")
    else:
        report["llm"]["used"] = False
        report["llm"]["reason"] = llm.get("reason")

    return jsonify(report)


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
            "familiarity_exposure": resume_json.get("familiarity_exposure"),
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

    try:
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

        try:
            track_event(
                db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
                event_type="user_edit_accepted",
                payload={"has_job_analysis": bool(job_analysis)},
            )
        except Exception:
            pass

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

        try:
            track_event(
                db_path=os.path.join(os.path.dirname(__file__), "data", "events.json"),
                event_type="final_pdf_generated",
                payload={"filename": os.path.basename(pdf_path)},
            )
        except Exception:
            pass

        return jsonify({
            "message": "Final PDF generated",
            "download_url": download_url,
            "pdf_path": pdf_path,
            "quality_gate": gate,
        })
    except Exception as e:
        try:
            app.logger.error(str(e))
        except Exception:
            print(e)
        return jsonify({"error": str(e)}), 500


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
    recruiter_email = (data.get("recruiterEmail") or "").strip()
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

    # Convenience links
    subject = f"Application for {role} — {candidate or 'Your Name'}"
    body = messages.get("cold_email", "")
    try:
        from urllib.parse import quote
    except Exception:
        quote = None

    mailto = None
    gmail_url = None
    if quote:
        to_part = recruiter_email
        mailto = f"mailto:{to_part}?subject={quote(subject)}&body={quote(body)}"
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(to_part)}&su={quote(subject)}&body={quote(body)}"

    return jsonify({
        "message": "Outreach generated",
        "outreach": messages,
        "mailto": mailto,
        "gmail_url": gmail_url,
    })


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
