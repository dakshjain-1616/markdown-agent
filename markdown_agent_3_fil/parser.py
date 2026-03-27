"""Markdown parser for plan.md and memory.md."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Task:
    text: str
    completed: bool = False
    sub_tasks: List["Task"] = field(default_factory=list)

    def to_md(self) -> str:
        """Render the task as a Markdown checkbox line."""
        mark = "x" if self.completed else " "
        return f"- [{mark}] {self.text}"


@dataclass
class Plan:
    goal: str
    tasks: List[Task]
    context: str
    raw: str

    def pending_tasks(self) -> List[Task]:
        """Return tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.completed]

    def completed_tasks(self) -> List[Task]:
        """Return tasks that are already marked complete."""
        return [t for t in self.tasks if t.completed]


@dataclass
class MemorySession:
    timestamp: str
    goal: str
    tasks_completed: List[str]
    summary: str


@dataclass
class Memory:
    sessions: List[MemorySession]
    context: str
    state: Dict[str, Any]
    raw: str

    def last_session(self) -> Optional[MemorySession]:
        """Return the most recent session, or None if no sessions exist."""
        return self.sessions[-1] if self.sessions else None


# ── helpers ────────────────────────────────────────────────────────────────

def _extract_section(content: str, heading: str) -> str:
    """Return text under a heading until the next same-level heading."""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_tasks(text: str) -> List[Task]:
    """Extract checkbox task lines from a markdown text block."""
    tasks: List[Task] = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s*\[([ xX])\]\s*(.*)", line)
        if m:
            completed = m.group(1).lower() == "x"
            tasks.append(Task(text=m.group(2).strip(), completed=completed))
    return tasks


def _parse_state(text: str) -> Dict[str, Any]:
    """Parse a key-value state block (``- key: value`` lines) into a dict."""
    state: Dict[str, Any] = {}
    for line in text.splitlines():
        m = re.match(r"[-*]?\s*([^:]+):\s*(.*)", line.strip())
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            state[key] = m.group(2).strip()
    return state


# ── public API ──────────────────────────────────────────────────────────────

def parse_plan(content: str) -> Plan:
    """Parse plan.md content into a Plan object."""
    # Goal
    goal = _extract_section(content, "Goal")
    if not goal:
        # Try H1 as fallback
        m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
        goal = m.group(1).strip() if m else "No goal specified"

    # Tasks
    tasks_section = _extract_section(content, "Tasks")
    tasks = _parse_tasks(tasks_section or content)

    # Extra context (everything not in Goal/Tasks)
    context_parts = []
    for section in ("Context", "Background", "Notes", "Constraints"):
        sec = _extract_section(content, section)
        if sec:
            context_parts.append(f"### {section}\n{sec}")
    context = "\n\n".join(context_parts)

    return Plan(goal=goal, tasks=tasks, context=context, raw=content)


def parse_memory(content: str) -> Memory:
    """Parse memory.md content into a Memory object."""
    sessions: List[MemorySession] = []

    # Sessions block
    sessions_text = _extract_section(content, "Sessions")
    if sessions_text:
        # Each session starts with "### Session" or "#### "
        blocks = re.split(r"\n###+ ", sessions_text)
        for block in blocks:
            if not block.strip():
                continue
            ts_m = re.search(r"Timestamp[:\s]+(.+)", block)
            goal_m = re.search(r"Goal[:\s]+(.+)", block)
            summary_m = re.search(r"Summary[:\s]+(.+)", block, re.DOTALL)
            tasks_completed = re.findall(r"-\s+(.+)", block)
            sessions.append(
                MemorySession(
                    timestamp=ts_m.group(1).strip() if ts_m else "unknown",
                    goal=goal_m.group(1).strip() if goal_m else "unknown",
                    tasks_completed=tasks_completed,
                    summary=summary_m.group(1).strip()[:300] if summary_m else "",
                )
            )

    context = _extract_section(content, "Context")
    state_text = _extract_section(content, "State")
    state = _parse_state(state_text) if state_text else {}

    return Memory(sessions=sessions, context=context, state=state, raw=content)


def mark_tasks_complete(plan_content: str) -> str:
    """Return plan_content with all tasks marked complete."""
    return re.sub(r"- \[ \]", "- [x]", plan_content)
