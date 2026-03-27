#!/usr/bin/env python3
"""
01_quick_start.py — Minimal working example of Markdown Agent.

Run from any directory:
    python examples/01_quick_start.py
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
import tempfile

from markdown_agent_3_fil import execute
from markdown_agent_3_fil.backends import get_backend

# Write a plan to a temporary file
plan_content = """\
# Plan

## Goal
Summarise the key principles of clean code

## Tasks
- [ ] List the top 5 clean code principles
- [ ] Give a one-line example for each
"""

with tempfile.TemporaryDirectory() as tmp:
    plan   = Path(tmp) / "plan.md"
    memory = Path(tmp) / "memory.md"
    output = Path(tmp) / "output.md"

    plan.write_text(plan_content, encoding="utf-8")

    backend = get_backend()            # auto-detects: mock if no API keys set
    result  = execute(plan, memory, output, backend=backend, verbose=True)

    print("\n--- Output preview (first 20 lines) ---")
    for line in result.splitlines()[:20]:
        print(line)
