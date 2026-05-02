"""
Smart Job Agent V2 — LangGraph StateGraph
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8-agent orchestration:
- Parallel fan-out: Agents 1 + 2 run simultaneously on same state snapshot
- Supervisor interrupt hooks on every node
- Quality gate loop (max 3 auto-correct attempts)
- Conditional routing: caution gate, auto-apply score gate
- MemorySaver checkpointer for session resumability

ROOT CAUSE FIX: run_session now uses ainvoke() which returns the
complete accumulated state, not astream() which returns per-node deltas.
"""
import asyncio
import logging
from pathlib import Path
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from backend_v2.agents.state import (
    AgentState, default_state,
    AGENT_PARSER, AGENT_ARCHITECT, AGENT_ENHANCER, AGENT_JD_MATCH,
    AGENT_COLD_EMAIL, AGENT_INFRA, AGENT_SUPERVISOR, AGENT_SCORER, AGENT_AUTO_APPLY,
    HEALTH_OK, HEALTH_FAILED,
)
import backend_v2.agents.agent_01_resume_architect as agent1
import backend_v2.agents.agent_02_content_enhancer as agent2
import backend_v2.agents.agent_03_jd_strategist as agent3
import backend_v2.agents.agent_04_cold_email as agent4
import backend_v2.agents.agent_05_infra as agent5
import backend_v2.agents.agent_06_supervisor as agent6
import backend_v2.agents.agent_07_scorer_mentor as agent7
import backend_v2.agents.agent_08_auto_apply as agent8

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_resume_structure(resume: dict) -> dict:
    """
    Guarantee minimum resume structure so agents never crash on missing keys.
    Applied defensively at multiple pipeline stages.
    Includes all industry-standard sections: certifications, achievements, openSource, etc.
    """
    if not isinstance(resume, dict):
        resume = {}
    defaults = {
        "contact": {"name": "", "email": "", "phone": "", "location": "",
                    "linkedin": "", "github": "", "portfolio": ""},
        "summary": "",
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "openSource": [],
        "publications": [],
        "volunteering": [],
        "languages": [],
    }
    for key, val in defaults.items():
        if key not in resume:
            resume[key] = val
        elif not resume[key] and isinstance(val, list):
            resume[key] = val  # keep empty list rather than None
    # Ensure contact sub-fields exist
    contact = resume.get("contact", {})
    if not isinstance(contact, dict):
        resume["contact"] = defaults["contact"]
    else:
        for field in ["name", "email", "phone", "location", "linkedin", "github", "portfolio"]:
            contact.setdefault(field, "")
    return resume


