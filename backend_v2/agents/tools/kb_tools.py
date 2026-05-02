"""
Knowledge Base tools — thin wrappers around V1 KnowledgeBase.
Reuses backend/knowledge_base.py and all knowledge/*.json files unchanged.
"""
import sys
from pathlib import Path

# Allow importing from V1 backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from knowledge_base import KnowledgeBase  # type: ignore

_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        from backend_v2.config import get_settings
        settings = get_settings()
        _kb = KnowledgeBase(knowledge_dir=str(settings.knowledge_dir))
    return _kb


def get_role_knowledge(role_key: str) -> dict:
    return get_kb().get_role_knowledge(role_key) or {}


def get_ats_keywords(role_key: str) -> dict:
    return get_kb().get_keywords_for_role(role_key) or {}


def infer_role(text: str) -> str:
    """Infer role key from job description or resume text.
    V1 infer_role_key() returns (role_key, confidence) tuple — extract just the string.
    """
    result = get_kb().infer_role_key(text)
    if isinstance(result, tuple):
        return result[0] or "backend_fresher"
    return result or "backend_fresher"


def expand_synonyms(terms: list[str], role_key: str) -> list[str]:
    return get_kb().expand_synonyms(terms, role_key)


def get_indian_hiring_patterns() -> dict:
    return get_kb().indian_hiring_patterns() or {}


def get_cold_email_templates() -> dict:
    return get_kb().cold_email_templates() or {}


def get_resume_best_practices() -> dict:
    return get_kb().resume_best_practices() or {}
