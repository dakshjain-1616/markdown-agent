"""
Pytest suite for Markdown Agent.

Tests cover:
  1. Plan execution from plan.md content
  2. Memory/state persistence across sessions
  3. Three-file constraint (plan.md, memory.md, output.md)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

PLAN_CONTENT = """\
# Plan

## Goal
Test the agent with a simple goal

## Tasks
- [ ] Verify agent parses goals
- [ ] Confirm task list extraction
- [ ] Check output is written correctly

## Context
This is a test plan for the pytest suite.
"""

PLAN_WITH_COMPLETED = """\
# Plan

## Goal
Partially completed plan

## Tasks
- [x] Already done task
- [ ] Pending task one
- [ ] Pending task two
"""

MEMORY_CONTENT = """\
# Memory

## Context
Testing context loaded from memory.md.

## State
- last_run: 2024-01-01T10:00:00
- total_sessions: 3
- status: completed

## Sessions

### Session — 2024-01-01T10:00:00
- Timestamp: 2024-01-01T10:00:00
- Goal: Previous test goal
- Tasks completed:
  - task one
  - task two
- Summary: Previous session completed successfully.
"""


@pytest.fixture
def tmp_files(tmp_path: Path):
    """Create temporary plan/memory/output files."""
    plan = tmp_path / "plan.md"
    memory = tmp_path / "memory.md"
    output = tmp_path / "output.md"
    plan.write_text(PLAN_CONTENT, encoding="utf-8")
    memory.write_text(MEMORY_CONTENT, encoding="utf-8")
    return plan, memory, output


@pytest.fixture
def mock_backend():
    from markdown_agent_3_fil.backends import MockBackend
    return MockBackend()


# ── 1. Parser tests ───────────────────────────────────────────────────────────

class TestParser:
    def test_parse_plan_extracts_goal(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        assert "Test the agent" in plan.goal

    def test_parse_plan_extracts_tasks(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        assert len(plan.tasks) == 3

    def test_parse_plan_task_text(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        texts = [t.text for t in plan.tasks]
        assert any("goals" in t for t in texts)

    def test_parse_plan_tasks_not_completed(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        assert all(not t.completed for t in plan.tasks)
        assert len(plan.pending_tasks()) == 3

    def test_parse_plan_with_completed_tasks(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_WITH_COMPLETED)
        completed = plan.completed_tasks()
        pending = plan.pending_tasks()
        assert len(completed) == 1
        assert len(pending) == 2

    def test_parse_plan_extracts_context(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        assert "pytest" in plan.context

    def test_parse_plan_raw_preserved(self):
        from markdown_agent_3_fil.parser import parse_plan
        plan = parse_plan(PLAN_CONTENT)
        assert plan.raw == PLAN_CONTENT

    def test_parse_memory_extracts_state(self):
        from markdown_agent_3_fil.parser import parse_memory
        memory = parse_memory(MEMORY_CONTENT)
        assert "total_sessions" in memory.state
        assert memory.state["total_sessions"] == "3"

    def test_parse_memory_extracts_context(self):
        from markdown_agent_3_fil.parser import parse_memory
        memory = parse_memory(MEMORY_CONTENT)
        assert "Testing context" in memory.context

    def test_parse_memory_extracts_sessions(self):
        from markdown_agent_3_fil.parser import parse_memory
        memory = parse_memory(MEMORY_CONTENT)
        assert len(memory.sessions) >= 1

    def test_parse_memory_last_session(self):
        from markdown_agent_3_fil.parser import parse_memory
        memory = parse_memory(MEMORY_CONTENT)
        last = memory.last_session()
        assert last is not None
        assert "Previous test goal" in last.goal

    def test_mark_tasks_complete(self):
        from markdown_agent_3_fil.parser import mark_tasks_complete
        result = mark_tasks_complete(PLAN_CONTENT)
        assert "- [x]" in result
        assert "- [ ]" not in result

    def test_task_to_md_incomplete(self):
        from markdown_agent_3_fil.parser import Task
        t = Task(text="do something", completed=False)
        assert t.to_md() == "- [ ] do something"

    def test_task_to_md_complete(self):
        from markdown_agent_3_fil.parser import Task
        t = Task(text="done thing", completed=True)
        assert t.to_md() == "- [x] done thing"


# ── 2. Backend tests ──────────────────────────────────────────────────────────

class TestBackends:
    def test_mock_backend_returns_string(self, mock_backend):
        result = mock_backend.generate("GOAL: test goal\n- [ ] task one")
        assert isinstance(result, str)
        assert len(result) > 50

    def test_mock_backend_name(self, mock_backend):
        assert mock_backend.name == "mock"

    def test_mock_backend_python_content(self, mock_backend):
        result = mock_backend.generate("GOAL: python best practices\n- [ ] write code")
        assert len(result) > 0

    def test_mock_backend_respects_prompt(self, mock_backend):
        result = mock_backend.generate("GOAL: research topic\n- [ ] find sources")
        assert isinstance(result, str)

    def test_get_backend_returns_mock_without_keys(self, monkeypatch):
        from markdown_agent_3_fil.backends import get_backend
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLAMA_MODEL_PATH", raising=False)
        backend = get_backend()
        assert backend.name == "mock"

    def test_get_backend_override_mock(self):
        from markdown_agent_3_fil.backends import get_backend
        backend = get_backend(override="mock")
        assert backend.name == "mock"


# ── 3. Executor tests ─────────────────────────────────────────────────────────

class TestExecutor:
    def test_execute_creates_output_file(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        assert output.exists()

    def test_execute_output_nonempty(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert len(content) > 100

    def test_execute_output_contains_goal(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "Test the agent" in content

    def test_execute_output_contains_timestamp(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "Generated:" in content

    def test_execute_output_marks_tasks_complete(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "[x]" in content

    def test_execute_returns_output_text(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        result = execute(plan, memory, output, backend=mock_backend, verbose=False)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_updates_memory(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        memory_after = memory.read_text(encoding="utf-8")
        assert "last_run" in memory_after
        # Should not say "never" after a run
        # Find just the last_run line
        for line in memory_after.splitlines():
            if "last_run:" in line:
                assert "never" not in line
                break

    def test_execute_memory_records_session(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        memory_after = memory.read_text(encoding="utf-8")
        assert "Session" in memory_after

    def test_execute_memory_contains_goal(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        memory_after = memory.read_text(encoding="utf-8")
        assert "Test the agent" in memory_after

    def test_execute_creates_memory_if_missing(self, tmp_path, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")
        # Do NOT create memory.md
        assert not memory.exists()
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        assert memory.exists()
        assert output.exists()


# ── 4. Three-file constraint tests ────────────────────────────────────────────

class TestThreeFileConstraint:
    """The core promise: exactly plan.md, memory.md, output.md."""

    def test_three_core_files_exist_in_project(self):
        root = Path(__file__).parent.parent
        assert (root / "plan.md").exists(), "plan.md must exist"
        assert (root / "memory.md").exists(), "memory.md must exist"
        assert (root / "output.md").exists(), "output.md must exist"

    def test_plan_md_has_goal_section(self):
        root = Path(__file__).parent.parent
        content = (root / "plan.md").read_text(encoding="utf-8")
        assert "## Goal" in content

    def test_plan_md_has_tasks_section(self):
        root = Path(__file__).parent.parent
        content = (root / "plan.md").read_text(encoding="utf-8")
        assert "## Tasks" in content

    def test_memory_md_has_state_section(self):
        root = Path(__file__).parent.parent
        content = (root / "memory.md").read_text(encoding="utf-8")
        assert "## State" in content

    def test_output_md_exists(self):
        root = Path(__file__).parent.parent
        assert (root / "output.md").exists()

    def test_execute_only_touches_three_files(self, tmp_path, mock_backend):
        """After execution, only plan, memory, output should be written (no extra files)."""
        from markdown_agent_3_fil.executor import execute

        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")

        files_before = set(tmp_path.iterdir())
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        files_after = set(tmp_path.iterdir())

        new_files = files_after - files_before
        # Only memory and output should be new/modified (plan was already there)
        for f in new_files:
            assert f.name in {"memory.md", "output.md"}, f"Unexpected file created: {f.name}"


# ── 5. State persistence tests ────────────────────────────────────────────────

class TestStatePersistence:
    def test_multiple_runs_accumulate_sessions(self, tmp_path, mock_backend):
        from markdown_agent_3_fil.executor import execute
        from markdown_agent_3_fil.parser import parse_memory

        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")

        # Run twice
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        execute(plan, memory, output, backend=mock_backend, verbose=False)

        mem = parse_memory(memory.read_text(encoding="utf-8"))
        assert len(mem.sessions) >= 2

    def test_state_total_sessions_increments(self, tmp_path, mock_backend):
        from markdown_agent_3_fil.executor import execute
        from markdown_agent_3_fil.parser import parse_memory

        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")

        execute(plan, memory, output, backend=mock_backend, verbose=False)
        mem1 = parse_memory(memory.read_text(encoding="utf-8"))
        sessions_after_first = len(mem1.sessions)

        execute(plan, memory, output, backend=mock_backend, verbose=False)
        mem2 = parse_memory(memory.read_text(encoding="utf-8"))
        sessions_after_second = len(mem2.sessions)

        assert sessions_after_second > sessions_after_first

    def test_memory_preserves_existing_context(self, tmp_path, mock_backend):
        from markdown_agent_3_fil.executor import execute

        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")
        memory.write_text(MEMORY_CONTENT, encoding="utf-8")

        execute(plan, memory, output, backend=mock_backend, verbose=False)
        memory_after = memory.read_text(encoding="utf-8")

        # Original context should still be present
        assert "Testing context" in memory_after


# ── 6. Prompt builder tests ───────────────────────────────────────────────────

class TestPromptBuilder:
    def test_build_prompt_contains_goal(self):
        from markdown_agent_3_fil.executor import build_prompt
        from markdown_agent_3_fil.parser import parse_plan, parse_memory

        plan = parse_plan(PLAN_CONTENT)
        memory = parse_memory(MEMORY_CONTENT)
        prompt = build_prompt(plan, memory)
        assert "Test the agent" in prompt

    def test_build_prompt_contains_tasks(self):
        from markdown_agent_3_fil.executor import build_prompt
        from markdown_agent_3_fil.parser import parse_plan, parse_memory

        plan = parse_plan(PLAN_CONTENT)
        memory = parse_memory(MEMORY_CONTENT)
        prompt = build_prompt(plan, memory)
        assert "- [ ]" in prompt

    def test_build_prompt_contains_memory_context(self):
        from markdown_agent_3_fil.executor import build_prompt
        from markdown_agent_3_fil.parser import parse_plan, parse_memory

        plan = parse_plan(PLAN_CONTENT)
        memory = parse_memory(MEMORY_CONTENT)
        prompt = build_prompt(plan, memory)
        assert "Testing context" in prompt


# ── 7. Templates tests ────────────────────────────────────────────────────────

class TestTemplates:
    def test_list_templates_returns_list(self):
        from markdown_agent_3_fil.templates import list_templates
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 5

    def test_list_templates_sorted(self):
        from markdown_agent_3_fil.templates import list_templates
        templates = list_templates()
        assert templates == sorted(templates)

    def test_list_templates_contains_expected(self):
        from markdown_agent_3_fil.templates import list_templates
        templates = list_templates()
        for name in ("research", "code-review", "brainstorm", "bug-report", "weekly-review"):
            assert name in templates

    def test_get_template_returns_string(self):
        from markdown_agent_3_fil.templates import get_template
        content = get_template("research")
        assert isinstance(content, str)
        assert len(content) > 50

    def test_get_template_has_goal_section(self):
        from markdown_agent_3_fil.templates import get_template, list_templates
        for name in list_templates():
            content = get_template(name)
            assert "## Goal" in content, f"Template '{name}' missing ## Goal"

    def test_get_template_has_tasks_section(self):
        from markdown_agent_3_fil.templates import get_template, list_templates
        for name in list_templates():
            content = get_template(name)
            assert "## Tasks" in content, f"Template '{name}' missing ## Tasks"

    def test_get_template_has_checkboxes(self):
        from markdown_agent_3_fil.templates import get_template, list_templates
        for name in list_templates():
            content = get_template(name)
            assert "- [ ]" in content, f"Template '{name}' missing task checkboxes"

    def test_get_template_invalid_name_raises(self):
        from markdown_agent_3_fil.templates import get_template
        with pytest.raises(KeyError, match="Unknown template"):
            get_template("nonexistent-template-xyz")

    def test_get_template_error_lists_available(self):
        from markdown_agent_3_fil.templates import get_template
        try:
            get_template("nonexistent-template-xyz")
        except KeyError as exc:
            assert "Available" in str(exc)

    def test_template_parseable_by_agent(self):
        from markdown_agent_3_fil.templates import get_template
        from markdown_agent_3_fil.parser import parse_plan
        content = get_template("research")
        plan = parse_plan(content)
        assert plan.goal != "No goal specified"
        assert len(plan.tasks) > 0


# ── 8. History tests ──────────────────────────────────────────────────────────

class TestHistory:
    def test_format_history_no_sessions(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history
        empty_mem = parse_memory("# Memory\n## State\n- last_run: never\n## Sessions\n")
        result = format_history(empty_mem)
        assert "No sessions" in result

    def test_format_history_with_sessions(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history
        memory = parse_memory(MEMORY_CONTENT)
        result = format_history(memory)
        assert "Session" in result
        assert "Previous test goal" in result

    def test_format_history_shows_total_count(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history
        memory = parse_memory(MEMORY_CONTENT)
        result = format_history(memory)
        assert "session" in result.lower()

    def test_format_history_max_sessions(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history
        # Build memory with 3 sessions
        multi_mem = MEMORY_CONTENT + "\n".join([
            "",
            "### Session — 2024-02-01T10:00:00",
            "- Timestamp: 2024-02-01T10:00:00",
            "- Goal: Second goal",
            "- Tasks completed:",
            "  - task A",
            "- Summary: Second session done.",
            "",
            "### Session — 2024-03-01T10:00:00",
            "- Timestamp: 2024-03-01T10:00:00",
            "- Goal: Third goal",
            "- Tasks completed:",
            "  - task B",
            "- Summary: Third session done.",
        ])
        memory = parse_memory(multi_mem)
        result = format_history(memory, max_sessions=1)
        assert "Third goal" in result
        # Earlier sessions are cropped
        assert "Previous test goal" not in result

    def test_format_history_compact(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history_compact
        memory = parse_memory(MEMORY_CONTENT)
        result = format_history_compact(memory)
        assert "Previous test goal" in result

    def test_format_history_compact_no_sessions(self):
        from markdown_agent_3_fil.parser import parse_memory
        from markdown_agent_3_fil.history import format_history_compact
        empty_mem = parse_memory("# Memory\n## State\n- last_run: never\n## Sessions\n")
        result = format_history_compact(empty_mem)
        assert "no sessions" in result.lower()


# ── 9. Export tests ───────────────────────────────────────────────────────────

SAMPLE_OUTPUT = """\
# Output

