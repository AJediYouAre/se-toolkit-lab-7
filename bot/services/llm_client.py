"""LLM client — handles chat completions with tool calling.

Uses the OpenAI-compatible API at LLM_API_BASE_URL.
"""

import json
import sys
from typing import Any

import httpx

from bot.config import LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL

_client = httpx.Client(
    base_url=LLM_API_BASE_URL,
    headers={
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=30.0,
)


class LlmError(Exception):
    """Raised when the LLM API returns an error or is unreachable."""
    pass


def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Send a chat completion request.

    Returns the full response dict. If the LLM wants to call tools,
    the response message will contain 'tool_calls'.
    """
    payload: dict[str, Any] = {
        "model": LLM_API_MODEL,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    try:
        resp = _client.post("/chat/completions", json=payload)
    except httpx.HTTPError as exc:
        raise LlmError(f"LLM error: {exc}") from exc

    if resp.status_code >= 400:
        raise LlmError(
            f"LLM error: HTTP {resp.status_code} {resp.reason_phrase}"
        )

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
