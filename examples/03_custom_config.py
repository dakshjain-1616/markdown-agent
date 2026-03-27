#!/usr/bin/env python3
"""
03_custom_config.py — Customising behaviour via env vars and config.

Demonstrates:
  - Forcing a specific backend via environment variable
  - Adjusting max tokens and retry settings
  - Selecting files from non-default paths (AGENT_PLAN_FILE etc.)
  - Using the dry-run backend to preview prompts without calling an LLM

Run from any directory:
    python examples/03_custom_config.py

    # Force Anthropic backend (requires ANTHROPIC_API_KEY):
    ANTHROPIC_API_KEY=sk-... python examples/03_custom_config.py

    # Limit token budget:
    AGENT_MAX_TOKENS=512 python examples/03_custom_config.py
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
import tempfile

from markdown_agent_3_fil import execute
from markdown_agent_3_fil.backends import get_backend, DryRunBackend, MockBackend

PLAN = """\
# Plan

## Goal
Analyse the trade-offs between SQL and NoSQL databases

## Tasks
- [ ] List 3 strengths of SQL databases
- [ ] List 3 strengths of NoSQL databases
- [ ] Recommend when to choose each

## Context
Audience: backend engineers choosing a data store for a new microservice.
"""

with tempfile.TemporaryDirectory() as tmp:
    plan   = Path(tmp) / "plan.md"
    memory = Path(tmp) / "memory.md"
    output = Path(tmp) / "output.md"
    plan.write_text(PLAN, encoding="utf-8")

    # ── Config 1: dry-run — shows prompt without calling LLM ─────────────────
    print("=== Dry-run mode (no LLM called, memory not updated) ===\n")
    dry_backend = DryRunBackend()
    result = execute(
        plan, memory, output,
        backend=dry_backend,
        verbose=True,
        dry_run=True,
    )
    print("\n--- Dry-run output ---")
    print(result[:600])

    # Reset memory for next run
    if memory.exists():
        memory.unlink()

    # ── Config 2: mock backend, low token limit via env var ───────────────────
    print("\n=== Mock backend with AGENT_MAX_TOKENS=256 ===\n")
    os.environ["AGENT_MAX_TOKENS"] = "256"

    # AGENT_BACKEND env var selects the backend when using get_backend()
    backend = get_backend(override="mock")
    result = execute(plan, memory, output, backend=backend, verbose=True)
    print(f"\nOutput length: {len(result)} chars")

    del os.environ["AGENT_MAX_TOKENS"]

    # ── Config 3: explicit backend override ───────────────────────────────────
    print("\n=== Explicit backend selection ===")
    # Environment variables that control backend choice:
    #   ANTHROPIC_API_KEY  → AnthropicBackend
    #   OPENAI_API_KEY     → OpenAIBackend
    #   LLAMA_MODEL_PATH   → LlamaBackend
    #   (none set)         → MockBackend  ← always available, zero config
    auto_backend = get_backend()   # auto-detects from env
    print(f"Auto-detected backend: {auto_backend.name}")
    print("\nTo override, pass override= to get_backend():")
    print("  get_backend(override='mock')       # always mock")
    print("  get_backend(override='anthropic')  # force Anthropic")
    print("  get_backend(override='dry-run')    # dry-run")
    print("\nOr set AGENT_BACKEND in your .env file.")
