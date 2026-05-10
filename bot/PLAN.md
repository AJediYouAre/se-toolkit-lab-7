# Bot Development Plan

## Architecture Overview

The Telegram bot follows a **layered architecture** with clear separation of concerns:

- **Entry point** (`bot.py`) — parses CLI args, loads config, dispatches to handlers or starts Telegram polling
- **Handlers** (`handlers/`) — pure functions `(text) -> text`, no Telegram dependency, testable via `--test` mode
- **Services** (`services/`) — API clients for LMS backend and LLM, isolated behind clean interfaces
- **Config** (`config.py`) — loads env vars from `.env.bot.secret`

This separation means the same handler logic runs from `--test` CLI, unit tests, and live Telegram — no duplication.

## Task 1: Plan and Scaffold

Create the project skeleton: `bot/` directory, `pyproject.toml`, `config.py`, handler modules with placeholder responses, and `bot.py` with `--test` mode. Handlers return static strings. No external API calls yet.

## Task 2: Backend Integration

Replace placeholder handlers with real LMS API calls. Add `services/lms_client.py` with Bearer auth. Implement `/health` (backend status), `/labs` (list labs), `/scores <lab>` (fetch scores). Error handling for network failures and missing data. Telegram bot starts polling and responds to commands.

## Task 3: Intent-Based Natural Language Routing

Add `services/llm_client.py` that calls the LLM API with tool definitions. The LLM reads user messages and decides which tool (handler) to invoke. Add `handlers/intent_router.py` that bridges LLM tool calls back to handlers. System prompt and tool descriptions are critical — the LLM routes based on them, not regex.

## Task 4: Containerize and Document

Add `Dockerfile` for the bot, update `docker-compose.yml` to include the bot service. Document deployment steps, environment variables, and troubleshooting. The bot runs alongside the existing backend stack on the VM.
