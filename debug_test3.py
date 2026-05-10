"""Debug: trace the full tool-calling loop for 'sync the data'."""
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

SYSTEM_PROMPT = """You are an LMS (Learning Management System) bot assistant. You help students and instructors query lab data.

You have access to tools that fetch real data from the backend. When a user asks a question:
1. Call the appropriate tool(s) to get data — always use tools for questions about labs, scores, students, groups, statistics, or syncing
2. For multi-step queries (e.g. "which lab has the lowest pass rate"), call tools iteratively: first get_items to discover labs, then get_pass_rates for each lab with data, then compare
3. For greetings or general questions, respond directly without tools
4. For nonsensical input, respond helpfully listing what you can do

IMPORTANT: When you have tool results, you MUST use that data in your final answer. Include specific numbers, lab names, percentages, and counts from the tool results. Do NOT give generic responses like "I don't have the information" when tool results are available.

Keep responses concise but data-rich. Always include actual numbers from the tool results."""

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "sync the data"},
]

for round_num in range(5):
    print(f"\n=== Round {round_num + 1} ===", file=sys.stderr)
    print(f"Messages count: {len(messages)}", file=sys.stderr)
    print(f"Last message role: {messages[-1]['role']}", file=sys.stderr)

    payload = {"model": LLM_API_MODEL, "messages": messages, "tools": TOOLS}
    try:
        resp = client.post("/chat/completions", json=payload)
        print(f"HTTP status: {resp.status_code}", file=sys.stderr)
        if resp.status_code >= 400:
            print(f"Error body: {resp.text[:1000]}", file=sys.stderr)
            break
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        break

    data = resp.json()
    msg = data["choices"][0]["message"]
    finish = data["choices"][0].get("finish_reason")
    content = msg.get("content") or ""
    tool_calls = msg.get("tool_calls", [])

    print(f"finish_reason: {finish}", file=sys.stderr)
    print(f"content: {content[:300]}", file=sys.stderr)
    print(f"tool_calls count: {len(tool_calls)}", file=sys.stderr)

    if not tool_calls:
        print(f"\nFINAL ANSWER: {content}", file=sys.stderr)
        print(content)
        break

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
        print(f"  <- {truncated[:300]}", file=sys.stderr)

        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": truncated,
        })
