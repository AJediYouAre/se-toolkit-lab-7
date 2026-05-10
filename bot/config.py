"""Bot configuration — loads environment variables from .env.bot.secret."""

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load .env.bot.secret from the project root (parent of bot/)."""
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env.bot.secret"
    if env_path.exists():
        load_dotenv(env_path)


_load_env()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
LMS_API_BASE_URL: str = os.getenv("LMS_API_BASE_URL", "http://localhost:42002")
LMS_API_KEY: str = os.getenv("LMS_API_KEY", "")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "http://localhost:42005/v1")
LLM_API_MODEL: str = os.getenv("LLM_API_MODEL", "coder-model")
