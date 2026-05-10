"""Debug script — test LLM with different queries to understand tool calling behavior."""
import json
import sys

import httpx

from bot.config import LLM_API_KEY, LLM_API_BASE_URL, LLM_API_MODEL
from bot.services.tools import TOOLS

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

queries = [
    "how many students are enrolled",
    "which group is doing best in lab 3",
    "which lab has the lowest pass rate",
    "sync the data",
]

for query in queries:
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"QUERY: {query}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    payload = {"model": LLM_API_MODEL, "messages": messages, "tools": TOOLS}
    resp = client.post("/chat/completions", json=payload)
    print(f"HTTP status: {resp.status_code}", file=sys.stderr)

    data = resp.json()
    msg = data["choices"][0]["message"]
    finish = data["choices"][0].get("finish_reason")
    content = msg.get("content") or ""
    tool_calls = msg.get("tool_calls", [])

    print(f"finish_reason: {finish}", file=sys.stderr)
    print(f"content: {content[:300]}", file=sys.stderr)
    print(f"tool_calls count: {len(tool_calls)}", file=sys.stderr)
    for tc in tool_calls:
        func = tc["function"]
        print(f"  -> {func['name']}({func.get('arguments', '{}')})", file=sys.stderr)

    # Also print the full response for debugging
    print(f"Full response keys: {list(data.keys())}", file=sys.stderr)
    if "error" in data:
        print(f"Error: {data['error']}", file=sys.stderr)
