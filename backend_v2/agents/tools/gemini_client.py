"""
Shared Gemini API client — google-genai SDK.
Production-grade: retry logic, robust JSON extraction, timeouts, logging.
"""
import asyncio
import json
import logging
import re
import time
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_RETRIES = 2           # 2 attempts max — 3 × 90s = too slow
RETRY_BASE_DELAY = 1.5   # seconds
DEFAULT_MAX_TOKENS = 4096  # enough for full resume JSON; 8192 makes model slow
DEFAULT_TEMPERATURE = 0.35


@lru_cache(maxsize=4)
def _get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _parse_retry_delay(exc: Exception) -> float | None:
    """
    Extract the server-suggested retryDelay from a 429 error response.
    The Gemini API returns e.g. 'retryDelay': '48s' in the error details.
    Returns seconds as float, or None if not found.
    """
    try:
        msg = str(exc)
        # Look for 'retryDelay': '48s' or "retryDelay": "48s"
        m = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"](\d+(?:\.\d+)?)s['\"]", msg)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """
    Robustly extract JSON from model output.
    Handles: raw JSON, ```json ... ```, ``` ... ```, leading/trailing prose.
    """
    text = text.strip()

    # 1. Try stripping markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        return fence_match.group(1).strip()

    # 2. Try finding outermost { ... } or [ ... ]
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Walk to find matching close bracket, tracking string/escape state
        depth = 0
        in_string = False
        escape_next = False
        end_idx = -1
        for i, ch in enumerate(text[start:], start=start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch in ('\n', '\r', '\t') and in_string:
                # Literal control chars inside a string — treat as string content, not structure
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        if end_idx != -1:
            return text[start:end_idx + 1]

    # 3. Last resort: return as-is
    return text


def _fix_unescaped_control_chars(text: str) -> str:
    """
    Fix literal newlines, tabs, and carriage returns inside JSON string values.
    LLMs often output multiline strings with actual newline chars instead of \\n.
    Walks char-by-char, only replacing inside quoted strings.
    """
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            else:
                result.append(ch)
        else:
            result.append(ch)
    return ''.join(result)


def _repair_truncated_json(text: str) -> str:
    """
    Attempt to repair JSON truncated mid-response (model hit token limit).
    Strategy: find the last complete top-level key-value pair boundary and
    close all open brackets/braces/strings after it.
    """
    # If it already ends with } we don't need to repair
    stripped = text.strip()
    if stripped.endswith('}') or stripped.endswith(']'):
        return text

    # Walk through tracking open structures, close them at the end
    stack = []
    in_string = False
    escape_next = False
    last_safe_pos = 0  # position of last complete comma-separated item

    for i, ch in enumerate(stripped):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in '{[':
            stack.append(ch)
        elif ch in '}]':
            if stack:
                stack.pop()
            if not stack:
                last_safe_pos = i + 1
        elif ch == ',' and len(stack) == 1:
            last_safe_pos = i  # safe to truncate here

    # Truncate to last safe position and close all open structures
    result = stripped[:last_safe_pos].rstrip().rstrip(',')

    # Close all remaining open structures in reverse order
    closers = {'{': '}', '[': ']'}
    for opener in reversed(stack):
        # For arrays that may have been cut, just close them
        if opener == '[':
            result += ']'
        else:
            result += '}'

    return result


def _parse_json_safe(text: str) -> dict:
    """
    Parse JSON with multiple fallback strategies.
    Never raises — returns error dict on complete failure.

    Pipeline (each step tried in order until one succeeds):
    1. Direct parse
    2. Extract JSON block then parse
    3. Fix trailing commas, extract, parse
    4. Fix unescaped control chars (literal newlines in strings), parse
    5. All of the above + truncation repair (close unclosed brackets)
    """
    def _attempt(candidate: str) -> dict | None:
        try:
            return json.loads(candidate)
        except Exception:
            return None

    # Pre-process: fix control chars on raw text first (so _extract_json works correctly)
    text_fixed = _fix_unescaped_control_chars(text)
    extracted = _extract_json(text)
    extracted_fixed = _extract_json(text_fixed)
    # Also fix trailing commas
    no_trailing = re.sub(r',\s*([}\]])', r'\1', extracted_fixed)

    for candidate in [
        text,                                    # 1. raw
        extracted,                               # 2. extracted block (raw)
        text_fixed,                              # 3. control chars fixed (full)
        extracted_fixed,                         # 4. extracted + control chars fixed
        no_trailing,                             # 5. trailing commas removed
        _repair_truncated_json(no_trailing),     # 6. truncation repaired
        _repair_truncated_json(extracted_fixed), # 7. repair without comma fix
    ]:
        result = _attempt(candidate)
        if result is not None:
            return result

    logger.error(f"[GeminiClient] JSON parse failed. Raw output (first 500): {text[:500]}")
    return {"_parse_error": True, "raw_output": text[:2000]}


# ── Core API call ─────────────────────────────────────────────────────────────

async def gemini_generate(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    disable_thinking: bool = True,
) -> str:
    """
    Call Gemini and return raw text. Retries up to MAX_RETRIES on transient errors.
    Runs the sync SDK call in a thread executor (non-blocking).

    disable_thinking=True (default): Disables thinking mode for gemini-2.5-* models
    so that max_output_tokens is fully used for actual response text, not reasoning tokens.
    Set to False for tasks that benefit from deep reasoning (complex analysis).
    """
    client = _get_client(api_key)

    # Build config — suppress thinking for fast text-generation tasks
    config_kwargs: dict[str, Any] = {
        "max_output_tokens": max_tokens,
        "temperature": temperature,
        "system_instruction": system_prompt,
    }
    # For gemini-2.5-* thinking models, disable thinking by setting budget=0
    # This ensures all max_output_tokens go to the actual text response
    if disable_thinking and ("2.5" in model_name or "thinking" in model_name.lower()):
        try:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except AttributeError:
            pass  # Older SDK version — skip thinking config

    config = types.GenerateContentConfig(**config_kwargs)

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=config,
                    ),
                ),
                timeout=40.0,  # 40s per attempt — fast enough for lite model
            )
            # For thinking models (gemini-2.5-*), response.text may be None if only
            # thinking parts exist. Extract text from non-thinking parts explicitly.
            text = response.text
            if not text or not text.strip():
                # Fallback: manually collect text from candidate content parts
                if response.candidates:
                    parts = []
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                part_text = getattr(part, "text", None)
                                # Skip thinking parts (they have thought=True attribute)
                                is_thinking = getattr(part, "thought", False)
                                if part_text and not is_thinking:
                                    parts.append(part_text)
                    text = " ".join(parts).strip()
                if not text or not text.strip():
                    raise ValueError("Empty response from Gemini")
            return text

        except asyncio.TimeoutError:
            last_exc = TimeoutError(f"Gemini call timed out after 90s (attempt {attempt})")
            logger.warning(f"[GeminiClient] Timeout on attempt {attempt}/{MAX_RETRIES}")
        except Exception as exc:
            last_exc = exc
            logger.warning(f"[GeminiClient] Attempt {attempt}/{MAX_RETRIES} failed: {exc}")

        if attempt < MAX_RETRIES:
            # Try to extract retryDelay from the 429 error body — respect server's backoff
            server_delay = _parse_retry_delay(last_exc)
            if server_delay:
                delay = min(server_delay + 1.0, 10.0)  # cap at 10s — don't block endpoint
                logger.info(f"[GeminiClient] Rate limited — waiting {delay:.0f}s (server said {server_delay:.0f}s)...")
            else:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))  # exponential backoff
                logger.info(f"[GeminiClient] Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    raise RuntimeError(f"Gemini API failed after {MAX_RETRIES} attempts: {last_exc}") from last_exc


async def gemini_json(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    disable_thinking: bool = True,
) -> dict:
    """
    Call Gemini and return parsed JSON dict.
    Uses _parse_json_safe — never raises JSONDecodeError.
    """
    # Add explicit JSON instruction to system prompt
    json_system = (
        system_prompt
        + "\n\nCRITICAL: Your response MUST be valid JSON only. "
          "No markdown. No explanation. No code fences. Start with { and end with }."
    )
    raw = await gemini_generate(
        api_key, model_name, json_system, user_prompt, max_tokens, temperature,
        disable_thinking=disable_thinking,
    )
    result = _parse_json_safe(raw)

    if result.get("_parse_error"):
        logger.error(f"[GeminiClient] JSON parse failed — returning error dict")

    return result