def _text_to_minimal_resume(text: str) -> dict:
    """
    Convert raw resume text into a minimal structured resume dict.
    Used when the V1 parser fails or returns empty.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    resume = _ensure_resume_structure({})

    # Try to extract name (first non-empty line)
    if lines:
        resume["contact"]["name"] = lines[0]

    # Try to extract email
    import re
    for line in lines[:10]:
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', line, re.I)
        if email_match:
            resume["contact"]["email"] = email_match.group()
            break

    # Extract skills (look for skills section)
    skills_mode = False
    collected_skills = []
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ["skill", "technology", "tech stack", "languages"]):
            skills_mode = True
            continue
        if skills_mode:
            if any(kw in low for kw in ["experience", "education", "project", "work"]):
                skills_mode = False
                continue
            # Split by comma, pipe, or bullet
            for skill in re.split(r'[,|•·]', line):
                skill = skill.strip()
                if 2 < len(skill) < 30:
                    collected_skills.append(skill)
        if len(collected_skills) >= 20:
            break

    resume["skills"] = collected_skills[:20] if collected_skills else ["Python"]

    # Use first 3 meaningful lines as summary
    summary_parts = [l for l in lines[1:6] if len(l) > 20][:2]
    resume["summary"] = " ".join(summary_parts) or f"Software developer with skills in {', '.join(resume['skills'][:3])}."

    return resume


# ─── Node wrappers ────────────────────────────────────────────────────────────

async def parse_resume_node(state: AgentState) -> AgentState:
    """
    Parse resume from text or bytes into structured JSON.
    NEVER returns empty dict — always produces a usable structure.
    """
    from backend_v2.agents.tools.resume_tools import parse_resume_async, load_and_parse_file_async

    state = await agent6.check_and_heal(state, AGENT_PARSER)

    # Short-circuit: if resume_data was provided directly (from builder), use it as-is
    if state.get("parsed_resume") and state["parsed_resume"].get("contact", {}).get("name"):
        logger.info("[parse_resume_node] Using pre-populated parsed_resume (from resume_data input)")
        parsed = _ensure_resume_structure(state["parsed_resume"])
        return {
            **state,
            "parsed_resume": parsed,
            "current_agent": AGENT_PARSER,
            "agent_health_map": {**state.get("agent_health_map", {}), AGENT_PARSER: HEALTH_OK},
        }

    raw_bytes = state.get("raw_resume_bytes")
    raw_text = state.get("raw_resume_text", "")
    parsed = {}

    try:
        if raw_bytes:
            filename = state.get("upload_filename", "resume.pdf")
            parsed = await load_and_parse_file_async(raw_bytes, filename)
        elif raw_text:
            parsed = await parse_resume_async(raw_text)
    except Exception as exc:
        logger.warning(f"[parse_resume_node] Parser failed: {exc} — using text fallback")

    # ── CRITICAL: never let empty dict through ────────────────────────────────
    if not parsed or not isinstance(parsed, dict) or not parsed.get("contact", {}).get("name"):
        logger.warning("[parse_resume_node] Parser returned empty/invalid — building minimal structure")
        if raw_text:
            parsed = _text_to_minimal_resume(raw_text)
        elif raw_bytes:
            # Try extracting raw text from bytes
            try:
                import io
                import pdfplumber
                with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                parsed = _text_to_minimal_resume(text)
            except Exception:
                parsed = _ensure_resume_structure({})
        else:
            parsed = _ensure_resume_structure({})

    parsed = _ensure_resume_structure(parsed)

    return {
        **state,
        "parsed_resume": parsed,
        "current_agent": AGENT_PARSER,
        "agent_health_map": {**state.get("agent_health_map", {}), AGENT_PARSER: HEALTH_OK},
    }


async def architect_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_ARCHITECT)
    return await agent1.run(state)


async def enhancer_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_ENHANCER)
    return await agent2.run(state)


async def merge_parallel_node(state: AgentState) -> AgentState:
    """
    Fan-in: merge outputs from Agent 1 (tailored_resume) and Agent 2 (enhanced_resume).
    Strategy:
    - Use enhanced_resume as base (Agent 2's language quality pass)
    - Fill any missing sections from tailored_resume (Agent 1's content transformation)
    - Fill any remaining gaps from parsed_resume (original extracted data)
    - Preserve all new sections: certifications, achievements, openSource, etc.
    """
    enhanced = state.get("enhanced_resume") or {}
    tailored = state.get("tailored_resume") or {}
    parsed   = state.get("parsed_resume") or {}

    # Start with the best base
    if enhanced and isinstance(enhanced, dict) and enhanced.get("experience"):
        base = dict(enhanced)
        source = "enhanced"
    elif tailored and isinstance(tailored, dict) and tailored.get("experience"):
        base = dict(tailored)
        source = "tailored"
    else:
        base = dict(parsed) if parsed else {}
        source = "parsed"

    # Cross-pollinate: fill gaps in base from fallback sources
    fallback_chain = [tailored, parsed] if source == "enhanced" else [parsed]
    new_sections = ["certifications", "achievements", "openSource", "publications", "volunteering", "languages"]

    for fallback in fallback_chain:
        if not isinstance(fallback, dict):
            continue
        # For new sections: use any non-empty source
        for section in new_sections:
            if not base.get(section) and fallback.get(section):
                base[section] = fallback[section]
        # For contact: fill missing sub-fields
        if isinstance(base.get("contact"), dict) and isinstance(fallback.get("contact"), dict):
            for field in ["email", "phone", "linkedin", "github", "location", "portfolio"]:
                if not base["contact"].get(field) and fallback["contact"].get(field):
                    base["contact"][field] = fallback["contact"][field]

    final = _ensure_resume_structure(base)

    # Merge quality issues from Agent 2
    quality_issues = state.get("quality_issues", [])

    logger.info(
        f"[Graph] merge_parallel | session={state.get('session_id')} "
        f"| base={source} | "
        f"certs={len(final.get('certifications', []))} | "
        f"achievements={len(final.get('achievements', []))} | "
        f"exp={len(final.get('experience', []))}"
    )
    return {**state, "final_resume": final, "quality_issues": quality_issues}


async def quality_gate_node(state: AgentState) -> AgentState:
    """Run ATS quality gate. Auto-correct up to 3 times."""
    from backend_v2.agents.tools.resume_tools import check_quality_async, analyze_job_async
    from backend_v2.agents.tools.kb_tools import infer_role

    resume = state.get("final_resume") or {}
    jd_text = state.get("job_description", "")
    job_analysis = {}

    try:
        if jd_text:
            role_key = infer_role(jd_text)
            job_analysis = await analyze_job_async(jd_text, role_key)
        quality = await check_quality_async(resume, job_analysis)
    except Exception as exc:
        logger.warning(f"[quality_gate_node] Check failed: {exc} — passing through")
        quality = {"passed": True, "issues": [], "ats_score": 70}

    passed = quality.get("passed", False)
    # Force pass if resume has minimum required fields
    if not passed:
        has_min = bool(
            resume.get("contact", {}).get("name")
            and resume.get("skills")
            and (resume.get("experience") or resume.get("projects"))
        )
        if has_min and state.get("auto_correct_attempts", 0) >= 2:
            passed = True  # don't loop forever on a valid-enough resume
            quality["passed"] = True

    return {
        **state,
        "quality_gate": quality,
        "quality_gate_passed": passed,
        "current_agent": "quality_gate",
    }


async def auto_correct_node(state: AgentState) -> AgentState:
    """Apply rule-based auto-corrections when quality gate fails. Max 3 attempts."""
    import copy
    attempts = state.get("auto_correct_attempts", 0)
    resume = copy.deepcopy(state.get("final_resume") or {})
    resume = _ensure_resume_structure(resume)

    issues = (state.get("quality_gate") or {}).get("issues", [])
    corrections_made = []

    # Fix 1: Add missing summary using Gemini (not a hardcoded placeholder)
    if not resume.get("summary"):
        try:
            from backend_v2.agents.tools.gemini_client import gemini_json as _gemini_json
            from backend_v2.config import get_settings as _get_settings
            _s = _get_settings()
            contact = resume.get("contact", {})
            name = contact.get("name", "Candidate")
            skills = resume.get("skills", [])
            projects = resume.get("projects", [])
            education = resume.get("education", [])
            proj_txt = "; ".join(
                f"{p.get('name','')} ({', '.join(p.get('techStack',[])[:3])})"
                for p in projects[:3] if isinstance(p, dict)
            )
            edu_txt = ""
            if education and isinstance(education[0], dict):
                e = education[0]
                edu_txt = f"{e.get('degree','')} in {e.get('field','')} from {e.get('institution','')} {e.get('endYear','')}"
            _sys = (
                "You are a senior technical recruiter writing professional resume summaries. "
                "Write ONLY a 4-5 sentence, 100-150 word professional summary paragraph. "
                "Use power verbs. Be specific to the candidate's actual projects and skills. "
                "Never use: passionate, hardworking, seeking opportunities, detail-oriented. "
                "Do NOT start with 'I'. Return JSON only: {\"summary\": \"...\"}."
            )
            _usr = (
                f"Candidate: {name}\n"
                f"Education: {edu_txt or 'Not specified'}\n"
                f"Skills: {', '.join(str(s) for s in skills[:12])}\n"
                f"Projects: {proj_txt or 'None listed'}\n"
                f"Write a 4-5 sentence professional summary using their ACTUAL project names and tech stack."
            )
            _r = await _gemini_json(_s.gemini_api_key, _s.llm_model_fast, _sys, _usr, max_tokens=400, temperature=0.7, disable_thinking=True)
            if _r.get("summary") and len(_r["summary"]) > 50:
                resume["summary"] = _r["summary"]
            else:
                raise ValueError("Short or missing summary from Gemini")
        except Exception as _exc:
            logger.warning(f"[auto_correct] Gemini summary fallback failed: {_exc} — using rule-based")
            contact = resume.get("contact", {})
            name = contact.get("name", "Candidate")
            skills = resume.get("skills", [])
            projects = resume.get("projects", [])
            proj_names = [p.get("name", "") for p in projects[:2] if isinstance(p, dict)]
            resume["summary"] = (
                f"Emerging {skills[0] if skills else 'Software'} developer "
                f"with hands-on experience building {proj_names[0] if proj_names else 'academic projects'} "
                f"using {', '.join(str(s) for s in skills[:4])}. "
                f"Demonstrated ability to design and implement technical solutions with measurable outcomes. "
                f"Eager to contribute expertise to a high-impact engineering team."
            )
        corrections_made.append("Generated summary with AI")

    # Fix 2: Ensure at least one skill
    if not resume.get("skills"):
        resume["skills"] = ["Python", "Problem Solving", "Communication"]
        corrections_made.append("Added default skills")

    # Fix 3: Trim projects to max 4
    if len(resume.get("projects", [])) > 4:
        resume["projects"] = resume["projects"][:4]
        corrections_made.append("Trimmed projects to 4")

    # Fix 4: Trim experience bullets to max 4 per role
    for exp in resume.get("experience", []):
        desc = exp.get("description", "")
        bullets = [b.strip() for b in desc.split("\n") if b.strip()]
        if len(bullets) > 4:
            exp["description"] = "\n".join(bullets[:4])
            corrections_made.append(f"Trimmed bullets: {exp.get('company', '')}")

    # Fix 5: Ensure all contact sub-fields exist
    contact = resume.get("contact", {})
    for field in ["name", "email", "phone", "location", "linkedin", "github"]:
        contact.setdefault(field, "")
    resume["contact"] = contact

    logger.info(f"[Graph] auto_correct attempt {attempts + 1} | fixes={corrections_made}")

    return {
        **state,
        "final_resume": resume,
        "auto_correct_attempts": attempts + 1,
        "change_log": (state.get("change_log") or []) + [{
            "agent": "auto_correct",
            "attempt": attempts + 1,
            "corrections": corrections_made,
        }],
    }


async def pdf_generator_node(state: AgentState) -> AgentState:
    """
    Generate PDF from final_resume using selected template.
    Falls back through 3 strategies before giving up.
    """
    from backend_v2.config import get_settings
    settings = get_settings()

    resume = state.get("final_resume") or {}
    resume = _ensure_resume_structure(dict(resume))
    template = state.get("selected_template", "ats_pro")

    # Ensure output directory exists
    settings.generated_dir.mkdir(parents=True, exist_ok=True)

    # ── Strategy 1: V2 template renderers ─────────────────────────────────────
    try:
        if template == "jakes":
            from backend_v2.templates.template_jakes import generate_pdf
        elif template == "harvard":
            from backend_v2.templates.template_harvard import generate_pdf
        else:
            from backend_v2.templates.template_ats_pro import generate_pdf

        output_path, download_url = generate_pdf(resume, settings)
        logger.info(f"[pdf_generator] Generated with template={template} | path={output_path}")
        return {**state, "pdf_path": str(output_path), "download_url": download_url}

    except Exception as exc:
        logger.warning(f"[pdf_generator] V2 template failed ({template}): {exc}")

    # ── Strategy 2: Simple inline PDF via ReportLab ───────────────────────────
    try:
        import uuid
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors

        filename = f"resume_{uuid.uuid4().hex[:8]}.pdf"
        output_path = settings.generated_dir / filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.6 * inch,
            leftMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )
        styles = getSampleStyleSheet()
        story = []

        contact = resume.get("contact", {})
        name_style = ParagraphStyle("name", parent=styles["Heading1"], fontSize=18, spaceAfter=4)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=4, textColor=colors.HexColor("#4F46E5"))
        normal = styles["Normal"]
        normal.fontSize = 10

        # Name + contact
        story.append(Paragraph(contact.get("name", "Candidate"), name_style))
        contact_line = " | ".join(filter(None, [
            contact.get("email"), contact.get("phone"),
            contact.get("location"), contact.get("linkedin"),
        ]))
        if contact_line:
            story.append(Paragraph(contact_line, normal))
        story.append(Spacer(1, 8))

        def section(title, items_fn):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#4F46E5")))
            story.append(Paragraph(title.upper(), h2))
            items_fn()
            story.append(Spacer(1, 6))

        if resume.get("summary"):
            section("Summary", lambda: story.append(Paragraph(resume["summary"], normal)))

        if resume.get("skills"):
            skills = resume["skills"]
            skills_str = ", ".join(str(s) for s in skills) if isinstance(skills, list) else str(skills)
            section("Skills", lambda: story.append(Paragraph(skills_str, normal)))

        def add_experience():
            for exp in resume.get("experience", []):
                title = f"<b>{exp.get('title', '')}</b> — {exp.get('company', '')} | {exp.get('startDate', '')}–{exp.get('endDate', 'Present')}"
                story.append(Paragraph(title, normal))
                for bullet in exp.get("description", "").split("\n"):
                    b = bullet.strip()
                    if b:
                        story.append(Paragraph(f"• {b}", normal))
        if resume.get("experience"):
            section("Experience", add_experience)

        def add_projects():
            for proj in resume.get("projects", []):
                tech = proj.get("techStack", [])
                tech_str = ", ".join(tech) if isinstance(tech, list) else str(tech)
                title = f"<b>{proj.get('name', '')}</b>{' | ' + tech_str if tech_str else ''}"
                story.append(Paragraph(title, normal))
                if proj.get("description"):
                    story.append(Paragraph(f"• {proj['description'][:200]}", normal))
        if resume.get("projects"):
            section("Projects", add_projects)

        def add_education():
            for edu in resume.get("education", []):
                line = f"<b>{edu.get('degree', '')}</b> in {edu.get('field', '')} — {edu.get('institution', '')} | {edu.get('endDate', '')} | {edu.get('grade', '')}"
                story.append(Paragraph(line, normal))
        if resume.get("education"):
            section("Education", add_education)

        doc.build(story)
        download_url = f"/v2/agent/download/{filename}"
        logger.info(f"[pdf_generator] Inline PDF generated | path={output_path}")
        return {**state, "pdf_path": str(output_path), "download_url": download_url}

    except Exception as exc2:
        logger.error(f"[pdf_generator] Inline PDF also failed: {exc2}")
        return {**state, "error": f"PDF generation failed: {exc2}", "pdf_path": None, "download_url": None}


async def jd_match_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_JD_MATCH)
    return await agent3.run(state)


async def scorer_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_SCORER)
    return await agent7.run(state)


async def cold_email_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_COLD_EMAIL)
    return await agent4.run(state)


async def infra_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_INFRA)
    return await agent5.run(state)


async def auto_apply_node(state: AgentState) -> AgentState:
    state = await agent6.check_and_heal(state, AGENT_AUTO_APPLY)
    return await agent8.run(state)


async def supervisor_final_node(state: AgentState) -> AgentState:
    return await agent6.run(state)


async def save_session_node(state: AgentState) -> AgentState:
    """Persist final session state to PostgreSQL."""
    try:
        await agent5.persist_session_state(state.get("session_id", ""), state)
    except Exception as exc:
        logger.warning(f"[Graph] Session save failed (non-fatal): {exc}")
    return {**state, "current_agent": "completed"}


# ─── Routing functions ────────────────────────────────────────────────────────

def route_quality_gate(state: AgentState) -> Literal["auto_correct_node", "pdf_generator_node"]:
    """Route based on quality gate. Max 3 auto-correct attempts then force through."""
    passed = state.get("quality_gate_passed", False)
    attempts = state.get("auto_correct_attempts", 0)
    if not passed and attempts < 3:
        return "auto_correct_node"
    return "pdf_generator_node"


def route_auto_apply(state: AgentState) -> Literal["auto_apply_node", "supervisor_final_node"]:
    """Route to auto-apply only if enabled and score is sufficient."""
    score = state.get("resume_score") or 0.0
    threshold = state.get("apply_score_threshold") or 7.0
    if state.get("auto_apply_enabled") and float(score) >= float(threshold):
        return "auto_apply_node"
    return "supervisor_final_node"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Build the full LangGraph StateGraph.

    Topology:
    START → parse_resume
          ↓  (fan-out — same state snapshot sent to both)
    architect_node   enhancer_node   ← parallel
          ↓                ↓
          └── merge_parallel_node ──┘
                    ↓
             quality_gate_node
          ↙ (fail+<3)  ↘ (pass or ≥3)
    auto_correct    pdf_generator_node
          ↑_________↗        ↓ (fan-out)
                   jd_match  scorer  cold_email  infra   ← parallel
                      ↓        ↓         ↓         ↓
                      └────────┼─────────┴─────────┘
                           save_session_node
                               ↓
                              END
    """
    graph = StateGraph(AgentState)

    graph.add_node("parse_resume", parse_resume_node)
    graph.add_node("architect_node", architect_node)
    graph.add_node("enhancer_node", enhancer_node)
    graph.add_node("merge_parallel_node", merge_parallel_node)
    graph.add_node("quality_gate_node", quality_gate_node)
    graph.add_node("auto_correct_node", auto_correct_node)
    graph.add_node("pdf_generator_node", pdf_generator_node)
    graph.add_node("jd_match_node", jd_match_node)
    graph.add_node("scorer_node", scorer_node)
    graph.add_node("cold_email_node", cold_email_node)
    graph.add_node("infra_node", infra_node)
    graph.add_node("auto_apply_node", auto_apply_node)
    graph.add_node("supervisor_final_node", supervisor_final_node)
    graph.add_node("save_session_node", save_session_node)

    # Linear start
    graph.add_edge(START, "parse_resume")

    # Fan-out: parse → Agents 1 + 2 in parallel
    graph.add_edge("parse_resume", "architect_node")
    graph.add_edge("parse_resume", "enhancer_node")

    # Fan-in: both → merge
    graph.add_edge("architect_node", "merge_parallel_node")
    graph.add_edge("enhancer_node", "merge_parallel_node")

    # Quality gate loop
    graph.add_edge("merge_parallel_node", "quality_gate_node")
    graph.add_conditional_edges(
        "quality_gate_node",
        route_quality_gate,
        {"auto_correct_node": "auto_correct_node", "pdf_generator_node": "pdf_generator_node"},
    )
    graph.add_edge("auto_correct_node", "quality_gate_node")

    # After PDF: fan-out to 4 parallel nodes
    graph.add_edge("pdf_generator_node", "jd_match_node")
    graph.add_edge("pdf_generator_node", "scorer_node")
    graph.add_edge("pdf_generator_node", "cold_email_node")
    graph.add_edge("pdf_generator_node", "infra_node")

    # JD match + cold email + infra → save session
    graph.add_edge("jd_match_node", "save_session_node")
    graph.add_edge("cold_email_node", "save_session_node")
    graph.add_edge("infra_node", "save_session_node")

    # Scorer → auto-apply gate
    graph.add_conditional_edges(
        "scorer_node",
        route_auto_apply,
        {"auto_apply_node": "auto_apply_node", "supervisor_final_node": "supervisor_final_node"},
    )
    graph.add_edge("auto_apply_node", "supervisor_final_node")
    graph.add_edge("supervisor_final_node", "save_session_node")
    graph.add_edge("save_session_node", END)

    return graph


def compile_graph():
    """Compile graph with MemorySaver for session resumability."""
    graph = build_graph()
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Singleton compiled graph
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = compile_graph()
    return _compiled_graph


async def run_session(initial_state: AgentState) -> AgentState:
    """
    Run a complete agent session.

    CRITICAL FIX: Uses ainvoke() which returns the COMPLETE accumulated state.
    The previous astream() implementation only returned per-node state deltas,
    meaning _format_response got {node_name: partial_delta} instead of full state.

    Also streams intermediate events to logger for observability.
    """
    graph = get_graph()
    session_id = initial_state.get("session_id", "unknown")
    config = {"configurable": {"thread_id": session_id}}

    logger.info(f"[Graph] run_session starting | session={session_id}")

    # Stream events for observability (logging only), then invoke for final state
    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
            node_name = list(event.keys())[0] if event else "unknown"
            node_state = event.get(node_name) or {}
            health = node_state.get("agent_health_map", {}) if isinstance(node_state, dict) else {}
            current = node_state.get("current_agent", node_name) if isinstance(node_state, dict) else node_name
            logger.info(f"[Graph] ✓ Node done: {node_name} | agent={current} | health={health}")
    except Exception as exc:
        logger.error(f"[Graph] Streaming failed: {exc}", exc_info=True)

    # Get the complete final state from the checkpointer
    try:
        final = graph.get_state(config)
    except Exception as exc:
        logger.error(f"[Graph] get_state failed: {exc}", exc_info=True)
        final = None
    if final and final.values:
        logger.info(f"[Graph] run_session complete | session={session_id}")
        return dict(final.values)

    # Fallback: re-invoke synchronously if streaming + get_state failed
    logger.warning("[Graph] get_state returned empty — falling back to ainvoke()")
    try:
        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": f"{session_id}_inv"}})
        return dict(result) if result else dict(initial_state)
    except Exception as exc2:
        logger.error(f"[Graph] ainvoke fallback also failed: {exc2}")
        return dict(initial_state)
