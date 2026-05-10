"""Bot entry point — supports --test mode and Telegram polling.

Usage:
    uv run python -m bot.bot --test "/start"
    uv run python -m bot.bot --test "/scores lab-04"
    uv run python -m bot.bot
"""

import argparse
import sys
from typing import Callable

from .config import BOT_TOKEN
from .handlers import handle_start, handle_help, handle_health, handle_labs, handle_scores


COMMANDS: dict[str, Callable[..., str]] = {
    "/start": handle_start,
    "/help": handle_help,
    "/health": handle_health,
    "/labs": handle_labs,
    "/scores": handle_scores,
}


def dispatch(text: str) -> str:
    """Route a message to the appropriate handler."""
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return "Empty message. Type /help for available commands."

    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(command)
    if handler is None:
        return f"Unknown command: {command}. Type /help for available commands."

    if command == "/scores":
        return handler(args)

    return handler()


def run_test_mode(text: str) -> None:
    """Run in test mode — print response to stdout and exit."""
    response = dispatch(text)
    print(response)
    sys.exit(0)


def run_telegram_mode() -> None:
    """Run in Telegram mode — start polling for updates."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set in .env.bot.secret", file=sys.stderr)
        sys.exit(1)

    application = Application.builder().token(BOT_TOKEN).build()

    async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text if update.message else ""
        response = dispatch(text)
        if update.message:
            await update.message.reply_text(response)

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text if update.message else ""
        response = dispatch(text)
        if update.message:
            await update.message.reply_text(response)

    for cmd in COMMANDS:
        application.add_handler(CommandHandler(cmd.lstrip("/"), on_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument("--test", nargs="?", const="", metavar="MESSAGE",
                        help="Run in test mode: print response to stdout")
    args = parser.parse_args()

    if args.test is not None:
        run_test_mode(args.test)
    else:
        run_telegram_mode()


if __name__ == "__main__":
    main()
