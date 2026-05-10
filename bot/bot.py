"""Bot entry point — supports --test mode and Telegram polling.

Usage:
    uv run bot.py --test "/start"
    uv run bot.py --test "/scores lab-04"
    uv run bot.py --test "what labs are available"
    uv run bot.py
"""

import argparse
import sys
from pathlib import Path
from typing import Callable

# Ensure the project root is in sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from bot.config import BOT_TOKEN
from bot.handlers import handle_start, handle_help, handle_health, handle_labs, handle_scores
from bot.handlers.intent import route as route_intent


COMMANDS: dict[str, Callable[..., str]] = {
    "/start": handle_start,
    "/help": handle_help,
    "/health": handle_health,
    "/labs": handle_labs,
    "/scores": handle_scores,
}


def dispatch(text: str) -> str:
    """Route a message: slash commands go to handlers, plain text goes to LLM."""
    stripped = text.strip()

    # Slash commands → direct handlers
    if stripped.startswith("/"):
        parts = stripped.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = COMMANDS.get(command)
        if handler is None:
            return f"Unknown command: {command}. Type /help for available commands."

        if command == "/scores":
            return handler(args)
        return handler()

    # Plain text → LLM intent router
    return route_intent(stripped)


def run_test_mode(text: str) -> None:
    """Run in test mode — print response to stdout and exit."""
    response = dispatch(text)
    print(response)
    sys.exit(0)


def _main_keyboard() -> "InlineKeyboardMarkup":
    """Build the inline keyboard shown after /start."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = [
        [
            InlineKeyboardButton("📋 List Labs", callback_data="/labs"),
            InlineKeyboardButton("💚 Health", callback_data="/health"),
        ],
        [
            InlineKeyboardButton("📊 Scores", callback_data="/scores"),
            InlineKeyboardButton("❓ Help", callback_data="/help"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def run_telegram_mode() -> None:
    """Run in Telegram mode — start polling for updates."""
    from telegram import Update
    from telegram.ext import (
        Application, CallbackQueryHandler, CommandHandler,
        ContextTypes, MessageHandler, filters,
    )

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set in .env.bot.secret", file=sys.stderr)
        sys.exit(1)

    application = Application.builder().token(BOT_TOKEN).build()

    async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text if update.message else ""
        response = dispatch(text)
        if update.message:
            if text.strip().startswith("/start"):
                await update.message.reply_text(response, reply_markup=_main_keyboard())
            else:
                await update.message.reply_text(response)

    async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()
        response = dispatch(query.data)
        await query.edit_message_text(response)

    async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text if update.message else ""
        response = dispatch(text)
        if update.message:
            await update.message.reply_text(response)

    for cmd in COMMANDS:
        application.add_handler(CommandHandler(cmd.lstrip("/"), on_command))

    application.add_handler(CallbackQueryHandler(on_callback))
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
