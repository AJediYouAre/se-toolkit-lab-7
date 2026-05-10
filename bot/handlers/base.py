"""Base handler utilities."""

from typing import Callable

# Type alias for command handlers
HandlerFunc = Callable[..., str]
