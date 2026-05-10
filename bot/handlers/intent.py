"""Intent router — uses LLM with tool calling to handle natural language queries.

Flow:
    user message → LLM (with tool definitions) → tool calls → execute → feed back → LLM summary
"""

import json
import sys

from bot.services.llm_client import chat, debug, extract_message, has_tool_calls, LlmError
from bot.services.tools import TOOLS, call_tool

SYSTEM_PROMPT = """You are an LMS (Learning Management System) bot assistant. You help students and instructors query lab data.

You have access to tools that fetch real data from the backend. When a user asks a question:
1. If you need data, call the appropriate tool(s)
2. If the user's request is ambiguous, call the tool that best matches
3. If it's a greeting or general question, respond directly without tools
4. If the query is nonsensical, respond helpfully with what you can do

Always use tools when the user asks about labs, scores, students, groups, or statistics.
For multi-step queries (e.g. "which lab has the lowest pass rate"), call tools iteratively:
  first get_items to discover labs, then get_pass_rates for each lab, then compare.

When you have enough data to answer, provide a concise, helpful response with specific numbers."""


def route(text: str) -> str:
    """Route a natural language message through the LLM intent router.

    Returns the final text response.
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    # Tool calling loop — allow up to 5 rounds of tool calls
    for _ in range(5):
        try:
            response = chat(messages, tools=TOOLS)
        except LlmError as exc:
            return f"Sorry, the AI service is currently unavailable: {exc}"

        message = extract_message(response)

        if not has_tool_calls(message):
            # LLM responded with text — we're done
            content = message.get("content", "")
            if not content:
                return "I'm not sure how to help with that. Try asking about labs, scores, or students."
            return content

        # LLM wants to call tools — execute them
        messages.append(message)

        for tool_call in message["tool_calls"]:
            func = tool_call["function"]
            name = func["name"]
            raw_args = func.get("arguments", "{}")

            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = raw_args

            debug(f"[tool] LLM called: {name}({arguments})")

            result = call_tool(name, arguments)
            debug(f"[tool] Result: {result[:200]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

        debug(f"[summary] Feeding {len(message['tool_calls'])} tool result(s) back to LLM")

    # If we exhausted the loop, ask LLM for a final summary
    try:
        response = chat(messages, tools=None)
        message = extract_message(response)
        return message.get("content", "I processed the data but couldn't formulate a response.")
    except LlmError as exc:
        return f"Sorry, the AI service is currently unavailable: {exc}"
