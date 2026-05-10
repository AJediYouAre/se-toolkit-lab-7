"""Debug: full 2-round loop for 'sync the data'."""
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

# Round 1
print("=== Round 1 ===", file=sys.stderr)
payload = {"model": LLM_API_MODEL, "messages": messages, "tools": TOOLS}
resp = client.post("/chat/completions", json=payload)
print(f"HTTP: {resp.status_code}", file=sys.stderr)
data = resp.json()

# Print full response for debugging
print(f"Full response: {json.dumps(data, indent=2)[:2000]}", file=sys.stderr)

msg = data["choices"][0]["message"]
finish = data["choices"][0].get("finish_reason")
content = msg.get("content") or ""
tool_calls = msg.get("tool_calls", [])

print(f"finish_reason: {finish}", file=sys.stderr)
print(f"content: {content[:300]}", file=sys.stderr)
print(f"tool_calls: {len(tool_calls)}", file=sys.stderr)

if not tool_calls:
    print("No tool calls!", file=sys.stderr)
    sys.exit(0)

# Execute tool calls
messages.append(msg)
for tc in tool_calls:
    func = tc["function"]
    name = func["name"]
    raw_args = func.get("arguments", "{}")
    if isinstance(raw_args, str):
        args = json.loads(raw_args)
    else:
        args = raw_args

    print(f"\nExecuting: {name}({args})", file=sys.stderr)
    result = call_tool(name, args)
    print(f"Result: {result[:500]}", file=sys.stderr)

    messages.append({
        "role": "tool",
        "tool_call_id": tc["id"],
        "content": result[:2000],
    })

# Round 2 — NO tools parameter
print("\n=== Round 2 (no tools) ===", file=sys.stderr)
print(f"Messages count: {len(messages)}", file=sys.stderr)
for i, m in enumerate(messages):
    print(f"  [{i}] role={m['role']}, content={str(m.get('content', ''))[:100]}", file=sys.stderr)

payload2 = {"model": LLM_API_MODEL, "messages": messages}
resp2 = client.post("/chat/completions", json=payload2)
print(f"HTTP: {resp2.status_code}", file=sys.stderr)
data2 = resp2.json()

print(f"Full response 2: {json.dumps(data2, indent=2)[:2000]}", file=sys.stderr)

msg2 = data2["choices"][0]["message"]
finish2 = data2["choices"][0].get("finish_reason")
content2 = msg2.get("content") or ""

print(f"finish_reason: {finish2}", file=sys.stderr)
print(f"content: {content2[:500]}", file=sys.stderr)
