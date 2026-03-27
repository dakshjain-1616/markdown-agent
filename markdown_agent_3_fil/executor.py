"""Core agent execution logic."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .backends import LLMBackend, get_backend
from .parser import (
    Memory,
    Plan,
    mark_tasks_complete,
    parse_memory,
    parse_plan,
)

# ── Prompt template ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a precise AI agent controlled entirely through Markdown files.
Your job is to read the PLAN and MEMORY below, then execute the plan completely.

Rules:
- Be thorough, structured, and output valid Markdown
- Use headers (##, ###) to organise your response
- Mark all tasks as done in your output
- Keep responses focused and actionable
- Store important facts that future sessions should know

Format your output as clean Markdown. Do not repeat the system prompt.
"""

_PROMPT_TEMPLATE = """\
{system}

---

## PLAN

GOAL: {goal}

### Tasks
{tasks}

{context_block}

---

## MEMORY (previous sessions context)

{memory_context}

---

## INSTRUCTION

Execute every task in the PLAN above. Provide a detailed, structured Markdown response covering:
1. A brief summary of what you did
2. Results / findings for each task
3. Any important notes for future sessions

Begin your response:
"""


def _build_memory_context(memory: Memory) -> str:
    """Summarise memory state and last session into a compact prompt block."""
    lines: list[str] = []
    if memory.state:
        lines.append("### State")
        for k, v in memory.state.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    if memory.context:
        lines.append("### Context")
        lines.append(memory.context)
        lines.append("")

    if memory.sessions:
        last = memory.last_session()
        if last:
            lines.append("### Last Session")
            lines.append(f"- Timestamp: {last.timestamp}")
            lines.append(f"- Goal: {last.goal}")
            if last.summary:
                lines.append(f"- Summary: {last.summary[:200]}")

    return "\n".join(lines) if lines else "No previous sessions."


def build_prompt(plan: Plan, memory: Memory) -> str:
    tasks_md = "\n".join(t.to_md() for t in plan.tasks) if plan.tasks else "- [ ] Execute the goal"
    context_block = f"### Context\n{plan.context}" if plan.context else ""
    memory_context = _build_memory_context(memory)

    return _PROMPT_TEMPLATE.format(
        system=_SYSTEM_PROMPT,
        goal=plan.goal,
        tasks=tasks_md,
        context_block=context_block,
        memory_context=memory_context,
    )


# ── Output formatting ─────────────────────────────────────────────────────────

