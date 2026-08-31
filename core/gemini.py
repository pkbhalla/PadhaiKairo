"""
core/gemini.py — PadhaiKairo AI Client (Unified google-genai SDK)
Uses the single google-genai SDK for BOTH modes:
  - Vertex AI (Cloud Run prod): Client(vertexai=True, project=..., location=...)
  - API Key  (Local dev):       Client(api_key=...)
Controlled by USE_VERTEX_AI env var.
"""
import os
import time
import threading
from typing import Any, Optional, Dict, List

from core.config import (
    GEMINI_API_KEY,
    MODEL,
    MIN_SECONDS_BETWEEN_CALLS,
    USE_VERTEX_AI,
    GOOGLE_CLOUD_PROJECT,
    VERTEX_AI_LOCATION,
)

_rate_lock = threading.Lock()
_last_call_time = 0.0
_cache: Dict[str, Any] = {}
_client = None

# Model priority pool — confirmed available in asia-south1 (Mumbai)
# Updated: removed deprecated gemini-2.x models (retired/404).
# Current valid models as of 2026.
MODEL_PRIORITY_POOL = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]


def _enforce_rate_limit():
    global _last_call_time
    with _rate_lock:
        elapsed = time.time() - _last_call_time
        if elapsed < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)
        _last_call_time = time.time()


def _get_client():
    """
    Lazy-initialize a single google-genai Client.
    - USE_VERTEX_AI=true  → Vertex AI backend (ADC / service account, no API key needed)
    - USE_VERTEX_AI=false → Gemini Developer API backend (API key)
    """
    global _client
    if _client is not None:
        return _client

    from google import genai

    if USE_VERTEX_AI:
        project = GOOGLE_CLOUD_PROJECT or os.getenv("GOOGLE_CLOUD_PROJECT", "")
        location = VERTEX_AI_LOCATION or os.getenv("VERTEX_AI_LOCATION", "asia-south1")
        _client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        print(f"PadhaiKairo: Initialized google-genai Client in Vertex AI mode (project={project}, location={location})")
    else:
        key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY not set. Set it in .env or use USE_VERTEX_AI=true for Cloud Run."
            )
        _client = genai.Client(api_key=key)
        print("PadhaiKairo: Initialized google-genai Client in API Key mode")

    return _client


def generate_content_with_retry(
    contents: Any,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
    response_schema: Optional[Any] = None,
    response_mime_type: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    use_cache: bool = True,
) -> Any:
    """
    Unified content generation via the google-genai SDK.
    Automatically tries multiple model candidates on failure.

    Works identically for both Vertex AI and API Key backends.
    """
    cache_key = f"{model}:{system_instruction}:{str(contents)[:200]}"
    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    _enforce_rate_limit()

    from google.genai import types

    client = _get_client()
    candidates = list(dict.fromkeys(
        ([model] if model else []) + [MODEL] + MODEL_PRIORITY_POOL
    ))

    # Build config
    cfg: Dict[str, Any] = {}
    if system_instruction:
        cfg["system_instruction"] = system_instruction
    if response_schema:
        cfg["response_schema"] = response_schema
    if response_mime_type:
        cfg["response_mime_type"] = response_mime_type

    # Google GenAI best practice:
    # - Tools present → use Chat.send_message for AFC
    # - No tools     → use Models.generate_content with AFC disabled
    if tools:
        cfg["tools"] = tools
        gen_config = types.GenerateContentConfig(**cfg)
        use_chat_afc = True
    else:
        cfg["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
        gen_config = types.GenerateContentConfig(**cfg)
        use_chat_afc = False

    last_err = None
    for m in candidates:
        if not m:
            continue
        try:
            if use_chat_afc:
                chat = client.chats.create(model=m, config=gen_config)
                resp = chat.send_message(contents)
            else:
                resp = client.models.generate_content(
                    model=m, contents=contents, config=gen_config
                )

            if resp and resp.text:
                if use_cache:
                    _cache[cache_key] = resp
                return resp
        except Exception as e:
            err_str = str(e)
            print(f"Notice: Model {m} error: {err_str[:150]}")
            last_err = e
            # On 404 (model not found) or 429 (rate limit), try next model
            if "404" in err_str or "NOT_FOUND" in err_str:
                continue
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                continue
            # On other errors, stop trying
            break

    if last_err:
        raise last_err
