"""
core/gemini.py — PadhaiKairo AI Client
Dual-mode: google-genai (dev/free-tier) vs Vertex AI (Cloud Run prod)
Controlled by USE_VERTEX_AI env var in .env / Cloud Run.
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
_api_client = None

# Free-tier & API Key model priority pool
MODEL_PRIORITY_POOL = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]

# Vertex AI Production model pool (available in asia-south1 / us-central1)
VERTEX_PRIORITY_POOL = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-002",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro",
]


def _enforce_rate_limit():
    global _last_call_time
    with _rate_lock:
        elapsed = time.time() - _last_call_time
        if elapsed < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)
        _last_call_time = time.time()


def _get_api_client():
    global _api_client
    if _api_client is None:
        from google import genai
        key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY not set. Set it in .env or use USE_VERTEX_AI=true.")
        _api_client = genai.Client(api_key=key)
    return _api_client


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
    Unified content generation — same call signature regardless of backend.

    Dev  (USE_VERTEX_AI=false): google-genai SDK + GEMINI_API_KEY
         - When tools are passed: uses Chat.send_message (recommended for AFC)
         - When tools are None  : uses Models.generate_content with AFC disabled
    Prod (USE_VERTEX_AI=true) : Vertex AI SDK + ADC / service account (no API key)
    """
    cache_key = f"{model}:{system_instruction}:{str(contents)[:200]}"
    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    _enforce_rate_limit()

    # ── VERTEX AI MODE (Cloud Run / ADC) ────────────────────────────────────
    if USE_VERTEX_AI:
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig
        except ImportError:
            raise ImportError("Install: pip install google-cloud-aiplatform>=1.60.0")

        if not getattr(generate_content_with_retry, "_vertex_initialized", False):
            vertexai.init(project=GOOGLE_CLOUD_PROJECT, location=VERTEX_AI_LOCATION)
            generate_content_with_retry._vertex_initialized = True

        v_candidates = list(dict.fromkeys(([model] if model else []) + [MODEL] + VERTEX_PRIORITY_POOL))
        prompt_text = contents if isinstance(contents, str) else str(contents)

        gen_dict: Dict[str, Any] = {"temperature": 0.7, "max_output_tokens": 2048}
        if response_mime_type:
            gen_dict["response_mime_type"] = response_mime_type
        generation_config = GenerationConfig(**gen_dict)

        last_v_err = None
        for m in v_candidates:
            if not m: continue
            try:
                vertex_model = GenerativeModel(
                    m,
                    system_instruction=[system_instruction] if system_instruction else None
                )
                response = vertex_model.generate_content(
                    prompt_text,
                    generation_config=generation_config,
                )
                if response and response.text:
                    class _Resp:
                        def __init__(self, t): self.text = t
                    result = _Resp(response.text)
                    if use_cache:
                        _cache[cache_key] = result
            except Exception as e:
                print(f"Notice: Vertex AI model {m} notice: {e}")
                last_v_err = e

        if last_v_err:
            if GEMINI_API_KEY or os.getenv("GEMINI_API_KEY"):
                print("Notice: Vertex AI failed; falling back to GEMINI_API_KEY...")
            else:
                raise last_v_err

    # ── API KEY MODE (Local Dev / Free Tier / Fallback) ──────────────────────
    from google.genai import types

    client = _get_api_client()
    candidates = list(dict.fromkeys(([model] if model else []) + [MODEL] + MODEL_PRIORITY_POOL))

    cfg: Dict[str, Any] = {}
    if system_instruction:
        cfg["system_instruction"] = system_instruction
    if response_schema:
        cfg["response_schema"] = response_schema
    if response_mime_type:
        cfg["response_mime_type"] = response_mime_type

    # Google GenAI best practice:
    # 1. If tools are used, use Chat.send_message for Automatic Function Calling (AFC).
    # 2. If no tools are used, explicitly disable AFC to silence direct Models.generate_content warning.
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
        if not m: continue
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
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"Notice: Rate limit/quota hit on {m}, backing off...")
                last_err = e
            elif "404" in err or "NOT_FOUND" in err:
                last_err = e
            else:
                last_err = e
                break

    if last_err:
        raise last_err
