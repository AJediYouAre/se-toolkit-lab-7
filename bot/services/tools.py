"""Tool definitions for LLM function calling.

Each tool wraps a backend endpoint. The LLM reads these descriptions
to decide which tool to call for a given user query.
"""

from bot.services.lms_client import (
    get_items,
    get_pass_rates,
)

# ---------------------------------------------------------------------------
# Tool schemas — sent to the LLM so it knows what functions are available
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": (
                "List all labs and tasks available in the LMS. "
                "Use this when the user asks what labs exist, what tasks are available, "
                "or needs to know lab IDs for other queries."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": (
                "Get the list of enrolled students and their groups. "
                "Use this for questions about how many students are enrolled, "
                "which groups exist, or student counts."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": (
                "Get score distribution (4 buckets: 0-25, 26-50, 51-75, 76-100) for a lab. "
                "Use this when the user asks about score distribution or grade breakdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": (
                "Get per-task average scores and attempt counts for a lab. "
                "Use this when the user asks about pass rates, task scores, "
                "or how students performed on specific tasks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01', 'lab-04'",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": (
                "Get submission counts per day for a lab. "
                "Use this when the user asks about submission patterns over time, "
                "deadline rushes, or activity timelines."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": (
                "Get per-group performance data for a lab. "
                "Use this when the user asks which group is best, "
                "wants to compare groups, or needs group-level statistics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": (
                "Get the top N learners by score for a lab. "
                "Use this when the user asks about top students, "
                "leaderboard, or best performers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top learners to return, default 5",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": (
                "Get the overall completion rate percentage for a lab. "
                "Use this when the user asks what percentage of students completed the lab."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier, e.g. 'lab-01'",
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": (
                "Trigger an ETL sync to refresh data from the autochecker. "
                "Use this when the user asks to refresh data, update scores, "
                "or if data seems stale."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool name → callable mapping
# ---------------------------------------------------------------------------

import json

import httpx
from bot.config import LMS_API_BASE_URL, LMS_API_KEY


def _api_get(path: str, params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to the backend."""
    resp = httpx.get(
        f"{LMS_API_BASE_URL}{path}",
        params=params or {},
        headers={"Authorization": f"Bearer {LMS_API_KEY}"},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()


def _api_post(path: str, json_body: dict | None = None) -> dict | list:
    """Make an authenticated POST request to the backend."""
    resp = httpx.post(
        f"{LMS_API_BASE_URL}{path}",
        json=json_body or {},
        headers={
            "Authorization": f"Bearer {LMS_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def call_tool(name: str, arguments: dict) -> str:
    """Execute a tool call by name with the given arguments.

    Returns a JSON string with the result (or error).
    """
    try:
        match name:
            case "get_items":
                result = _api_get("/items/")
            case "get_learners":
                result = _api_get("/learners/")
            case "get_scores":
                result = _api_get("/analytics/scores", params={"lab": arguments["lab"]})
            case "get_pass_rates":
                result = _api_get("/analytics/pass-rates", params={"lab": arguments["lab"]})
            case "get_timeline":
                result = _api_get("/analytics/timeline", params={"lab": arguments["lab"]})
            case "get_groups":
                result = _api_get("/analytics/groups", params={"lab": arguments["lab"]})
            case "get_top_learners":
                result = _api_get(
                    "/analytics/top-learners",
                    params={"lab": arguments["lab"], "limit": arguments.get("limit", 5)},
                )
            case "get_completion_rate":
                result = _api_get("/analytics/completion-rate", params={"lab": arguments["lab"]})
            case "trigger_sync":
                result = _api_post("/pipeline/sync")
            case _:
                return json.dumps({"error": f"Unknown tool: {name}"})
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})
