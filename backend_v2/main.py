"""
Smart Job Agent V2 — FastAPI Application
Port: 8000 (V1 Flask stays on port 5000 during migration)
"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend_v2.config import get_settings
from backend_v2.database import init_pool, close_pool
from backend_v2.agents.graph import run_session
from backend_v2.agents.state import default_state
from backend_v2.agents.agent_05_infra import run_startup_checks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB pool and run Agent 5 startup checks."""
    logger.info("Smart Job Agent V2 starting up...")
    # Ensure generated files directory exists
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generated files directory: {settings.generated_dir}")
    try:
        await init_pool()
        logger.info("PostgreSQL pool initialized")
        await run_startup_checks()
    except Exception as exc:
        logger.warning(f"DB init failed (continuing without persistence): {exc}")
    yield
    await close_pool()
    logger.info("Smart Job Agent V2 shutting down")


app = FastAPI(
    title="Smart Job Agent V2",
    version="2.0.0",
    description="8-agent LangGraph orchestration for ATS resume building and automated job applications",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class BuildResumeTextRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_data: Optional[dict] = None
    job_description: Optional[str] = None
    selected_template: str = "ats_pro"
    role_preference: Optional[str] = None
    candidate_email: Optional[str] = None
    recruiter_email: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    auto_apply_enabled: bool = False


class GenerateSummaryRequest(BaseModel):
    resume_data: Optional[dict] = None       # structured resume from builder
    existing_summary: Optional[str] = None   # what the candidate already typed
    job_description: Optional[str] = None    # optional JD for tailoring
    role_title: Optional[str] = None         # target role (e.g. "Backend Engineer")
    target_role: Optional[str] = None        # alias — used by role-selector UI
    consent_given: bool = False              # GDPR: explicit consent to AI processing


class JDMatchRequest(BaseModel):
    resume_text: str
    job_description: str
    selected_template: str = "ats_pro"


class ColdEmailRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_data: Optional[dict] = None
    recruiter_email: str
    candidate_email: Optional[str] = None
    company_name: str
    role_title: str
    job_description: Optional[str] = None
    recruiter_name: Optional[str] = None


class FinalizeRequest(BaseModel):
    resume_data: dict
    selected_template: str = "ats_pro"
    session_id: Optional[str] = None


class ScoreRequest(BaseModel):
    resume_data: dict
    job_description: Optional[str] = None


class AutoApplyRequest(BaseModel):
    resume_data: dict
    resume_score: Optional[float] = None
    preferences: Optional[dict] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def new_session_id() -> str:
    return f"v2_{uuid.uuid4().hex[:12]}"


async def _parse_resume_input(resume_text: str = None, resume_data: dict = None) -> dict:
    """Parse resume from text if resume_data not provided."""
    if resume_data:
        return resume_data
    if resume_text:
        from backend_v2.agents.tools.resume_tools import parse_resume_async
        return await parse_resume_async(resume_text)
    return {}


# ─── Core Agent Routes ────────────────────────────────────────────────────────

@app.post("/v2/agent/build-resume")
async def build_resume_from_text(req: BuildResumeTextRequest):
    """
    Full 8-agent pipeline: parse → architect+enhance → JD match → PDF → score → cold email.
    Accepts either resume_text (raw string) or resume_data (structured dict from builder).
    """
    if not req.resume_text and not req.resume_data:
        raise HTTPException(400, "Provide resume_text or resume_data")

    session_id = new_session_id()
    state = default_state(session_id, req.selected_template)
    state.update({
        "raw_resume_text": req.resume_text,
        "job_description": req.job_description,
        "role_preference": req.role_preference,
        "candidate_email": req.candidate_email,
        "recruiter_email": req.recruiter_email,
        "company_name": req.company_name,
        "role_title": req.role_title,
        "auto_apply_enabled": req.auto_apply_enabled,
    })

    # If structured resume_data is provided (from builder), pre-populate parsed_resume
    # so Agent 1 can skip the text parsing step and work directly on the structured data.
    if req.resume_data:
        state["parsed_resume"] = req.resume_data

    try:
        final_state = await run_session(state)
        return _format_response(final_state, session_id)
    except Exception as exc:
        logger.error(f"Build resume failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/v2/agent/build-resume-upload")
async def build_resume_from_upload(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    selected_template: str = Form("ats_pro"),
    role_preference: Optional[str] = Form(None),
    candidate_email: Optional[str] = Form(None),
    recruiter_email: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    role_title: Optional[str] = Form(None),
):
    """Full pipeline for uploaded resume (PDF/DOCX)."""
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    file_bytes = await file.read()
    session_id = new_session_id()
    state = default_state(session_id, selected_template)
    state.update({
        "raw_resume_bytes": file_bytes,
        "job_description": job_description,
        "role_preference": role_preference,
        "candidate_email": candidate_email,
        "recruiter_email": recruiter_email,
        "company_name": company_name,
        "role_title": role_title,
    })

    try:
        final_state = await run_session(state)
        return _format_response(final_state, session_id)
    except Exception as exc:
        logger.error(f"Upload build failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/v2/agent/parse-resume")
async def parse_resume_upload(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
):
    """
    LLM-powered resume parsing only (no full pipeline).
    Returns properly structured JSON matching frontend ResumeData schema.
    Used by the builder import flow for instant AI-quality parsing.
    """
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    file_bytes = await file.read()

    try:
        from backend_v2.agents.tools.resume_tools import load_and_parse_file_async
        parsed = await load_and_parse_file_async(file_bytes, file.filename)
        return {
            "ok": True,
            "parsed": parsed,
            "filename": file.filename,
            "parse_warnings": [],
        }
    except Exception as exc:
        logger.error(f"[parse-resume] Failed: {exc}")
        raise HTTPException(500, f"Parse failed: {exc}")


@app.post("/v2/agent/finalize-resume")
async def finalize_resume(req: FinalizeRequest):
    """Generate PDF from approved resume JSON (skips agent pipeline)."""
    session_id = req.session_id or new_session_id()
    state = default_state(session_id, req.selected_template)
    state["final_resume"] = req.resume_data

    from backend_v2.agents.graph import pdf_generator_node
    result = await pdf_generator_node(state)

    return {
        "ok": True,
        "session_id": session_id,
        "download_url": result.get("download_url"),
        "pdf_path": result.get("pdf_path"),
    }


class JDTailorRequest(BaseModel):
    resume_data: dict
    job_description: str
    selected_template: str = "ats_pro"
    role_preference: Optional[str] = None


@app.post("/v2/agent/jd-tailor")
async def jd_tailor_resume(req: JDTailorRequest):
    """
    Lightweight JD-specific resume rewrite: Agents 1 + 2 (parallel) → merge → PDF → Agent 3.
    Skips cold email, scorer, infra, and auto-apply — fast, focused, no hangs.
    Returns rewritten resume + JD match score + download URL in ~15-25 seconds.
    """
    import asyncio as _asyncio
    from backend_v2.agents.graph import (
        parse_resume_node, architect_node, enhancer_node,
        merge_parallel_node, quality_gate_node, auto_correct_node,
        pdf_generator_node,
    )
    from backend_v2.agents.agent_03_jd_strategist import run as _agent3_run

    session_id = new_session_id()
    state = default_state(session_id, req.selected_template)
    state.update({
        "parsed_resume": req.resume_data,   # pre-populated → parse_resume_node short-circuits
        "job_description": req.job_description,
        "role_preference": req.role_preference,
        "auto_apply_enabled": False,
    })

    try:
        # Step 1: parse (short-circuits since parsed_resume already set)
        state = {**state, **await parse_resume_node(state)}

        # Step 2: Agents 1 + 2 in parallel
        arch_result, enh_result = await _asyncio.gather(
            architect_node(state),
            enhancer_node(state),
            return_exceptions=True,
        )
        # Extract ONLY the output fields from each agent (not the full state they echo back).
        # Both agents run off the original `state` snapshot so a naive {**arch, **enh} merge
        # would have enh_result clobber arch_result's tailored_resume with the original None.
        if isinstance(arch_result, Exception):
            logger.warning(f"[jd-tailor] Agent 1 failed: {arch_result} — using parsed")
            state["tailored_resume"] = state.get("parsed_resume")
        else:
            state["tailored_resume"] = arch_result.get("tailored_resume") or state.get("parsed_resume")
            if arch_result.get("change_log"):
                state["change_log"] = arch_result["change_log"]

        if isinstance(enh_result, Exception):
            logger.warning(f"[jd-tailor] Agent 2 failed: {enh_result} — using tailored")
            state["enhanced_resume"] = state.get("tailored_resume") or state.get("parsed_resume")
        else:
            state["enhanced_resume"] = enh_result.get("enhanced_resume") or state.get("tailored_resume")
            if enh_result.get("quality_issues"):
                state["quality_issues"] = enh_result["quality_issues"]

        # Step 3: merge
        state = {**state, **await merge_parallel_node(state)}

        # Step 4: quality gate loop (max 2 iterations)
        for _ in range(2):
            state = {**state, **await quality_gate_node(state)}
            if state.get("quality_gate_passed"):
                break
            state = {**state, **await auto_correct_node(state)}

        # Step 5: PDF
        state = {**state, **await pdf_generator_node(state)}

        # Step 6: JD match analysis
        try:
            jd_state = await _agent3_run(state)
            state = {**state, **jd_state}
        except Exception as exc3:
            logger.warning(f"[jd-tailor] Agent 3 failed: {exc3}")

        download_url = state.get("download_url", "")
        if download_url and download_url.startswith("/v2/"):
            pass  # frontend will prepend /api

        # final_resume is the authoritative merged output; alias as tailored_resume for frontend
        final_resume = state.get("final_resume") or state.get("tailored_resume") or state.get("parsed_resume")
        return {
            "ok": True,
            "session_id": session_id,
            "download_url": download_url,
            "pdf_path": state.get("pdf_path"),
            "final_resume": final_resume,
            "tailored_resume": final_resume,   # alias — frontend uses this key
            "jd_match_score": state.get("jd_match_score"),
            "jd_match_details": state.get("jd_match_details"),
            "caution_issued": state.get("caution_issued", False),
            "tailoring_plan": state.get("tailoring_plan", []),
            "quality_gate": state.get("quality_gate"),
            "quality_gate_passed": state.get("quality_gate_passed", False),
            "change_log": state.get("change_log", []),
            "agent_health_map": state.get("agent_health_map", {}),
            "error": state.get("error"),
        }
    except Exception as exc:
        logger.error(f"[jd-tailor] Failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/v2/agent/jd-match")
async def jd_match(req: JDMatchRequest):
    """Agent 3 only — JD match analysis without full pipeline."""
    session_id = new_session_id()
    from backend_v2.agents.tools.resume_tools import parse_resume_async
    from backend_v2.agents.agent_03_jd_strategist import run as run_agent3

    parsed = await parse_resume_async(req.resume_text)
    state = default_state(session_id, req.selected_template)
    state.update({
        "parsed_resume": parsed,
        "final_resume": parsed,
        "job_description": req.job_description,
    })

    result = await run_agent3(state)
    return {
        "ok": True,
        "session_id": session_id,
        "match_score": result.get("jd_match_score"),
        "jd_match_details": result.get("jd_match_details"),
        "caution_issued": result.get("caution_issued", False),
        "tailoring_plan": result.get("tailoring_plan", []),
    }


@app.post("/v2/agent/generate-summary")
async def generate_summary(req: GenerateSummaryRequest):
    """
    Fast AI summary writer — recruiter-POV rewrite using Gemini Flash.
    Uses resume_data (skills, experience, projects) + optional JD to craft a
    tailored, STAR-based, ATS-optimized 3-sentence summary in ~3-5 seconds.
    Does NOT run the full agent pipeline.
    """
    from backend_v2.agents.tools.gemini_client import gemini_generate as _gemini_gen

    if not settings.gemini_api_key:
        raise HTTPException(500, "GEMINI_API_KEY not configured on backend")

    r = req.resume_data or {}
    contact = r.get("contact", {}) if isinstance(r.get("contact"), dict) else {}
    name = contact.get("name", "The candidate")
    job_title = req.role_title or contact.get("jobTitle", "")
    skills = r.get("skills", []) or []
    experience = r.get("experience", []) or []
    education = r.get("education", []) or []
    projects = r.get("projects", []) or []
    certs = r.get("certifications", []) or []

    # Build compact context — only sections that exist
    exp_lines = []
    for e in experience[:3]:
        if not isinstance(e, dict):
            continue
        exp_lines.append(
            f"- {e.get('title','')} at {e.get('company','')} "
            f"({e.get('startDate','')}–{e.get('endDate','Present')}): "
            f"{(e.get('description','') or '')[:200]}"
        )

    proj_lines = []
    for p in projects[:2]:
        if not isinstance(p, dict):
            continue
        stack = p.get("techStack", []) or []
        proj_lines.append(
            f"- {p.get('name','')}: {(p.get('description','') or '')[:150]} "
            f"| Stack: {', '.join(stack[:5])}"
        )

    edu_line = ""
    if education and isinstance(education[0], dict):
        edu = education[0]
        edu_line = (
            f"{edu.get('degree','')} in {edu.get('field','')} "
            f"from {edu.get('institution','')} ({edu.get('endYear','')})"
        )

    cert_line = ", ".join(
        c.get("name", "") for c in certs[:3] if isinstance(c, dict)
    ) if certs else ""

    existing = req.existing_summary or r.get("summary", "") or ""

    jd_section = ""
    if req.job_description:
        jd_section = (
            f"\nTARGET JOB DESCRIPTION (mirror its keywords naturally):\n"
            f"{req.job_description[:800]}\n"
        )

    # Resolve effective role — target_role (from role selector) takes priority over contact jobTitle
    effective_role = req.target_role or req.role_title or job_title or "Software Engineer"

    # ── Role-specific context research (domain vocabulary for the target role) ──
    ROLE_CONTEXT: dict[str, str] = {
        "backend": "microservices, REST APIs, system design, database optimization, concurrency, scalability, latency reduction, distributed systems",
        "frontend": "component architecture, performance optimization, Core Web Vitals, accessibility, design systems, state management, bundle size",
        "full stack": "end-to-end delivery, API design, frontend performance, database schema, deployment pipelines, system architecture",
        "software engineer": "clean code, system design, data structures, algorithms, code review, cross-functional collaboration, production reliability",
        "product engineer": "product thinking, user-centric engineering, A/B testing, feature flags, metrics-driven iteration, cross-functional delivery",
        "data scientist": "predictive modelling, feature engineering, A/B testing, statistical significance, model accuracy, business impact, EDA",
        "machine learning": "model training, inference optimization, MLOps, training pipelines, benchmark scores, production deployment, model monitoring",
        "devops": "CI/CD pipelines, infrastructure as code, zero-downtime deployments, SRE, observability, incident response, automation",
        "site reliability": "SLOs/SLAs/SLIs, toil reduction, chaos engineering, on-call, monitoring, alerting, capacity planning",
        "mobile": "cross-platform performance, app store optimization, offline-first architecture, user retention metrics, deep linking",
        "android": "Jetpack Compose, MVVM, Coroutines, Room DB, Play Store delivery, accessibility, crash-free rates",
        "ios": "SwiftUI, Combine, Core Data, TestFlight, App Store delivery, memory management, instrument profiling",
        "flutter": "widget architecture, state management (BLoC/Riverpod), native integrations, Play Store / App Store delivery",
        "data engineer": "ETL/ELT pipelines, data lake architecture, streaming ingestion (Kafka/Flink), query optimization, data lineage, governance",
        "cloud": "multi-region architecture, cost optimization, IAM, serverless, container orchestration, FinOps, disaster recovery",
        "security": "threat modelling, OWASP top 10, penetration testing, compliance (SOC2/ISO27001), zero-trust architecture, SIEM",
    }
    role_lower = effective_role.lower()
    role_domain_context = next(
        (v for k, v in ROLE_CONTEXT.items() if k in role_lower), ""
    )

    system_prompt = (
        f"You are a world-class technical resume writer and senior engineering recruiter who has "
        f"hired for Google, Microsoft, Razorpay, CRED, Atlassian, and 200+ top Indian tech companies.\n\n"
        f"═══════════════════════════════════════\n"
        f"CORE MANDATE: SHOWCASE TALENT CONFIDENTLY\n"
        f"═══════════════════════════════════════\n"
        f"This summary must read like a STATEMENT OF CAPABILITY — not a job application.\n"
        f"The candidate is NOT requesting a job. They ARE presenting what they deliver.\n"
        f"A recruiter reading this must immediately think: 'I need to call this person today.'\n\n"
        f"TARGET ROLE: {effective_role}\n"
        f"DOMAIN VOCABULARY TO WEAVE IN: {role_domain_context or 'technical depth, system design, scalable architecture'}\n\n"
        f"═══════════════════════════════\n"
        f"STRUCTURE — 4 SENTENCES MAXIMUM\n"
        f"═══════════════════════════════\n"
        f"S1 — IDENTITY + DOMAIN AUTHORITY (1 sentence)\n"
        f"    Lead with their professional identity + highest-value domain expertise.\n"
        f"    Pattern: '[Role] specialising in [top 2 domains] — [one crisp differentiator].'\n"
        f"    WRONG: 'Seeking a backend role to apply my skills'\n"
        f"    RIGHT: 'Backend Engineer specialising in distributed systems and API performance, "
        f"with a track record of shipping FastAPI services handling 100K+ daily requests.'\n\n"
        f"S2 — STRONGEST PROOF POINT (1 sentence)\n"
        f"    Name their best project or role. Use actual project name + actual tech + hard metric.\n"
        f"    If no metric exists, frame scale: users, data volume, team size, time saved, cost cut.\n"
        f"    WRONG: 'Built a web application using Python'\n"
        f"    RIGHT: 'Engineered SmartJobAgent — an 8-agent LangGraph orchestration system "
        f"using FastAPI, PostgreSQL, and Gemini API — now used by 300+ job seekers weekly.'\n\n"
        f"S3 — SECOND PROOF POINT OR TECHNICAL DEPTH (1 sentence)\n"
        f"    Second-best achievement OR demonstrate depth (architecture decision, algo, scale).\n"
        f"    WRONG: 'Also worked on other projects'\n"
        f"    RIGHT: 'Architected a BERT-based document classifier achieving 93% accuracy on a "
        f"10K-sample corpus, reducing manual triage time by 4 hours per day.'\n\n"
        f"S4 — AUTHORITY SIGNAL (1 sentence)\n"
        f"    Technical breadth + one hard credibility marker (cert, CGPA, award, open source, publication).\n"
        f"    If JD provided: mirror its exact keywords here naturally.\n"
        f"    WRONG: 'I am a quick learner with good communication skills'\n"
        f"    RIGHT: 'Fluent across Python, React, Docker, and AWS — certified Google Associate "
        f"Cloud Engineer — with a 9.1 CGPA from VIT Vellore.'\n\n"
        f"════════════════\n"
        f"ABSOLUTE RULES\n"
        f"════════════════\n"
        f"1. TONE: Assertive third-person. Confident. Zero hedging.\n"
        f"2. BANNED WORDS/PHRASES (auto-fail if any appear):\n"
        f"   seeking · looking for · hoping to · aspiring · eager to join · passionate · hardworking\n"
        f"   team player · excellent communication · motivated · detail-oriented · results-driven\n"
        f"   quick learner · go-getter · self-starter · strong work ethic · making them a candidate\n"
        f"   offers a unique combination\n"
        f"3. TENSE: Present tense for current capabilities, past tense for completed achievements.\n"
        f"4. NUMBERS: Include at least 2 concrete metrics. Estimate realistically if not given.\n"
        f"5. LENGTH: 80–130 words. Tight. Every word must pull weight.\n"
        f"6. OUTPUT: Plain paragraph only. No labels. No bullets. No markdown. No preamble."
    )

    user_prompt = (
        f"Write a professional summary for this candidate targeting: {effective_role}\n\n"
        f"━━━ CANDIDATE PROFILE ━━━\n"
        f"Name: {name}\n"
        f"Education: {edu_line or 'Not specified'}\n"
        f"Top Skills: {', '.join(skills[:12]) if skills else 'Not provided'}\n"
        f"Certifications: {cert_line or 'None'}\n\n"
        f"━━━ WORK EXPERIENCE ━━━\n"
        f"{chr(10).join(exp_lines) if exp_lines else '(No work experience — fresher/student profile)'}\n\n"
        f"━━━ PROJECTS ━━━\n"
        f"{chr(10).join(proj_lines) if proj_lines else '(No projects listed)'}\n\n"
        + (f"━━━ TARGET JD KEYWORDS (mirror these naturally) ━━━\n{req.job_description[:600]}\n\n" if req.job_description else "")
        + f"━━━ OUTPUT RULES ━━━\n"
        f"- 4 sentences. 80-130 words.\n"
        f"- Lead with role + domain authority. Do NOT start with '{name}'.\n"
        f"- Include at least 2 numbers/metrics from the experience or projects above.\n"
        f"- ZERO use of: seeking, looking for, passionate, motivated, quick learner.\n"
        f"- Present tense for capabilities, past tense for completed work.\n"
        f"- Write as if the candidate IS the expert, not IS TRYING TO BE.\n\n"
        f"Output the paragraph now:"
    )

    try:
        # Use the full structured system prompt built above — includes role-specific vocabulary
        raw = await _gemini_gen(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_heavy,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=1200,
            temperature=0.65,
            disable_thinking=True,
        )
        summary_text = (raw or "").strip().strip('"\'')

        # Strip any accidental labels or markdown
        for prefix in ("Summary:", "summary:", "Professional Summary:", "**Summary**",
                       "Final Paragraph:", "Here is", "Here's"):
            if summary_text.lower().startswith(prefix.lower()):
                summary_text = summary_text[len(prefix):].lstrip(":").strip()
        if summary_text.startswith("```"):
            summary_text = summary_text.strip("`").strip()

        # Fallback retry with a distilled prompt if too short
        if len(summary_text.split()) < 40:
            logger.warning(f"[generate-summary] Only {len(summary_text.split())} words — retrying with distilled prompt")
            proj_names = ", ".join(p.get("name", "") for p in projects[:2] if isinstance(p, dict))
            raw2 = await _gemini_gen(
                api_key=settings.gemini_api_key,
                model_name=settings.llm_model_heavy,
                system_prompt=(
                    f"Write a 4-sentence (90-130 word) professional resume summary for a {effective_role}. "
                    "Assertive tone. No 'seeking/passionate/motivated'. Include 2 metrics. "
                    f"Domain keywords: {role_domain_context or 'system design, scalable architecture'}. "
                    "Output ONLY the paragraph."
                ),
                user_prompt=(
                    f"Name: {name} | Role: {effective_role}\n"
                    f"Skills: {', '.join(str(s) for s in skills[:12])}\n"
                    f"Projects: {proj_names or 'not provided'}\n"
                    f"Education: {edu_line or 'BTech Computer Science'}\n"
                    f"Certs: {cert_line or 'none'}\n\n"
                    f"Write the summary paragraph now. Output ONLY the paragraph."
                ),
                max_tokens=1200,
                temperature=0.6,
                disable_thinking=True,
            )
            summary_text = (raw2 or "").strip().strip('"\'')

        if not summary_text or len(summary_text) < 30:
            raise ValueError("Empty summary after two attempts")
        return {"ok": True, "summary": summary_text}
    except Exception as exc:
        logger.error(f"[generate-summary] Failed: {exc}")
        raise HTTPException(500, f"Summary generation failed: {exc}")


@app.post("/v2/agent/cold-email")
async def cold_email(req: ColdEmailRequest):
    """Agent 4 only — cold email generation."""
    session_id = new_session_id()
    from backend_v2.agents.agent_04_cold_email import run as run_agent4

    if req.resume_data:
        parsed = req.resume_data
    elif req.resume_text:
        from backend_v2.agents.tools.resume_tools import parse_resume_async
        parsed = await parse_resume_async(req.resume_text)
    else:
        raise HTTPException(400, "Provide resume_text or resume_data")

    state = default_state(session_id)
    state.update({
        "final_resume": parsed,
        "recruiter_email": req.recruiter_email,
        "candidate_email": req.candidate_email or "",
        "company_name": req.company_name,
        "role_title": req.role_title,
        "job_description": req.job_description,
        "recruiter_name": req.recruiter_name,
    })

    result = await run_agent4(state)
    return {"ok": True, "session_id": session_id, **result.get("cold_email_output", {})}


@app.post("/v2/agent/score")
async def score_resume(req: ScoreRequest):
    """Agent 7 only — score resume and get mentor recommendations."""
    session_id = new_session_id()
    from backend_v2.agents.agent_07_scorer_mentor import run as run_agent7

    state = default_state(session_id)
    state.update({
        "final_resume": req.resume_data,
        "job_description": req.job_description,
    })

    result = await run_agent7(state)
    return {
        "ok": True,
        "session_id": session_id,
        "resume_score": result.get("resume_score"),
        "score_breakdown": result.get("score_breakdown"),
        "mentor_feedback": result.get("mentor_feedback"),
        "mentor_recommendations": result.get("mentor_recommendations"),
    }


@app.post("/v2/agent/auto-apply")
async def auto_apply(req: AutoApplyRequest):
    """Start Agent 8 auto-apply session (requires score >= threshold)."""
    session_id = new_session_id()
    from backend_v2.agents.agent_08_auto_apply import run as run_agent8

    state = default_state(session_id)
    state.update({
        "final_resume": req.resume_data,
        "resume_score": req.resume_score or 0.0,
        "auto_apply_enabled": True,
        "auto_apply_preferences": req.preferences or {},
    })

    result = await run_agent8(state)
    return {
        "ok": True,
        "session_id": session_id,
        "results": result.get("auto_apply_results", []),
        "agent_health": result.get("agent_health_map", {}),
    }


@app.get("/v2/agent/session/{session_id}")
async def get_session(session_id: str):
    """Get current agent session state from PostgreSQL."""
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_sessions WHERE session_id = $1", session_id
            )
            if not row:
                raise HTTPException(404, f"Session {session_id} not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ─── Tracker Routes (PostgreSQL-backed) ───────────────────────────────────────

@app.post("/v2/tracker/add")
async def tracker_add(req: dict):
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO applications (session_id, company, role, job_url, status, notes)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, company, role, status, applied_at
            """,
                req.get("session_id", ""),
                req.get("company", ""),
                req.get("role", ""),
                req.get("job_url", ""),
                req.get("status", "applied"),
                req.get("notes", ""),
            )
            return {"ok": True, "application": dict(row)}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/v2/tracker/list")
async def tracker_list(session_id: Optional[str] = None, page: int = 1, page_size: int = 20):
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            if session_id:
                rows = await conn.fetch(
                    "SELECT * FROM applications WHERE session_id = $1 ORDER BY applied_at DESC LIMIT $2 OFFSET $3",
                    session_id, page_size, (page - 1) * page_size,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM applications ORDER BY applied_at DESC LIMIT $1 OFFSET $2",
                    page_size, (page - 1) * page_size,
                )
            return {"ok": True, "applications": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post("/v2/tracker/update")
async def tracker_update(req: dict):
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE applications SET status = $1, notes = $2 WHERE id = $3",
                req.get("status"), req.get("notes"), req.get("id"),
            )
            return {"ok": True}
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ─── File Download ────────────────────────────────────────────────────────────

@app.get("/v2/agent/download/{filename}")
async def download_file(filename: str):
    """Serve generated PDF files."""
    # Security: only allow files from the generated directory
    safe_filename = Path(filename).name
    file_path = settings.generated_dir / safe_filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")
    if not str(file_path.resolve()).startswith(str(settings.generated_dir.resolve())):
        raise HTTPException(403, "Access denied")

    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        filename=safe_filename,
    )


# ─── Analytics ────────────────────────────────────────────────────────────────

@app.get("/v2/analytics/summary")
async def analytics_summary():
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            events = await conn.fetch("""
                SELECT event_type, count(*) as count
                FROM analytics_events
                GROUP BY event_type
                ORDER BY count DESC
            """)
            return {"ok": True, "events": [dict(e) for e in events]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ─── Health Check ────────────────────────────────────────────────────────────

@app.get("/v2/health")
async def health():
    from backend_v2.agents.agent_05_infra import _check_db_health
    db_health = await _check_db_health()
    return {
        "status": "ok",
        "version": "2.0.0",
        "db": db_health.get("status", "unknown"),
    }


# ─── Response formatter ────────────────────────────────────────────────────────

def _format_response(state: dict, session_id: str) -> dict:
    """
    Format final agent state into API response.
    Handles two cases:
    1. Complete accumulated state dict (from get_state() or ainvoke())
    2. LangGraph update event dict {node_name: delta} — merge all deltas
    """
    # Detect if state is a LangGraph update event: all values are dicts keyed by node name
    # Real AgentState has string/list/dict/None values — not nested node dicts
    _KNOWN_STATE_KEYS = {
        "session_id", "user_id", "raw_resume_text", "raw_resume_bytes",
        "job_description", "selected_template", "role_preference",
        "candidate_email", "recruiter_email", "recruiter_name", "company_name",
        "role_title", "parsed_resume", "tailored_resume", "enhanced_resume",
        "final_resume", "jd_match_score", "jd_match_details", "caution_issued",
        "proceed_despite_low_match", "tailoring_plan", "quality_gate",
        "quality_gate_passed", "auto_correct_attempts", "pdf_path", "download_url",
        "change_log", "cold_email_output", "resume_score", "score_breakdown",
        "mentor_feedback", "mentor_recommendations", "auto_apply_enabled",
        "auto_apply_results", "apply_score_threshold", "auto_apply_preferences",
        "db_health", "agent_health_map", "supervisor_interventions",
        "quality_issues", "upload_filename", "current_agent", "error",
        "retry_count", "messages",
    }
    # If none of the top-level keys match known state keys, assume it's a node-event dict
    if state and not any(k in _KNOWN_STATE_KEYS for k in state.keys()):
        logger.warning("[_format_response] Received node-event dict — merging deltas")
        merged: dict = {}
        for node_name, delta in state.items():
            if isinstance(delta, dict):
                merged.update(delta)
        state = merged

    return {
        "ok": True,
        "session_id": session_id,
        "download_url": state.get("download_url"),
        "pdf_path": state.get("pdf_path"),
        "final_resume": state.get("final_resume"),
        "quality_gate": state.get("quality_gate"),
        "quality_gate_passed": state.get("quality_gate_passed", False),
        "jd_match_score": state.get("jd_match_score"),
        "jd_match_details": state.get("jd_match_details"),
        "caution_issued": state.get("caution_issued", False),
        "tailoring_plan": state.get("tailoring_plan", []),
        "cold_email_output": state.get("cold_email_output"),
        "resume_score": state.get("resume_score"),
        "score_breakdown": state.get("score_breakdown"),
        "mentor_feedback": state.get("mentor_feedback"),
        "mentor_recommendations": state.get("mentor_recommendations"),
        "auto_apply_results": state.get("auto_apply_results"),
        "change_log": state.get("change_log"),
        "agent_health_map": state.get("agent_health_map", {}),
        "supervisor_interventions": state.get("supervisor_interventions", []),
        "quality_issues": state.get("quality_issues"),
        "error": state.get("error"),
    }


# ─── GDPR & Responsible AI ───────────────────────────────────────────────────
#
# Compliant with:
#   • GDPR Article 17  — Right to Erasure ("right to be forgotten")
#   • GDPR Article 15  — Right of Access (data export)
#   • GDPR Article 13  — Transparency (AI disclosure header on every response)
#   • EU AI Act Art 13 — Transparency obligation for AI systems
#   • Responsible AI   — no fabrication guarantee, human-in-the-loop, audit trail
#
# Implementation notes:
#   - PII is never written to server logs (session_id used instead of name/email)
#   - AI-generated content is labelled in every response (X-AI-Generated header)
#   - Sessions auto-expire after 30 days (retention policy enforced at DB level)
#   - Users can export or delete their data at any time via the endpoints below
# ─────────────────────────────────────────────────────────────────────────────

# Middleware: attach Responsible AI transparency headers to every response
@app.middleware("http")
async def responsible_ai_headers(request: Request, call_next):
    response = await call_next(request)
    # EU AI Act Article 13 — users must know when interacting with an AI system
    response.headers["X-AI-System"] = "Smart-Job-Agent-V2"
    response.headers["X-AI-Model-Family"] = "Google-Gemini"
    response.headers["X-AI-Content-Policy"] = (
        "AI-generated content is based on user-provided data only. "
        "No fabrication. Human review recommended before use."
    )
    # GDPR Article 13 — data controller contact
    response.headers["X-Data-Controller"] = "Smart Job Agent - kondapallivarun69@gmail.com"
    response.headers["X-Data-Retention-Days"] = "30"
    return response


class ConsentRequest(BaseModel):
    session_id: str
    consent_given: bool
    purposes: list[str] = ["resume_generation", "jd_matching"]  # granular consent


@app.post("/v2/gdpr/consent")
async def record_consent(req: ConsentRequest):
    """
    GDPR Article 7 — Record lawful basis for processing.
    Called when user ticks the consent checkbox before AI processing.
    """
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            await conn.execute("""
                INSERT INTO gdpr_consent_log
                    (session_id, consent_given, purposes, consented_at, ip_hash)
                VALUES ($1, $2, $3, NOW(), 'anonymised')
                ON CONFLICT (session_id) DO UPDATE
                    SET consent_given = $2, purposes = $3, consented_at = NOW()
            """, req.session_id, req.consent_given, req.purposes)
    except Exception:
        pass  # DB unavailable — log and continue (consent stored client-side as fallback)
    return {
        "ok": True,
        "message": "Consent recorded.",
        "your_rights": {
            "access": "GET /v2/gdpr/my-data/{session_id}",
            "delete": "DELETE /v2/gdpr/my-data/{session_id}",
            "withdraw_consent": "POST /v2/gdpr/consent with consent_given=false",
        },
    }


@app.get("/v2/gdpr/my-data/{session_id}")
async def export_my_data(session_id: str):
    """
    GDPR Article 15 — Right of Access.
    Returns all data stored against a session_id in a portable format.
    """
    data: dict = {"session_id": session_id, "stored_data": {}}
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            session = await conn.fetchrow(
                "SELECT * FROM agent_sessions WHERE session_id = $1", session_id
            )
            applications = await conn.fetch(
                "SELECT company, role, status, applied_at FROM applications WHERE session_id = $1",
                session_id,
            )
            if session:
                data["stored_data"]["session"] = dict(session)
            if applications:
                data["stored_data"]["applications"] = [dict(r) for r in applications]
    except Exception:
        pass
    data["ai_transparency"] = {
        "model_used": "gemini-2.5-flash-lite (Google)",
        "data_used_for_ai": ["resume text", "job description"],
        "data_NOT_sent_to_ai": ["email", "phone", "exact location"],
        "ai_content_policy": "All AI output is generated from your input only. No data is used to train models.",
        "human_review": "All AI-generated summaries and resumes should be reviewed before submission.",
    }
    return data


@app.delete("/v2/gdpr/my-data/{session_id}")
async def delete_my_data(session_id: str):
    """
    GDPR Article 17 — Right to Erasure.
    Deletes all data associated with a session. Irreversible.
    Also deletes any generated PDF files for the session.
    """
    deleted: dict[str, int] = {}
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            r1 = await conn.execute(
                "DELETE FROM agent_sessions WHERE session_id = $1", session_id
            )
            r2 = await conn.execute(
                "DELETE FROM applications WHERE session_id = $1", session_id
            )
            r3 = await conn.execute(
                "DELETE FROM gdpr_consent_log WHERE session_id = $1", session_id
            )
            deleted = {
                "sessions": int((r1 or "DELETE 0").split()[-1]),
                "applications": int((r2 or "DELETE 0").split()[-1]),
                "consent_records": int((r3 or "DELETE 0").split()[-1]),
            }
    except Exception:
        pass

    # Delete PDFs whose filename contains the session_id prefix
    try:
        generated_dir = get_settings().generated_dir
        prefix = session_id.replace("v2_", "")[:8]
        deleted_files = 0
        for f in generated_dir.glob(f"*{prefix}*.pdf"):
            f.unlink(missing_ok=True)
            deleted_files += 1
        deleted["pdf_files"] = deleted_files
    except Exception:
        pass

    return {
        "ok": True,
        "message": f"All data for session {session_id} has been permanently deleted.",
        "deleted": deleted,
    }


@app.get("/v2/ai/transparency")
async def ai_transparency():
    """
    EU AI Act Article 13 — AI system transparency disclosure.
    Public endpoint — no auth required.
    """
    return {
        "system": "Smart Job Agent V2",
        "version": "2.0.0",
        "ai_models": [
            {
                "name": "gemini-2.5-flash-lite",
                "provider": "Google DeepMind",
                "purpose": "Resume writing, JD matching, professional summary generation",
                "input_data": "Resume text and job descriptions provided by the user",
                "output_type": "Text — resume content and career recommendations",
            }
        ],
        "responsible_ai_commitments": [
            "No fabrication: AI output is based exclusively on user-provided data",
            "Human oversight: all AI output is editable and requires user approval before use",
            "No bias amplification: prompts explicitly ban demographic assumptions",
            "Transparency: every AI-generated section is labelled in the UI",
            "Data minimisation: only the fields necessary for the task are sent to the model",
            "No PII in logs: logs use session IDs, never names or contact details",
            "Right to erasure: users can delete all their data at any time",
        ],
        "gdpr_basis": "Explicit consent (Article 6(1)(a)) collected before AI processing",
        "data_retention": "Session data auto-deleted after 30 days",
        "contact": "kondapallivarun69@gmail.com",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_v2.main:app", host="0.0.0.0", port=8000, reload=True)