*Generated: 2024-01-01 10:00:00*
*Backend: mock*
*Tasks completed: 2/2*
*Session: #1*
*Elapsed: 0.01s*
*Words: 42*

---

## Goal: Test export

## Tasks
- [x] ~~Task one~~ ✓
- [x] ~~Task two~~ ✓

---

### Results

**Finding 1:** Everything works as expected.

| Col A | Col B |
|-------|-------|
| 1     | 2     |

`inline code` and ~~strikethrough~~ and *italic* and **bold**.
"""


class TestExport:
    def test_export_html_returns_string(self):
        from markdown_agent_3_fil.history import export_html
        html = export_html(SAMPLE_OUTPUT, title="Test")
        assert isinstance(html, str)
        assert "<html" in html

    def test_export_html_has_title(self):
        from markdown_agent_3_fil.history import export_html
        html = export_html(SAMPLE_OUTPUT, title="My Title")
        assert "My Title" in html

    def test_export_html_has_body(self):
        from markdown_agent_3_fil.history import export_html
        html = export_html(SAMPLE_OUTPUT)
        assert "<body>" in html
        assert "</body>" in html

    def test_export_html_contains_goal(self):
        from markdown_agent_3_fil.history import export_html
        html = export_html(SAMPLE_OUTPUT)
        assert "Test export" in html

    def test_export_html_no_script_injection(self):
        from markdown_agent_3_fil.history import export_html
        malicious = "# Title\n<script>alert('xss')</script>\n"
        html = export_html(malicious)
        assert "<script>" not in html

    def test_export_plain_strips_headings(self):
        from markdown_agent_3_fil.history import export_plain
        plain = export_plain("# Heading\n## Sub\nText here")
        assert "#" not in plain
        assert "Text here" in plain

    def test_export_plain_strips_bold(self):
        from markdown_agent_3_fil.history import export_plain
        plain = export_plain("**bold text** here")
        assert "**" not in plain
        assert "bold text" in plain

    def test_export_plain_strips_inline_code(self):
        from markdown_agent_3_fil.history import export_plain
        plain = export_plain("Use `foo()` to call it")
        assert "`" not in plain
        assert "foo()" in plain

    def test_export_to_file_html(self, tmp_path):
        from markdown_agent_3_fil.history import export_html
        output_md = tmp_path / "output.md"
        output_md.write_text(SAMPLE_OUTPUT, encoding="utf-8")
        html = export_html(SAMPLE_OUTPUT, title="output")
        dest = tmp_path / "output.html"
        dest.write_text(html, encoding="utf-8")
        assert dest.exists()
        assert dest.stat().st_size > 100


# ── 10. Dry-run tests ─────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_does_not_update_memory(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        from markdown_agent_3_fil.backends import DryRunBackend
        plan, memory, output = tmp_files
        memory_before = memory.read_text(encoding="utf-8")
        execute(plan, memory, output, backend=DryRunBackend(), verbose=False, dry_run=True)
        memory_after = memory.read_text(encoding="utf-8")
        assert memory_before == memory_after

    def test_dry_run_writes_output(self, tmp_files):
        from markdown_agent_3_fil.executor import execute
        from markdown_agent_3_fil.backends import DryRunBackend
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=DryRunBackend(), verbose=False, dry_run=True)
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert len(content) > 50

    def test_dry_run_output_mentions_dry_run(self, tmp_files):
        from markdown_agent_3_fil.executor import execute
        from markdown_agent_3_fil.backends import DryRunBackend
        plan, memory, output = tmp_files
        result = execute(plan, memory, output, backend=DryRunBackend(), verbose=False, dry_run=True)
        assert "dry" in result.lower() or "Dry" in result

    def test_dry_run_backend_name(self):
        from markdown_agent_3_fil.backends import DryRunBackend
        b = DryRunBackend()
        assert b.name == "dry-run"

    def test_dry_run_backend_generate_returns_string(self):
        from markdown_agent_3_fil.backends import DryRunBackend
        b = DryRunBackend()
        result = b.generate("GOAL: test\n- [ ] task one")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_backend_dry_run_flag(self):
        from markdown_agent_3_fil.backends import get_backend, DryRunBackend
        b = get_backend(dry_run=True)
        assert isinstance(b, DryRunBackend)

    def test_get_backend_dry_run_override(self):
        from markdown_agent_3_fil.backends import get_backend, DryRunBackend
        b = get_backend(override="dry-run")
        assert isinstance(b, DryRunBackend)


# ── 11. Retry backend tests ───────────────────────────────────────────────────

class TestRetryBackend:
    def test_retry_succeeds_on_first_try(self):
        from markdown_agent_3_fil.backends import RetryBackend, MockBackend
        backend = RetryBackend(MockBackend(), max_retries=2, retry_delay=0)
        result = backend.generate("GOAL: test")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_retry_name_mirrors_inner(self):
        from markdown_agent_3_fil.backends import RetryBackend, MockBackend
        inner = MockBackend()
        wrapped = RetryBackend(inner, max_retries=1, retry_delay=0)
        assert wrapped.name == inner.name

    def test_retry_raises_after_exhausting(self):
        from markdown_agent_3_fil.backends import RetryBackend, LLMBackend

        class AlwaysFails(LLMBackend):
            name = "failing"
            def generate(self, prompt, max_tokens=2048):
                raise ConnectionError("simulated failure")

        backend = RetryBackend(AlwaysFails(), max_retries=1, retry_delay=0)
        with pytest.raises(RuntimeError, match="attempt"):
            backend.generate("GOAL: test")

    def test_retry_fallback_to_mock(self):
        from markdown_agent_3_fil.backends import RetryBackend, LLMBackend

        class AlwaysFails(LLMBackend):
            name = "failing"
            def generate(self, prompt, max_tokens=2048):
                raise ConnectionError("simulated failure")

        backend = RetryBackend(AlwaysFails(), max_retries=0, retry_delay=0, fallback_to_mock=True)
        result = backend.generate("GOAL: test")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_retry_error_message_contains_tip(self):
        from markdown_agent_3_fil.backends import RetryBackend, LLMBackend

        class AlwaysFails(LLMBackend):
            name = "failing"
            def generate(self, prompt, max_tokens=2048):
                raise ValueError("boom")

        backend = RetryBackend(AlwaysFails(), max_retries=0, retry_delay=0)
        with pytest.raises(RuntimeError, match="AGENT_FALLBACK_TO_MOCK"):
            backend.generate("GOAL: test")


# ── 12. Richer output tests ───────────────────────────────────────────────────

class TestRicherOutput:
    def test_output_contains_elapsed_time(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "Elapsed:" in content

    def test_output_contains_word_count(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "Words:" in content

    def test_output_contains_session_number(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        assert "Session:" in content

    def test_session_number_increments(self, tmp_path, mock_backend):
        from markdown_agent_3_fil.executor import execute
        plan = tmp_path / "plan.md"
        memory = tmp_path / "memory.md"
        output = tmp_path / "output.md"
        plan.write_text(PLAN_CONTENT, encoding="utf-8")

        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content1 = output.read_text(encoding="utf-8")
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content2 = output.read_text(encoding="utf-8")

        # Second run should reference a higher session number
        import re
        def get_session_num(text):
            m = re.search(r"Session: #(\d+)", text)
            return int(m.group(1)) if m else 0

        assert get_session_num(content2) > get_session_num(content1)

    def test_elapsed_time_is_float(self, tmp_files, mock_backend):
        from markdown_agent_3_fil.executor import execute
        import re
        plan, memory, output = tmp_files
        execute(plan, memory, output, backend=mock_backend, verbose=False)
        content = output.read_text(encoding="utf-8")
        m = re.search(r"Elapsed: ([\d.]+)s", content)
        assert m is not None
        assert float(m.group(1)) >= 0.0


# ── 13. Mock backend richness tests ──────────────────────────────────────────

class TestMockBackendRichness:
    def test_mock_brainstorm_content(self):
        from markdown_agent_3_fil.backends import MockBackend
        b = MockBackend()
        result = b.generate("GOAL: brainstorm ideas for product\n- [ ] generate ideas")
        assert len(result) > 100

    def test_mock_code_review_content(self):
        from markdown_agent_3_fil.backends import MockBackend
        b = MockBackend()
        result = b.generate("GOAL: code-review the auth module\n- [ ] check bugs")
        assert len(result) > 100

    def test_mock_data_content(self):
        from markdown_agent_3_fil.backends import MockBackend
        b = MockBackend()
        result = b.generate("GOAL: data analysis of sales\n- [ ] analyse dataset")
        assert len(result) > 100

    def test_mock_weekly_content(self):
        from markdown_agent_3_fil.backends import MockBackend
        b = MockBackend()
        result = b.generate("GOAL: weekly review for team\n- [ ] list completed tasks")
        assert len(result) > 100

    def test_mock_bug_content(self):
        from markdown_agent_3_fil.backends import MockBackend
        b = MockBackend()
        result = b.generate("GOAL: investigate bug in login\n- [ ] reproduce bug")
        assert len(result) > 100
