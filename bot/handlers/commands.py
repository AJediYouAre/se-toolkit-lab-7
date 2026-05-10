"""Command handlers — each takes input text and returns response text.

These are pure functions with no Telegram dependency.
They can be called from --test mode, unit tests, or the Telegram bot.
"""

from bot.config import LMS_API_BASE_URL


def handle_start() -> str:
    """Welcome message."""
    return (
        "Welcome to the LMS Bot! 🎓\n"
        "I can help you check lab scores, pass rates, and more.\n"
        "Type /help to see available commands."
    )


def handle_help() -> str:
    """List available commands."""
    return (
        "Available commands:\n"
        "/start — Welcome message\n"
        "/help — Show this help\n"
        "/health — Check backend status\n"
        "/labs — List available labs\n"
        "/scores <lab> — Show pass rates for a lab"
    )


def handle_health() -> str:
    """Check backend health. Placeholder for Task 2."""
    return f"Backend health check — connecting to {LMS_API_BASE_URL} (not implemented yet)"


def handle_labs() -> str:
    """List available labs. Placeholder for Task 2."""
    return "Available labs: (not implemented yet — will fetch from backend in Task 2)"


def handle_scores(args: str = "") -> str:
    """Show scores for a lab. Placeholder for Task 2."""
    if not args.strip():
        return "Usage: /scores <lab-id> — e.g., /scores lab-04"
    return f"Scores for '{args.strip()}' (not implemented yet — will fetch from backend in Task 2)"
