"""Intent router — uses LLM with tool calling to handle natural language queries.

Flow:
    user message → LLM (with tool definitions) → tool calls → execute → feed back → LLM summary
"""

import json
import sys

from bot.services.llm_client import chat, debug, extract_message, has_tool_calls, LlmError
from bot.services.tools import TOOLS, call_tool

SYSTEM_PROMPT = """You are an LMS (Learning Management System) bot assistant. You help students and instructors query lab data.

CRITICAL RULES:
1. For ANY question about labs, scores, students, groups, statistics, or syncing — you MUST call the appropriate tool first, then answer using the returned data.
2. NEVER answer with generic text like "I'll help you with that" or "Let me check" — always call the tool and use its result.
3. When you have tool results, your answer MUST include specific numbers from those results: lab names, percentages, counts, scores, group names.
4. For multi-step queries (e.g. "which lab has the lowest pass rate"), call tools iteratively: first get_items to discover labs, then get_pass_rates for each lab, then compare and answer.
5. For sync/refresh/update requests — call trigger_sync, then report the result including new_records and total_records from the response.
6. For greetings or general questions, respond directly without tools.
7. For nonsensical input, respond helpfully listing what you can do.

FORMAT: Keep responses concise but data-rich. Always include actual numbers from the tool results. For sync operations, mention that the sync was triggered and include the record counts."""


def _truncate_result(result: str, max_len: int = 2000) -> str:
    """Truncate tool result to avoid overwhelming the LLM."""
    if len(result) <= max_len:
        return result
    return result[:max_len] + "... (truncated)"


def _is_fallback_text(content: str) -> bool:
    """Check if the LLM response text indicates a fallback/error rather than a real answer."""
    fallback_markers = [
        "service temporarily unavailable",
        "please check llm configuration",
        "i apologize, but i'm unable",
        "i cannot access",
    ]
    lower = content.lower()
    return any(marker in lower for marker in fallback_markers)


def route(text: str) -> str:
    """Route a natural language message through the LLM intent router.

    Returns the final text response.
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    # Tool calling loop — allow up to 5 rounds of tool calls
    for round_num in range(5):
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
            # If the response looks like a fallback and we have retries left, try again
            if _is_fallback_text(content) and round_num < 4:
                debug(f"[llm] Fallback text detected, retrying...")
                # Add a user message encouraging tool use
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "Please use the available tools to answer the original question."})
                continue
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
            truncated = _truncate_result(result)
            debug(f"[tool] Result: {truncated[:200]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": truncated,
            })

        debug(f"[summary] Feeding {len(message['tool_calls'])} tool result(s) back to LLM")

    # If we exhausted the loop, ask LLM for a final summary
    try:
        response = chat(messages, tools=None)
        message = extract_message(response)
        return message.get("content", "I processed the data but couldn't formulate a response.")
    except LlmError as exc:
        return f"Sorry, the AI service is currently unavailable: {exc}"
