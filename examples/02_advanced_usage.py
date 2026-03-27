#!/usr/bin/env python3
"""
02_advanced_usage.py — Advanced features: multi-run sessions, history, export.

Demonstrates:
  - Persistent memory across two consecutive runs
  - Reading session history with format_history / format_history_compact
  - Exporting output to HTML and plain text

Run from any directory:
    python examples/02_advanced_usage.py
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
import tempfile

from markdown_agent_3_fil import execute, parse_memory, format_history, format_history_compact
from markdown_agent_3_fil.backends import get_backend
from markdown_agent_3_fil.history import export_html, export_plain

PLAN_1 = """\
# Plan

## Goal
Research Python packaging best practices

## Tasks
- [ ] List the preferred project layout
- [ ] Explain pyproject.toml vs setup.py
"""

PLAN_2 = """\
# Plan

## Goal
Write a checklist for publishing a Python package to PyPI

## Tasks
- [ ] List the required metadata fields
- [ ] Describe the build and upload steps
"""

with tempfile.TemporaryDirectory() as tmp:
    plan   = Path(tmp) / "plan.md"
    memory = Path(tmp) / "memory.md"
    output = Path(tmp) / "output.md"

    backend = get_backend()

    # ── Run 1 ────────────────────────────────────────────────────────────────
    print("=== Run 1 ===")
    plan.write_text(PLAN_1, encoding="utf-8")
    execute(plan, memory, output, backend=backend, verbose=True)

    # ── Run 2 (agent reads Run 1 session from memory) ────────────────────────
    print("\n=== Run 2 ===")
    plan.write_text(PLAN_2, encoding="utf-8")
    execute(plan, memory, output, backend=backend, verbose=True)

    # ── Session history ──────────────────────────────────────────────────────
    mem = parse_memory(memory.read_text(encoding="utf-8"))
    print(f"\n=== Sessions recorded: {len(mem.sessions)} ===")
    print(format_history_compact(mem))
    print()
    print(format_history(mem))

    # ── Export ───────────────────────────────────────────────────────────────
    output_text = output.read_text(encoding="utf-8")

    html_path  = Path(tmp) / "output.html"
    plain_path = Path(tmp) / "output.txt"

    html_path.write_text(export_html(output_text, title="Run 2 Output"), encoding="utf-8")
    plain_path.write_text(export_plain(output_text), encoding="utf-8")

    print(f"\nExported HTML  → {html_path} ({html_path.stat().st_size} bytes)")
    print(f"Exported plain → {plain_path} ({plain_path.stat().st_size} bytes)")
