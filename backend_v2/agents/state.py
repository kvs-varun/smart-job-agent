"""
Smart Job Agent V2 — Shared AgentState TypedDict
Passed through every node in the LangGraph StateGraph.
"""
from __future__ import annotations
import operator
from typing import Optional, Dict, List, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def _merge_dicts(a: Dict, b: Dict) -> Dict:
    """Merge two dicts — used as reducer for agent_health_map so parallel nodes can all write."""
    merged = dict(a or {})
    merged.update(b or {})
    return merged

# ─── Template identifiers ────────────────────────────────────────────────────
TEMPLATE_JAKES = "jakes"
TEMPLATE_HARVARD = "harvard"
TEMPLATE_ATS_PRO = "ats_pro"
ALL_TEMPLATES = [TEMPLATE_JAKES, TEMPLATE_HARVARD, TEMPLATE_ATS_PRO]

# ─── Agent names (used as keys in health_map) ─────────────────────────────────
AGENT_PARSER = "parse_resume"
AGENT_ARCHITECT = "resume_architect"
AGENT_ENHANCER = "content_enhancer"
AGENT_JD_MATCH = "jd_strategist"
AGENT_COLD_EMAIL = "cold_email"
AGENT_INFRA = "backend_infra"
AGENT_SUPERVISOR = "supervisor"
AGENT_SCORER = "scorer_mentor"
AGENT_AUTO_APPLY = "auto_apply"

# Agent health status values
HEALTH_OK = "ok"
HEALTH_DEGRADED = "degraded"
HEALTH_FAILED = "failed"
HEALTH_RECOVERED = "recovered"
HEALTH_FALLBACK = "fallback_used"


class AgentState(TypedDict, total=False):
    # ── Session metadata ──────────────────────────────────────────────────────
    session_id: str
    user_id: Optional[str]

    # ── Input ─────────────────────────────────────────────────────────────────
    raw_resume_text: Optional[str]
    raw_resume_bytes: Optional[bytes]
    job_description: Optional[str]
    selected_template: str              # jakes | harvard | ats_pro
    role_preference: Optional[str]
    candidate_email: Optional[str]
    recruiter_email: Optional[str]
    recruiter_name: Optional[str]
    company_name: Optional[str]
    role_title: Optional[str]

    # ── Parsed / Built ────────────────────────────────────────────────────────
    parsed_resume: Optional[Dict[str, Any]]
    tailored_resume: Optional[Dict[str, Any]]    # Agent 1 output
    enhanced_resume: Optional[Dict[str, Any]]    # Agent 2 output (parallel)
    final_resume: Optional[Dict[str, Any]]       # merged: tailored + enhanced

    # ── JD Match (Agent 3) ────────────────────────────────────────────────────
    jd_match_score: Optional[float]              # 0–100
    jd_match_details: Optional[Dict[str, Any]]  # full report
    caution_issued: bool                         # score < 60%
    proceed_despite_low_match: bool              # user override
    tailoring_plan: Optional[List[Dict[str, Any]]]  # gap-closing steps

    # ── Quality Gate ──────────────────────────────────────────────────────────
    quality_gate: Optional[Dict[str, Any]]       # from ats_simulator
    quality_gate_passed: bool
    auto_correct_attempts: int                   # max 3

    # ── PDF / Output ──────────────────────────────────────────────────────────
    pdf_path: Optional[str]
    download_url: Optional[str]
    change_log: Optional[List[Dict[str, Any]]]

    # ── Cold Email (Agent 4) ──────────────────────────────────────────────────
    cold_email_output: Optional[Dict[str, Any]]
    # {subject, body, mailto_link, gmail_url, framework_used, word_count}

    # ── Score & Mentor (Agent 7) ──────────────────────────────────────────────
    resume_score: Optional[float]                # 0.0–10.0
    score_breakdown: Optional[Dict[str, float]]
    # {ats_compliance, content_quality, skill_alignment, profile_strength, presentation}
    mentor_feedback: Optional[str]
    mentor_recommendations: Optional[List[Dict[str, Any]]]
    # [{title, url, provider, duration_hours, free, relevance_score, domain}]

    # ── Auto-Apply (Agent 8) ──────────────────────────────────────────────────
    auto_apply_enabled: bool
    auto_apply_results: Optional[List[Dict[str, Any]]]
    apply_score_threshold: float                 # default 7.0/10
    auto_apply_preferences: Optional[Dict[str, Any]]
    # {target_roles, location, experience_level, platforms, max_applications}

    # ── Infrastructure (Agent 5) ──────────────────────────────────────────────
    db_health: Optional[Dict[str, Any]]
    # {status, connections, pool_utilization, slow_queries}

    # ── Supervisor (Agent 6) ──────────────────────────────────────────────────
    # Annotated with merge reducer so parallel nodes can all write their health status
    agent_health_map: Annotated[Dict[str, str], _merge_dicts]
    # Annotated with list concat so parallel nodes can all append interventions
    supervisor_interventions: Annotated[List[str], operator.add]

    # ── Quality issues (from Agent 2) ─────────────────────────────────────────
    quality_issues: Optional[List[Dict[str, Any]]]

    # ── Upload metadata ───────────────────────────────────────────────────────
    upload_filename: Optional[str]

    # ── Control flow ──────────────────────────────────────────────────────────
    current_agent: Optional[str]
    error: Optional[str]
    retry_count: int
    messages: Annotated[List[BaseMessage], add_messages]


def default_state(session_id: str, selected_template: str = TEMPLATE_ATS_PRO) -> AgentState:
    """Return a clean AgentState with safe defaults for a new session."""
    return AgentState(
        session_id=session_id,
        user_id=None,
        raw_resume_text=None,
        raw_resume_bytes=None,
        job_description=None,
        selected_template=selected_template,
        role_preference=None,
        candidate_email=None,
        recruiter_email=None,
        recruiter_name=None,
        company_name=None,
        role_title=None,
        parsed_resume=None,
        tailored_resume=None,
        enhanced_resume=None,
        final_resume=None,
        jd_match_score=None,
        jd_match_details=None,
        caution_issued=False,
        proceed_despite_low_match=False,
        tailoring_plan=None,
        quality_gate=None,
        quality_gate_passed=False,
        auto_correct_attempts=0,
        pdf_path=None,
        download_url=None,
        change_log=None,
        cold_email_output=None,
        resume_score=None,
        score_breakdown=None,
        mentor_feedback=None,
        mentor_recommendations=None,
        auto_apply_enabled=False,
        auto_apply_results=None,
        apply_score_threshold=7.0,
        auto_apply_preferences=None,
        db_health={},
        agent_health_map={},
        supervisor_interventions=[],
        quality_issues=None,
        upload_filename=None,
        current_agent=None,
        error=None,
        retry_count=0,
        messages=[],
    )
