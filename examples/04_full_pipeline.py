#!/usr/bin/env python3
"""
04_full_pipeline.py — End-to-end workflow: template → execute → history → export.

Demonstrates the complete Markdown Agent pipeline:
  1. Bootstrap plan.md from a built-in template
  2. Run the agent (3 consecutive sessions on evolving plans)
  3. Parse and display the session history
  4. Export the final output to HTML, plain text, and a JSON bundle

Run from any directory:
    python examples/04_full_pipeline.py
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from datetime import datetime
from pathlib import Path
import tempfile

from markdown_agent_3_fil import (
    execute,
    get_backend,
    parse_plan,
    parse_memory,
    get_template,
    list_templates,
    format_history,
    format_history_compact,
)
from markdown_agent_3_fil.history import export_html, export_plain

# ── Step 1: Show available templates ─────────────────────────────────────────

print("=== Available templates ===")
for name in list_templates():
    print(f"  • {name}")

# ── Step 2: Bootstrap a plan from the 'research' template ────────────────────

print("\n=== Bootstrapping plan from 'research' template ===")
template_content = get_template("research")
# Fill in the placeholder
filled_plan = template_content.replace(
    "Research [TOPIC] and produce a structured summary",
    "Research best practices for Python project documentation",
).replace(
    "Audience: [describe audience]",
    "Audience: open-source Python developers",
)
print(filled_plan[:300] + "…")

with tempfile.TemporaryDirectory() as tmp:
    plan   = Path(tmp) / "plan.md"
    memory = Path(tmp) / "memory.md"
    output = Path(tmp) / "output.md"

    backend = get_backend()
    print(f"\nUsing backend: {backend.name}\n")

    # ── Step 3: Three consecutive agent runs ─────────────────────────────────

    plans = [
        filled_plan,
        """\
# Plan

## Goal
Write a README template for Python open-source projects

## Tasks
- [ ] List the essential README sections
- [ ] Provide a minimal skeleton with placeholder text
- [ ] Note what to avoid in a README
""",
        """\
# Plan

## Goal
Summarise the documentation toolchain for Python projects

## Tasks
- [ ] Compare Sphinx, MkDocs, and pdoc
- [ ] Recommend a stack for a small open-source library
- [ ] List the steps to publish docs to GitHub Pages
""",
    ]

    for i, plan_text in enumerate(plans, 1):
        print(f"--- Run {i}/3 ---")
        plan.write_text(plan_text, encoding="utf-8")
        execute(plan, memory, output, backend=backend, verbose=True)
        print()

    # ── Step 4: Session history ───────────────────────────────────────────────

    mem = parse_memory(memory.read_text(encoding="utf-8"))
    print(f"=== History: {len(mem.sessions)} sessions ===\n")
    print(format_history_compact(mem))
    print()

    # ── Step 5: Export final output ───────────────────────────────────────────

    output_text = output.read_text(encoding="utf-8")

    html_path  = Path(tmp) / "output.html"
    plain_path = Path(tmp) / "output.txt"
    json_path  = Path(tmp) / "output.json"

    html_path.write_text(export_html(output_text, title="Full Pipeline Output"), encoding="utf-8")
    plain_path.write_text(export_plain(output_text), encoding="utf-8")

    final_plan = parse_plan(plans[-1])
    bundle = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "backend": backend.name,
        "sessions_total": len(mem.sessions),
        "final_plan": {
            "goal": final_plan.goal,
            "tasks": [t.text for t in final_plan.tasks],
        },
        "memory_state": mem.state,
        "output_chars": len(output_text),
    }
    json_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    print("=== Exports ===")
    for path in [html_path, plain_path, json_path]:
        print(f"  {path.suffix[1:].upper():<6} {path.stat().st_size:>6} bytes")

    print("\n=== JSON bundle ===")
    print(json.dumps(bundle, indent=2))
