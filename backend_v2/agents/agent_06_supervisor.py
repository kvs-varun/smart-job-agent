"""
Agent 6 — Supervisor / Doctor Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Master monitor and healer for all other agents. Runs as an interrupt
node before every other node in the LangGraph graph. Knows every agent's
capabilities, failure modes, and recovery strategy. Takes initiative when
any agent is degraded or failed.

Model: claude-haiku-4-5 (low-latency; must not slow down the pipeline)
"""
import logging
import time
from typing import Any

from backend_v2.agents.tools.gemini_client import gemini_generate

from backend_v2.agents.state import (
    AgentState,
    AGENT_SUPERVISOR, AGENT_ARCHITECT, AGENT_ENHANCER, AGENT_JD_MATCH,
    AGENT_COLD_EMAIL, AGENT_INFRA, AGENT_SCORER, AGENT_AUTO_APPLY,
    HEALTH_OK, HEALTH_DEGRADED, HEALTH_FAILED, HEALTH_RECOVERED, HEALTH_FALLBACK,
)
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

# Maximum retries before falling back to V1 rule-based logic
MAX_RETRIES = 3

# Agent timeout thresholds (seconds)
AGENT_TIMEOUTS = {
    AGENT_ARCHITECT: 45,
    AGENT_ENHANCER: 45,
    AGENT_JD_MATCH: 30,
    AGENT_COLD_EMAIL: 20,
    AGENT_INFRA: 15,
    AGENT_SCORER: 30,
    AGENT_AUTO_APPLY: 120,
}

# Fallback strategy: what to use when an agent fails
FALLBACK_STRATEGY = {
    AGENT_ARCHITECT: "v1_resume_tailor",
    AGENT_ENHANCER: "passthrough",            # skip, use Agent 1's output
    AGENT_JD_MATCH: "v1_job_matcher",
    AGENT_COLD_EMAIL: "v1_cold_email",
    AGENT_INFRA: "json_fallback",
    AGENT_SCORER: "v1_ats_simulator",
    AGENT_AUTO_APPLY: "skip_with_log",
}


async def check_and_heal(state: AgentState, about_to_run: str) -> AgentState:
    """
    Called BEFORE each agent node executes.
    Checks system health and takes corrective action if needed.
    This is the supervisor's primary intervention point.
    """
    session_id = state.get("session_id", "unknown")
    health_map = dict(state.get("agent_health_map", {}))
    interventions = list(state.get("supervisor_interventions", []))
    retry_count = state.get("retry_count", 0)

    # ── Check if the about-to-run agent has already failed ────────────────────
    agent_status = health_map.get(about_to_run, HEALTH_OK)

    if agent_status == HEALTH_FAILED and retry_count >= MAX_RETRIES:
        intervention = f"SUPERVISOR: {about_to_run} failed {retry_count}x — activating fallback: {FALLBACK_STRATEGY.get(about_to_run, 'skip')}"
        interventions.append(intervention)
        logger.warning(f"[Agent 6 — Supervisor] {intervention}")

        # Apply fallback state modifications
        state = await _apply_fallback(state, about_to_run)
        health_map[about_to_run] = HEALTH_FALLBACK
        health_map[AGENT_SUPERVISOR] = HEALTH_OK

        await _log_intervention(session_id, about_to_run, HEALTH_FAILED, intervention)

        return {**state, "agent_health_map": health_map, "supervisor_interventions": interventions}

    if agent_status == HEALTH_FAILED and retry_count < MAX_RETRIES:
        intervention = f"SUPERVISOR: {about_to_run} failed — scheduling retry {retry_count + 1}/{MAX_RETRIES}"
        interventions.append(intervention)
        logger.info(f"[Agent 6 — Supervisor] {intervention}")

        await _log_intervention(session_id, about_to_run, HEALTH_DEGRADED, intervention)

        return {
            **state,
            "retry_count": retry_count + 1,
            "agent_health_map": health_map,
            "supervisor_interventions": interventions,
        }

    # ── Check for DB health degradation ───────────────────────────────────────
    db_health = state.get("db_health") or {}
    if db_health.get("status") in ("critical", "error"):
        intervention = "SUPERVISOR: DB critical — switching to JSON fallback storage"
        interventions.append(intervention)
        logger.warning(f"[Agent 6 — Supervisor] {intervention}")

    return {
        **state,
        "agent_health_map": {**health_map, AGENT_SUPERVISOR: HEALTH_OK},
        "supervisor_interventions": interventions,
    }


