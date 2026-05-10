"""Debug script to test LLM tool calling loop step by step."""
import json
import sys

import httpx

from bot.config import LLM_API_KEY, LLM_API_BASE_URL, LLM_API_MODEL
from bot.services.tools import TOOLS, call_tool

client = httpx.Client(
    base_url=LLM_API_BASE_URL,
    headers={
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=120.0,
)

messages = [
    {
        "role": "system",
        "content": "You are an LMS bot assistant. Use tools to answer questions about labs, students, groups, and scores. Always call tools for data questions.",
    },
    {"role": "user", "content": "which group is doing best in lab 3"},
]

for round_num in range(5):
    print(f"\n=== Round {round_num + 1} ===", file=sys.stderr)
    print(f"Messages count: {len(messages)}", file=sys.stderr)

    payload = {"model": LLM_API_MODEL, "messages": messages, "tools": TOOLS}
    try:
        resp = client.post("/chat/completions", json=payload)
        print(f"HTTP status: {resp.status_code}", file=sys.stderr)
        if resp.status_code >= 400:
            print(f"Error body: {resp.text[:500]}", file=sys.stderr)
            break
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        break

    data = resp.json()
    msg = data["choices"][0]["message"]
    print(f"finish_reason: {data['choices'][0].get('finish_reason')}", file=sys.stderr)
    content = msg.get("content") or ""
    print(f"content: {content[:200]}", file=sys.stderr)

    tool_calls = msg.get("tool_calls", [])
    if not tool_calls:
        print("No tool calls — LLM responded directly", file=sys.stderr)
        print(msg.get("content", "No content"))
        break

    print(f"Tool calls: {len(tool_calls)}", file=sys.stderr)
    messages.append(msg)

    for tc in tool_calls:
        func = tc["function"]
        name = func["name"]
        raw_args = func.get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_args

        print(f"  -> {name}({args})", file=sys.stderr)
        result = call_tool(name, args)
        truncated = result[:2000]
        print(f"  <- {truncated[:200]}", file=sys.stderr)

        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": truncated,
        })
