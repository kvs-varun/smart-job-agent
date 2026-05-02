"""
Smart Job Agent V2 — Async PostgreSQL pool + pgvector init
"""
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
from backend_v2.config import get_settings

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        port=settings.postgres_port,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        command_timeout=settings.db_command_timeout,
        init=_init_connection,
    )
    return _pool


async def _init_connection(conn: asyncpg.Connection):
    """Register vector codec so pgvector lists serialize correctly."""
    await conn.execute("SET application_name = 'smartjob_v2'")


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
