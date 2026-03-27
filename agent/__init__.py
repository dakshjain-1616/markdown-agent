"""Markdown Agent — runs entirely through plan.md, memory.md, and output.md."""

from .executor import execute
from .backends import get_backend
from .parser import parse_plan, parse_memory
from .templates import get_template, list_templates
from .history import format_history, format_history_compact

__version__ = "1.1.0"
__all__ = [
    "execute",
    "get_backend",
    "parse_plan",
    "parse_memory",
    "get_template",
    "list_templates",
    "format_history",
    "format_history_compact",
]
