"""Optional OpenAI client (plain HTTP via httpx). Used only when
OPENAI_API_KEY is set. Any failure returns None so callers fall back to the
deterministic demo path."""
from __future__ import annotations

import json
import logging

import httpx

from ..config import get_settings

log = logging.getLogger("mykshema.llm")

GROUNDING_RULES = (
    "You are MyKshema, an assistant for a personal health record prototype. Use ONLY the JSON records provided. "
    "If information is absent, say it is not recorded. Never invent diagnoses, medications, results or "
    "prescriptions. Never prescribe, stop or change medicines; suggest discussing with a qualified clinician. "
    "Cite record ids in square brackets like [doc_seed0003] when you use them. Be concise. All data is synthetic."
)


def chat(messages: list[dict], *, json_mode: bool = False, max_tokens: int = 700) -> str | None:
    s = get_settings()
    if not s.openai_api_key:
        return None
    body: dict = {"model": s.openai_model, "messages": messages, "temperature": 0.1, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        resp = httpx.post(
            f"{s.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {s.openai_api_key}"},
            json=body,
            timeout=45,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:  # network, auth, quota, schema
        log.warning("OpenAI call failed, using demo fallback: %s", exc)
        return None


def chat_json(messages: list[dict], **kw) -> dict | None:
    raw = chat(messages, json_mode=True, **kw)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
