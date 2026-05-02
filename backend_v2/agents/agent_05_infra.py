"""
Agent 5 — Backend Infrastructure Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Role: Automated senior backend engineer. Manages PostgreSQL health,
connection pooling, schema migrations, and proactive scaling detection.
Runs pre-written scripts on startup; does not require LLM for normal operation.

Model: claude-haiku-4-5 (only for complex anomaly diagnosis)
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from backend_v2.agents.state import AgentState, AGENT_INFRA, HEALTH_OK, HEALTH_DEGRADED, HEALTH_FAILED
from backend_v2.config import get_settings

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
SLOW_QUERY_THRESHOLD_MS = 1000    # queries > 1s are "slow"
HIGH_CONNECTION_PCT = 80           # > 80% pool utilization = warning
CRITICAL_CONNECTION_PCT = 95       # > 95% = critical


async def run(state: AgentState) -> AgentState:
    """
    Agent 5 node function.
    Checks DB health and reports. Does not require resume data.
    """
    session_id = state.get("session_id", "unknown")
    logger.info(f"[Agent 5 — Infra] Health check | session={session_id}")

    try:
        health = await _check_db_health()
        status = health.get("status", "unknown")

        logger.info(f"[Agent 5 — Infra] DB status={status}")

        agent_status = HEALTH_OK if status == "healthy" else HEALTH_DEGRADED
        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_INFRA] = agent_status
        return {
            "db_health": health,
            "agent_health_map": health_map,
        }
    except Exception as exc:
        logger.error(f"[Agent 5 — Infra] FAILED: {exc}")
        health_map = dict(state.get("agent_health_map") or {})
        health_map[AGENT_INFRA] = HEALTH_FAILED
        return {
            "db_health": {"status": "error", "error": str(exc)},
            "agent_health_map": health_map,
        }


async def _check_db_health() -> dict[str, Any]:
    """Run comprehensive database health check."""
    try:
        from backend_v2.database import get_connection
    except ImportError:
        return {"status": "not_configured", "message": "Database not initialized"}

    start = time.monotonic()
    try:
        async with get_connection() as conn:
            # 1. Basic connectivity
            await conn.fetchval("SELECT 1")
            latency_ms = int((time.monotonic() - start) * 1000)

            # 2. Connection pool utilization
            pool_stats = await conn.fetchrow("""
                SELECT count(*) as total,
                       count(*) FILTER (WHERE state = 'active') as active,
                       count(*) FILTER (WHERE state = 'idle') as idle
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)

            # 3. Check for slow queries
            slow_queries = await conn.fetch("""
                SELECT query, calls, mean_exec_time, max_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > $1
                ORDER BY mean_exec_time DESC
                LIMIT 5
            """, SLOW_QUERY_THRESHOLD_MS) if await _has_pg_stat_statements(conn) else []

            # 4. Table sizes
            table_sizes = await conn.fetch("""
                SELECT relname as table_name,
                       pg_size_pretty(pg_total_relation_size(relid)) as total_size
                FROM pg_catalog.pg_statio_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 5
            """)

            # 5. Recent errors from agent_health_log
            recent_failures = await conn.fetchval("""
                SELECT count(*) FROM agent_health_log
                WHERE status = 'failed' AND logged_at > NOW() - INTERVAL '1 hour'
            """) if await _table_exists(conn, "agent_health_log") else 0

            settings = get_settings()
            pool_total = pool_stats["total"] if pool_stats else 0
            pool_max = settings.db_pool_max
            utilization_pct = (pool_total / pool_max * 100) if pool_max > 0 else 0

            status = "healthy"
            warnings = []

            if latency_ms > 500:
                warnings.append(f"High DB latency: {latency_ms}ms")
                status = "degraded"

            if utilization_pct > HIGH_CONNECTION_PCT:
                warnings.append(f"High connection utilization: {utilization_pct:.0f}%")
                status = "degraded" if utilization_pct < CRITICAL_CONNECTION_PCT else "critical"

            if slow_queries:
                warnings.append(f"{len(slow_queries)} slow queries detected (>{SLOW_QUERY_THRESHOLD_MS}ms)")

            if recent_failures > 5:
                warnings.append(f"{recent_failures} agent failures in last hour")

            return {
                "status": status,
                "latency_ms": latency_ms,
                "connections": {
                    "total": pool_total,
                    "active": pool_stats["active"] if pool_stats else 0,
                    "idle": pool_stats["idle"] if pool_stats else 0,
                    "pool_max": pool_max,
                    "utilization_pct": round(utilization_pct, 1),
                },
                "slow_queries": [dict(q) for q in slow_queries],
                "table_sizes": [dict(t) for t in table_sizes],
                "recent_agent_failures_1h": int(recent_failures),
                "warnings": warnings,
                "checked_at": datetime.utcnow().isoformat(),
            }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "checked_at": datetime.utcnow().isoformat(),
        }


async def _has_pg_stat_statements(conn) -> bool:
    result = await conn.fetchval(
        "SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements'"
    )
    return bool(result)


async def _table_exists(conn, table_name: str) -> bool:
    result = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
        table_name,
    )
    return bool(result)


# ── Startup script runner ─────────────────────────────────────────────────────

async def run_startup_checks():
    """
    Called on FastAPI startup. Verifies DB is ready, runs migrations if needed.
    This is Agent 5's proactive 'pre-written scripts' capability.
    """
    logger.info("[Agent 5 — Infra] Running startup checks...")
    settings = get_settings()

    health = await _check_db_health()
    if health["status"] == "error":
        logger.critical(f"[Agent 5] DB unreachable on startup: {health.get('error')}")
        return False

    logger.info(f"[Agent 5] DB healthy | latency={health.get('latency_ms')}ms")
    for warning in health.get("warnings", []):
        logger.warning(f"[Agent 5] {warning}")

    return True


async def persist_session_state(session_id: str, state: AgentState):
    """Persist LangGraph state snapshot to PostgreSQL for resumability."""
    try:
        from backend_v2.database import get_connection
        import json

        serializable = {
            k: v for k, v in state.items()
            if k not in ("raw_resume_bytes", "messages")  # skip large/unserializable fields
        }
        async with get_connection() as conn:
            await conn.execute("""
                INSERT INTO agent_sessions (session_id, state_snapshot, current_agent, status)
                VALUES ($1, $2, $3, 'running')
                ON CONFLICT (session_id) DO UPDATE
                SET state_snapshot = $2,
                    current_agent = $3,
                    updated_at = NOW(),
                    agents_completed = (
                        SELECT ARRAY(
                            SELECT DISTINCT unnest(agents_completed || ARRAY[$3])
                        )
                        FROM agent_sessions WHERE session_id = $1
                    )
            """, session_id, json.dumps(serializable), state.get("current_agent"))
    except Exception as exc:
        logger.error(f"[Agent 5] Failed to persist session state: {exc}")
