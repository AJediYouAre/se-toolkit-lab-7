"""Command handlers — each takes input text and returns response text.

These are pure functions with no Telegram dependency.
They can be called from --test mode, unit tests, or the Telegram bot.
"""

from bot.services.lms_client import LmsError, get_items, get_pass_rates


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
    """Check backend health by fetching items."""
    try:
        items = get_items()
        return f"Backend is healthy. {len(items)} items available."
    except LmsError as exc:
        return str(exc)


def handle_labs() -> str:
    """List available labs from the backend."""
    try:
        items = get_items()
        labs = [i for i in items if i.get("type") == "lab"]
        if not labs:
            return "No labs found."
        lines = ["Available labs:"]
        for lab in labs:
            lines.append(f"- {lab['title']}")
        return "\n".join(lines)
    except LmsError as exc:
        return str(exc)


def handle_scores(args: str = "") -> str:
    """Show per-task pass rates for a lab."""
    lab = args.strip()
    if not lab:
        return "Usage: /scores <lab-id> — e.g., /scores lab-04"

    try:
        rates = get_pass_rates(lab)
        if not rates:
            return f"No scores found for '{lab}'. Check the lab ID with /labs."

        lines = [f"Pass rates for {lab}:"]
        for entry in rates:
            task = entry["task"]
            avg = entry["avg_score"]
            attempts = entry["attempts"]
            lines.append(f"- {task}: {avg:.1f}% ({attempts} attempts)")

        return "\n".join(lines)
    except LmsError as exc:
        return str(exc)
