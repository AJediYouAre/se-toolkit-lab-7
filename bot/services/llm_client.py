"""LLM client — handles chat completions with tool calling.

Uses the OpenAI-compatible API at LLM_API_BASE_URL.
"""

import json
import sys
import time
from typing import Any

import httpx

from bot.config import LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL

_client = httpx.Client(
    base_url=LLM_API_BASE_URL,
    headers={
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=60.0,
)

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2


class LlmError(Exception):
    """Raised when the LLM API returns an error or is unreachable."""
    pass


def _is_fallback_response(data: dict) -> bool:
    """Check if the response is a fallback from the proxy (not a real LLM response)."""
    # The proxy returns id="fallback" with zero tokens when the backend is unreachable
    if data.get("id") == "fallback":
        return True
    usage = data.get("usage", {})
    if usage.get("total_tokens", 0) == 0 and usage.get("prompt_tokens", 0) == 0:
        return True
    return False


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Send a chat completion request with retry on fallback responses.

    Returns the full response dict. If the LLM wants to call tools,
    the response message will contain 'tool_calls'.

    Retries up to _MAX_RETRIES times if the proxy returns a fallback response.
    """
    payload: dict[str, Any] = {
        "model": LLM_API_MODEL,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    for attempt in range(_MAX_RETRIES):
        try:
            resp = _client.post("/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise LlmError(f"LLM error: {exc}") from exc

        if resp.status_code >= 400:
            raise LlmError(
                f"LLM error: HTTP {resp.status_code} {resp.reason_phrase}"
            )

        data = resp.json()

        if not _is_fallback_response(data):
            return data

        # Fallback detected — retry after a short delay
        debug(f"[llm] Fallback response detected (attempt {attempt + 1}/{_MAX_RETRIES}), retrying...")
        if attempt < _MAX_RETRIES - 1:
            time.sleep(_RETRY_DELAY_SECONDS)

    # All retries exhausted — return the last response, let the caller handle it
    return resp.json()


def extract_message(response: dict) -> dict:
    """Extract the assistant message from a chat completion response."""
    return response["choices"][0]["message"]


def has_tool_calls(message: dict) -> bool:
    """Check if the LLM response contains tool calls."""
    return bool(message.get("tool_calls"))


def debug(msg: str) -> None:
    """Print debug info to stderr (visible in --test mode)."""
    print(msg, file=sys.stderr)
