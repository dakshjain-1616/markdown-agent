"""Built-in plan templates for bootstrapping plan.md."""

from __future__ import annotations

from typing import Dict

_TEMPLATES: Dict[str, str] = {
    "research": """\
# Plan

## Goal
Research [TOPIC] and produce a structured summary

## Tasks
- [ ] Define the scope and key questions to answer
- [ ] Review primary sources and reference material
- [ ] Identify main themes, patterns, and insights
- [ ] Summarise findings with supporting evidence
- [ ] List open questions and next steps

## Context
Audience: [describe audience]
Depth: comprehensive / overview (pick one)
Output format: structured report with sections
""",
    "code-review": """\
# Plan

## Goal
Review [CODEBASE / PR / FILE] for quality, correctness, and style

## Tasks
- [ ] Check for correctness and potential bugs
- [ ] Evaluate code style and readability (naming, structure, PEP 8)
- [ ] Identify security or performance issues
- [ ] Suggest refactoring improvements
- [ ] Write a prioritised list of findings (critical / major / minor / nit)

## Context
Language: [e.g. Python 3.12]
Scope: [e.g. authentication module, PR #42]
Severity scale: critical / major / minor / nit
""",
    "brainstorm": """\
# Plan

## Goal
Brainstorm ideas for [TOPIC / PROBLEM]

## Tasks
- [ ] Generate a broad list of 10+ ideas without filtering
- [ ] Group ideas by theme or category
- [ ] Evaluate each group: pros, cons, feasibility
- [ ] Rank top 3 ideas with reasoning
- [ ] Propose a concrete next step for the top idea

## Context
Constraints: [time / budget / technical limits]
Audience: [who will use or evaluate these ideas]
Goal: innovation / practical / quick-wins (pick one)
""",
    "bug-report": """\
# Plan

## Goal
Investigate and document the root cause of [BUG DESCRIPTION]

## Tasks
- [ ] Reproduce the bug with a minimal test case
- [ ] Trace the execution path to the failure point
- [ ] Identify the root cause (not just the symptom)
- [ ] Propose one or more fixes with trade-off analysis
- [ ] Draft a regression test to prevent recurrence

## Context
Environment: [OS, Python version, library versions]
Severity: critical / major / minor
Observed behaviour: [what happens]
Expected behaviour: [what should happen]
""",
    "weekly-review": """\
# Plan

## Goal
Conduct a structured weekly review for the week of [DATE]

## Tasks
- [ ] List completed tasks and deliverables from the past week
- [ ] Identify what went well and capture key learnings
- [ ] Note blockers, delays, or unresolved items
- [ ] Set top 3 priorities for the coming week
- [ ] Update any relevant project documentation or notes

## Context
Team / project: [name]
Time-box: 30 minutes max
Format: concise bullet points, action-oriented
""",
    "data-analysis": """\
# Plan

## Goal
Analyse [DATASET / DATA SOURCE] to answer [QUESTION]

## Tasks
- [ ] Describe the dataset: shape, types, missing values
- [ ] Identify patterns, trends, and outliers
- [ ] Compute key statistics (mean, median, distribution)
- [ ] Visualise findings (describe charts or tables)
- [ ] State conclusions and confidence level

## Context
Dataset: [path or description]
Key metric: [what to optimise or understand]
Audience: technical / executive / both (pick one)
""",
}


def list_templates() -> list[str]:
    """Return sorted list of available template names."""
    return sorted(_TEMPLATES)


def get_template(name: str) -> str:
    """Return template content by name. Raises KeyError if not found."""
    if name not in _TEMPLATES:
        available = ", ".join(list_templates())
        raise KeyError(f"Unknown template '{name}'. Available: {available}")
    return _TEMPLATES[name]
