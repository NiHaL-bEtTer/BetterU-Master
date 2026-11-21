"""LLM access through the OpenAI-compatible API.

Groq, OpenRouter, Together, Ollama, vLLM and many others speak this protocol,
so switching provider is a config change (LLM_BASE_URL / LLM_API_KEY / LLM_MODEL).
"""

from functools import lru_cache

from openai import OpenAI

from betteru.config import get_settings


@lru_cache
def get_llm() -> OpenAI:
    s = get_settings()
    return OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key or "missing", timeout=60, max_retries=2)


def model_options() -> dict:
    """Extra request options for the configured model (e.g. reasoning effort)."""
    effort = get_settings().llm_reasoning_effort
    return {"reasoning_effort": effort} if effort else {}


def complete(prompt: str, *, system: str | None = None, fast: bool = True, max_tokens: int = 300,
             json_mode: bool = False, temperature: float = 0.0) -> str:
    """One-shot, non-streaming completion for small internal jobs."""
    s = get_settings()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = get_llm().chat.completions.create(
        model=s.llm_fast_model if fast else s.llm_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        **model_options(),
        **kwargs,
    )
    return (resp.choices[0].message.content or "").strip()
