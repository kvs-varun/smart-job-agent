import os
from typing import Dict, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def call_llm(system: str, user: str, temperature: float = 0.2, max_tokens: int = 800) -> Dict:
    """LLM wrapper (disabled by default).

    This project must have a robust rule-based fallback. Therefore this function:
    - Checks for an API key
    - If missing, returns {"ok": False, "text": None, "reason": "no_api_key"}

    Integration points:
    - resume_tailor.py can call this to rewrite bullets, but must enforce
      "do not invent" rules and be able to run without LLM.

    To enable later:
    - Add provider SDK (OpenAI/Azure/etc.)
    - Read endpoint + key from env
    - Keep prompts in code (auditable)
    """

    api_key = os.getenv("LLM_API_KEY") or os.getenv("SMART_JOB_AGENT_LLM_API_KEY")
    if not api_key:
        return {"ok": False, "text": None, "reason": "no_api_key"}

    return {"ok": False, "text": None, "reason": "llm_not_configured"}