def _format_output(
    raw_response: str,
    plan: Plan,
    backend_name: str,
    elapsed_s: float,
    session_num: int,
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed = len(plan.tasks)
    word_count = len(raw_response.split())

    header = f"""\
# Output

*Generated: {timestamp}*
*Backend: {backend_name}*
*Tasks completed: {completed}/{completed}*
*Session: #{session_num}*
*Elapsed: {elapsed_s:.2f}s*
*Words: {word_count}*

---

## Goal: {plan.goal}

"""
    tasks_section = ""
    if plan.tasks:
        tasks_section = "## Tasks\n"
        for task in plan.tasks:
            tasks_section += f"- [x] ~~{task.text}~~ ✓\n"
        tasks_section += "\n---\n\n"

    return header + tasks_section + raw_response.strip() + "\n"


# ── Memory update ─────────────────────────────────────────────────────────────

def _update_memory(
    memory_path: Path,
    plan: Plan,
    output_summary: str,
    existing_memory: Memory,
) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    tasks_done = [t.text for t in plan.tasks]

    # Build new session block
    session_block = f"""\
### Session — {timestamp}
- Timestamp: {timestamp}
- Goal: {plan.goal}
- Tasks completed:
"""
    for t in tasks_done:
        session_block += f"  - {t}\n"

    # Trim summary to first 200 chars
    short_summary = re.sub(r"\s+", " ", output_summary.strip())[:200]
    session_block += f"- Summary: {short_summary}\n"

    # Read current file or start fresh
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8")
    else:
        content = _default_memory()

    # Append session under ## Sessions
    if "## Sessions" in content:
        content = content + "\n" + session_block
    else:
        content += "\n## Sessions\n\n" + session_block

    # Update State section
    new_total = len(existing_memory.sessions) + 1
    state_replacement = f"""\
## State
- last_run: {timestamp}
- last_goal: {plan.goal}
- total_sessions: {new_total}
- status: completed
"""
    if "## State" in content:
        content = re.sub(
            r"## State\n.*?(?=\n##|\Z)", state_replacement, content, flags=re.DOTALL
        )
    else:
        content += "\n" + state_replacement

    memory_path.write_text(content, encoding="utf-8")


def _default_memory() -> str:
    """Return starter content for a new memory.md file."""
    return """\
# Memory

This file is managed by the Markdown Agent.
It persists state across sessions so the agent can recall previous work.

## Context
Agent initialised. No prior sessions recorded.

## State
- last_run: never
- total_sessions: 0
- status: initialised

## Sessions

"""


# ── Public API ────────────────────────────────────────────────────────────────

def execute(
    plan_path: Path,
    memory_path: Path,
    output_path: Path,
    backend: Optional[LLMBackend] = None,
    verbose: bool = True,
    backend_override: Optional[str] = None,
    dry_run: bool = False,
    verbose_prompt: bool = False,
) -> str:
    """
    Execute the agent: read plan + memory, call LLM, write output + update memory.

    Args:
        plan_path: Path to plan.md
        memory_path: Path to memory.md
        output_path: Path to output.md
        backend: Pre-constructed backend (overrides backend_override)
        verbose: Print progress messages
        backend_override: Name of backend to force ('mock', 'anthropic', etc.)
        dry_run: Build prompt and write a dry-run summary; skip real LLM call
        verbose_prompt: Print the full prompt before generating

    Returns:
        The generated output text.
    """
    if backend is None:
        backend = get_backend(backend_override, dry_run=dry_run)

    # ── Read inputs ──────────────────────────────────────────────────────────
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    memory_text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else _default_memory()

    plan = parse_plan(plan_text)
    memory = parse_memory(memory_text)
    session_num = len(memory.sessions) + 1

    if verbose:
        print(f"[agent] Backend  : {backend.name}")
        print(f"[agent] Goal     : {plan.goal}")
        print(f"[agent] Tasks    : {len(plan.tasks)} ({len(plan.pending_tasks())} pending)")
        print(f"[agent] Sessions : {len(memory.sessions)} previous (this will be #{session_num})")

    # ── Ensure memory file exists ─────────────────────────────────────────────
    if not memory_path.exists():
        memory_path.write_text(_default_memory(), encoding="utf-8")
        if verbose:
            print(f"[agent] Created  : {memory_path}")

    # ── Build prompt & generate ───────────────────────────────────────────────
    prompt = build_prompt(plan, memory)

    if verbose_prompt:
        print("\n[agent] ── Prompt ──────────────────────────────────────────")
        print(prompt)
        print("[agent] ── End Prompt ──────────────────────────────────────\n")

    if verbose:
        print("[agent] Generating response…")

    t_start = time.monotonic()
    raw_response = backend.generate(
        prompt,
        max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "2048")),
    )
    elapsed = time.monotonic() - t_start

    if verbose:
        word_count = len(raw_response.split())
        print(f"[agent] Generated : {word_count} words in {elapsed:.2f}s")

    # ── Format & write output ────────────────────────────────────────────────
    output_text = _format_output(raw_response, plan, backend.name, elapsed, session_num)
    output_path.write_text(output_text, encoding="utf-8")
    if verbose:
        print(f"[agent] Written  : {output_path}")

    # ── Update memory (skip for dry-run to keep things clean) ─────────────────
    if not dry_run:
        _update_memory(memory_path, plan, raw_response, memory)
        if verbose:
            print(f"[agent] Updated  : {memory_path}")

    return output_text