async def run(state: AgentState) -> AgentState:
    """
    Full supervisor scan node — runs at end of pipeline to generate health report.
    """
    session_id = state.get("session_id", "unknown")
    health_map = state.get("agent_health_map", {})

    failed_agents = [a for a, s in health_map.items() if s == HEALTH_FAILED]
    degraded_agents = [a for a, s in health_map.items() if s == HEALTH_DEGRADED]
    ok_agents = [a for a, s in health_map.items() if s == HEALTH_OK]

    logger.info(
        f"[Agent 6 — Supervisor] Session {session_id} summary | "
        f"ok={len(ok_agents)} | degraded={len(degraded_agents)} | failed={len(failed_agents)}"
    )

    if failed_agents:
        # Use LLM for complex failure diagnosis
        diagnosis = await _diagnose_failures(state, failed_agents)
        health_map[AGENT_SUPERVISOR] = HEALTH_OK
        # Return only NEW items to append (supervisor_interventions uses operator.add reducer)
        return {
            "supervisor_interventions": [f"DIAGNOSIS: {diagnosis}"],
            "agent_health_map": health_map,
        }

    health_map[AGENT_SUPERVISOR] = HEALTH_OK
    return {"agent_health_map": health_map}


async def _diagnose_failures(state: AgentState, failed_agents: list[str]) -> str:
    """Use LLM to diagnose complex multi-agent failures."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return f"Agents {failed_agents} failed — API key not configured for LLM diagnosis"

    interventions = state.get("supervisor_interventions", [])
    error_msg = state.get("error", "")

    try:
        return await gemini_generate(
            api_key=settings.gemini_api_key,
            model_name=settings.llm_model_fast,
            system_prompt=(
                "You are an AI system reliability engineer. Diagnose multi-agent failures "
                "and suggest specific recovery actions. Be concise — 3 sentences max."
            ),
            user_prompt=(
                f"Failed agents: {failed_agents}\n"
                f"Error: {error_msg}\n"
                f"Recent interventions: {interventions[-5:]}\n"
                f"DB health: {(state.get('db_health') or {}).get('status', 'unknown')}\n"
                "Diagnose and suggest next step."
            ),
            max_tokens=512,
        )
    except Exception as exc:
        logger.warning(f"[Agent 6] LLM diagnosis failed (non-critical): {exc}")
        return f"Agents {failed_agents} failed — rule-based fallbacks activated. Error: {str(exc)[:100]}"


async def _apply_fallback(state: AgentState, failed_agent: str) -> AgentState:
    """Apply the appropriate fallback for a completely failed agent."""
    strategy = FALLBACK_STRATEGY.get(failed_agent, "skip")
    logger.info(f"[Agent 6] Applying fallback '{strategy}' for {failed_agent}")

    if strategy == "passthrough":
        # Skip the failed agent — use previous agent's output
        return state

    if strategy == "v1_resume_tailor" and not state.get("tailored_resume"):
        try:
            from backend_v2.agents.tools.resume_tools import tailor_resume_async, analyze_job_async
            from backend_v2.agents.tools.kb_tools import infer_role
            parsed = state.get("parsed_resume", {})
            jd_text = state.get("job_description", "")
            role_key = infer_role(jd_text or "")
            job_analysis = await analyze_job_async(jd_text, role_key) if jd_text else {}
            result = await tailor_resume_async(parsed, job_analysis)
            return {**state, "tailored_resume": result.get("tailored_resume", parsed)}
        except Exception as e:
            logger.error(f"[Agent 6] V1 tailor fallback failed: {e}")

    if strategy == "v1_job_matcher" and not state.get("jd_match_score"):
        try:
            from backend_v2.agents.tools.resume_tools import analyze_job_async, compute_match_scores_async
            from backend_v2.agents.tools.kb_tools import infer_role
            resume = state.get("final_resume") or state.get("parsed_resume", {})
            jd_text = state.get("job_description", "")
            if jd_text and resume:
                role_key = infer_role(jd_text)
                job_analysis = await analyze_job_async(jd_text, role_key)
                scores = await compute_match_scores_async(resume, job_analysis)
                return {**state, "jd_match_score": scores.get("overall_score", 0) * 100}
        except Exception as e:
            logger.error(f"[Agent 6] V1 job matcher fallback failed: {e}")

    if strategy == "v1_ats_simulator" and not state.get("resume_score"):
        try:
            from backend_v2.agents.tools.resume_tools import check_quality_async
            resume = state.get("final_resume") or state.get("parsed_resume", {})
            quality = await check_quality_async(resume)
            ats_score = quality.get("ats_score", 0) / 10  # convert 0-100 to 0-10
            return {**state, "resume_score": ats_score}
        except Exception as e:
            logger.error(f"[Agent 6] V1 ATS scorer fallback failed: {e}")

    return state


async def _log_intervention(session_id: str, agent_name: str, status: str, intervention: str):
    """Log supervisor intervention to PostgreSQL."""
    try:
        from backend_v2.database import get_connection
        async with get_connection() as conn:
            await conn.execute("""
                INSERT INTO agent_health_log (session_id, agent_name, status, intervention, message)
                VALUES ($1, $2, $3, $4, $5)
            """, session_id, agent_name, status, intervention, f"Supervisor intervention at {time.time()}")
    except Exception as exc:
        logger.error(f"[Agent 6] Failed to log intervention: {exc}")
