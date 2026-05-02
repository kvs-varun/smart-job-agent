"""
Smart Job Agent V2 — Configuration
All settings loaded from environment via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────
    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")

    # Model assignments per agent (override in .env if needed)
    # gemini-1.5-flash = 1,500 req/day free tier (gemini-flash-latest maps to
    # gemini-3-flash which has only 20 req/day — not usable for development)
    llm_model_heavy: str = "gemini-2.5-flash-lite"  # Agents 1, 2, 3, 7
    llm_model_fast: str = "gemini-2.5-flash-lite"  # Agents 4, 5, 6, 8

    # ── Database ─────────────────────────────────────────
    database_url: str = Field(
        "postgresql+asyncpg://smartjob:smartjob@localhost:5432/smartjob_v2",
        alias="DATABASE_URL",
    )
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_db: str = Field("smartjob_v2", alias="POSTGRES_DB")
    postgres_user: str = Field("smartjob", alias="POSTGRES_USER")
    postgres_password: str = Field("smartjob", alias="POSTGRES_PASSWORD")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")

    # Connection pool
    db_pool_min: int = 5
    db_pool_max: int = 20
    db_command_timeout: int = 60

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # ── LangSmith (optional) ──────────────────────────────
    langchain_api_key: str = Field("", alias="LANGCHAIN_API_KEY")
    langchain_tracing_v2: bool = Field(False, alias="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field("smart-job-agent-v2", alias="LANGCHAIN_PROJECT")

    # ── Agent 8 — Auto-Apply credentials ──────────────────
    linkedin_email: str = Field("", alias="LINKEDIN_EMAIL")
    linkedin_password: str = Field("", alias="LINKEDIN_PASSWORD")
    naukri_email: str = Field("", alias="NAUKRI_EMAIL")
    naukri_password: str = Field("", alias="NAUKRI_PASSWORD")
    apply_score_threshold: float = Field(7.0, alias="APPLY_SCORE_THRESHOLD")

    # ── Backend URLs ──────────────────────────────────────
    v1_flask_url: str = Field("http://127.0.0.1:5000", alias="FLASK_BASE_URL")
    v2_api_url: str = Field("http://127.0.0.1:8000", alias="V2_API_URL")

    # ── Storage ───────────────────────────────────────────
    uploads_dir: Path = ROOT_DIR / "backend" / "uploads"
    generated_dir: Path = ROOT_DIR / "backend" / "static" / "generated"
    knowledge_dir: Path = ROOT_DIR / "knowledge"

    # ── Optional S3 backups ────────────────────────────────
    aws_s3_bucket: str = Field("", alias="AWS_S3_BUCKET")
    aws_access_key_id: str = Field("", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field("", alias="AWS_SECRET_ACCESS_KEY")

    # ── Feature flags ─────────────────────────────────────
    enable_auto_apply: bool = True
    enable_langsmith: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
