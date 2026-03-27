#!/usr/bin/env python3
"""
Demo script for Markdown Agent.

Auto-detects available backend (uses mock if no API keys set).
Always writes real output files to outputs/ directory.

Usage:
    python demo.py
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

DEMO_PLAN = ROOT / "outputs" / "demo_plan.md"
DEMO_MEMORY = ROOT / "outputs" / "demo_memory.md"
DEMO_OUTPUT = ROOT / "outputs" / "demo_output.md"
DEMO_RESULTS = ROOT / "outputs" / "demo_results.json"


# ── Demo plan content ─────────────────────────────────────────────────────────

_PLAN_CONTENT = """\
# Plan

## Goal
Create a Python Developer Best-Practices Guide for 2024

## Tasks
- [ ] Summarise PEP 8 style guidelines
- [ ] List top testing best practices with pytest
- [ ] Recommend essential developer tooling (uv, ruff, pyright)
- [ ] Provide a quick-start project checklist

## Context
Target audience: intermediate Python developers.
Focus on modern tooling available in 2024+.
Keep examples concise and actionable.
"""

_MEMORY_CONTENT = """\
# Memory

## Context
Agent is operating in Python best-practices advisory mode.
Prefer modern tooling over legacy alternatives.

## State
- last_run: never
- total_sessions: 0
- status: initialised

## Sessions

"""


# ── Rich terminal output helpers ──────────────────────────────────────────────

def _sep(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _header(text: str) -> None:
    _sep("═")
    print(f"  {text}")
    _sep("═")


def _section(text: str) -> None:
    print(f"\n▶ {text}")
    _sep()


# ── Main demo ─────────────────────────────────────────────────────────────────

def run_demo() -> None:
    _header("Markdown Agent — Demo")
    print(f"  Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Outputs   : {OUTPUTS_DIR}")

    # Write demo input files
    DEMO_PLAN.write_text(_PLAN_CONTENT, encoding="utf-8")
    DEMO_MEMORY.write_text(_MEMORY_CONTENT, encoding="utf-8")

    # ── Import after dotenv loaded ────────────────────────────────────────────
    from markdown_agent_3_fil import execute, __version__
    from markdown_agent_3_fil.backends import get_backend

    backend = get_backend()
    print(f"  Backend   : {backend.name}")

    _section("Running agent…")
    output_text = execute(
        plan_path=DEMO_PLAN,
        memory_path=DEMO_MEMORY,
        output_path=DEMO_OUTPUT,
        backend=backend,
        verbose=True,
    )

    _section("Output preview (first 30 lines)")
    for i, line in enumerate(output_text.splitlines()[:30]):
        print(line)
    if len(output_text.splitlines()) > 30:
        print("… (truncated — see outputs/demo_output.md for full output)")

    # ── Save structured JSON results ─────────────────────────────────────────
    _section("Saving structured results → outputs/demo_results.json")

    from markdown_agent_3_fil.parser import parse_plan, parse_memory

    plan = parse_plan(_PLAN_CONTENT)
    memory_after = parse_memory(DEMO_MEMORY.read_text(encoding="utf-8"))

    results = {
        "meta": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "backend": backend.name,
            "version": __version__,
        },
        "plan": {
            "goal": plan.goal,
            "tasks_total": len(plan.tasks),
            "tasks_completed": len(plan.tasks),  # agent completes all tasks
            "tasks": [
                {"text": t.text, "completed": True} for t in plan.tasks
            ],
        },
        "memory": {
            "sessions_after_run": len(memory_after.sessions),
            "state": memory_after.state,
        },
        "output": {
            "file": str(DEMO_OUTPUT.relative_to(ROOT)),
            "char_count": len(output_text),
            "line_count": len(output_text.splitlines()),
        },
        "files": {
            "plan": str(DEMO_PLAN.relative_to(ROOT)),
            "memory": str(DEMO_MEMORY.relative_to(ROOT)),
            "output": str(DEMO_OUTPUT.relative_to(ROOT)),
        },
    }

    DEMO_RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"  Saved: {DEMO_RESULTS}")

    _sep("═")
    print("\n  All output files saved:")
    for f in [DEMO_PLAN, DEMO_MEMORY, DEMO_OUTPUT, DEMO_RESULTS]:
        size = f.stat().st_size
        print(f"    {f.relative_to(ROOT):<40} {size:>6} bytes")

    print("\n  Next steps:")
    print("    1. Edit plan.md with your own goal")
    print("    2. Run: python run_agent.py")
    print("    3. Check output.md for results\n")


if __name__ == "__main__":
    run_demo()
