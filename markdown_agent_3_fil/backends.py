"""LLM backends: llama-cpp-python, Anthropic, OpenAI, Mock, and DryRun."""

from __future__ import annotations

import os
import re
import textwrap
import time
from pathlib import Path
from typing import Optional


# ── Protocol / base ─────────────────────────────────────────────────────────

class LLMBackend:
    """Abstract LLM backend."""

    name: str = "base"

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:  # noqa: D401
        raise NotImplementedError


# ── Mock backend ─────────────────────────────────────────────────────────────

_MOCK_CONTENT_MAP: dict[str, str] = {
    "python": textwrap.dedent("""\
        ### Python Best Practices Findings

        After thorough analysis of Python community guidelines (PEP 8, PEP 20, PEP 257):

        **1. Code Style**
        - Follow PEP 8 for naming, spacing, and line length (79 chars for code, 72 for docstrings)
        - Use `black` or `ruff format` for auto-formatting

        **2. Type Annotations**
        - Annotate all public functions: `def greet(name: str) -> str:`
        - Use `from __future__ import annotations` for forward references

        **3. Error Handling**
        - Catch specific exceptions, not bare `except:`
        - Use context managers (`with` statements) for resource cleanup

        **4. Project Structure**
        - Organise code into packages with `__init__.py`
        - Keep `requirements.txt` and `pyproject.toml` at the root

        **5. Testing**
        - Write tests with `pytest`; aim for ≥80% coverage
        - Use `fixtures` for shared setup, `parametrize` for data-driven tests
    """),
    "summary": textwrap.dedent("""\
        ### Executive Summary

        **Key Findings:**
        - Data analysis completed across all requested dimensions
        - 3 primary patterns identified in the dataset
        - Recommendations generated based on observed trends

        **Metrics:**
        | Metric | Value |
        |--------|-------|
        | Items Processed | 1,247 |
        | Patterns Found  | 3 |
        | Confidence      | 94% |

        **Top Recommendations:**
        1. Focus on high-impact areas first (ROI: 3.2x)
        2. Automate repetitive sub-tasks
        3. Schedule a follow-up review in 30 days
    """),
    "research": textwrap.dedent("""\
        ### Research Results

        **Literature Review:**
        Multiple authoritative sources were reviewed. Key consensus points:

        - Primary mechanism is well-established (confidence: high)
        - Recent developments suggest a shift in best practice
        - Three competing approaches exist; each has trade-offs

        **Comparison Matrix:**
        | Approach | Speed | Quality | Complexity |
        |----------|-------|---------|------------|
        | Method A | Fast  | Medium  | Low        |
        | Method B | Slow  | High    | High       |
        | Method C | Med   | High    | Medium     |

        **Recommendation:** Method C offers the best balance.
    """),
    "code-review": textwrap.dedent("""\
        ### Code Review Findings

        **Critical Issues (0)**
        No blocking issues found.

        **Major Issues (2)**
        - `auth.py:42` — Bare `except:` swallows all exceptions; use `except ValueError`
        - `db.py:17` — Connection not closed in error path; use `with` context manager

        **Minor Issues (3)**
        - `utils.py:8` — Variable name `x` is not descriptive; rename to `item_count`
        - Missing docstrings on 3 public functions
        - Line length exceeds 79 chars in 2 places

        **Nits**
        - Prefer f-strings over `.format()` for readability

        **Overall:** Good structure. Address the 2 major issues before merging.
        Confidence: high | Coverage reviewed: 100%
    """),
    "brainstorm": textwrap.dedent("""\
        ### Brainstorm Results

        **Raw Ideas (12 generated)**
        1. Automate onboarding with a chatbot
        2. Create a self-service knowledge base
        3. Introduce async task processing
        4. Add real-time notifications
        5. Build a CLI companion tool
        6. Gamify progress tracking
        7. Integrate with existing calendar tools
        8. Use AI to auto-tag and categorise entries
        9. Provide a dark-mode dashboard
        10. Export reports as PDF
        11. Add a mobile-first view
        12. Enable webhook-based integrations

        **Grouped by Theme:**
        - **Automation:** 1, 3, 8
        - **UX / Accessibility:** 2, 9, 11
        - **Integration:** 4, 7, 12
        - **Developer Tools:** 5, 10, 6

        **Top 3 (ranked by feasibility × impact):**
        1. **Auto-tag with AI** (idea 8) — high impact, moderate effort
        2. **Webhook integrations** (idea 12) — multiplies reach, low effort
        3. **CLI companion** (idea 5) — targets power users, low effort

        **Next step:** Prototype idea 8 with a mock classifier this week.
    """),
    "bug": textwrap.dedent("""\
        ### Bug Investigation Report

        **Root Cause Identified**
        The issue originates in the state management layer. A race condition between
        the write and read operations causes stale data to be returned under concurrent
        load (> 10 req/s).

        **Reproduction Steps**
        1. Start 3 concurrent workers against the shared queue
        2. Submit 50 items in rapid succession
        3. Observe ~15% of reads return the previous value

        **Fix Options:**
        | Option | Complexity | Risk | Notes |
        |--------|-----------|------|-------|
        | Add mutex lock | Low | Low | Serialises writes; safe choice |
        | Use atomic CAS | Medium | Medium | Better throughput |
        | Refactor to event sourcing | High | High | Overkill for now |

        **Recommended Fix:** Add mutex lock. Estimated effort: 2 hours.

        **Regression Test:**
        ```python
        def test_concurrent_write_read():
            # spin up 10 threads, verify final state is consistent
        ```
    """),
    "data": textwrap.dedent("""\
        ### Data Analysis Results

        **Dataset Overview**
        - Shape: 10,420 rows × 14 columns
        - Missing values: 3 columns with <2% nulls (imputed with median)
        - Date range: 2023-01-01 → 2024-12-31

        **Key Statistics**
        | Metric | Value |
        |--------|-------|
        | Mean   | 142.3 |
        | Median | 138.7 |
        | Std Dev | 28.4 |
        | Outliers (>3σ) | 47 rows (0.45%) |

        **Patterns & Trends**
        - Strong seasonal spike in Q4 (+32% vs baseline)
        - Negative correlation between feature_A and target (r = -0.68)
        - Cluster analysis reveals 3 distinct user segments

        **Confidence:** High (95% CI: ±4.2)

        **Recommendations:**
        1. Remove or cap outliers before modelling
        2. Engineer a Q4 seasonality feature
        3. Train separate models per user segment
    """),
    "weekly": textwrap.dedent("""\
        ### Weekly Review

        **Completed This Week**
        - Shipped v2.1 hotfix (bug #312, #318)
        - Completed API integration with partner service
        - Onboarded two new team members

        **What Went Well**
        - Pair programming sessions cut review cycle from 2 days to 4 hours
        - Automated deploy pipeline saved ~3 hours of manual work

        **Blockers & Unresolved**
        - Staging environment still flaky — follow up with DevOps on Monday
        - Design review for v2.2 postponed to next week

        **Top 3 Priorities Next Week**
        1. Complete v2.2 design review
        2. Write integration tests for the new API endpoints
        3. Resolve staging environment instability

        **Notes for Memory**
        - v2.2 kickoff scheduled; design doc lives in Notion
        - Partner API rate limit: 1000 req/min (document in README)
    """),
    "default": textwrap.dedent("""\
        ### Task Results

        All requested tasks have been completed successfully.

        **Actions taken:**
        - Analysed the provided goal and decomposed it into actionable steps
        - Executed each step sequentially, verifying outputs at each stage
        - Consolidated results into this structured report

        **Outcome:**
        The plan has been fully executed. Key outputs are documented below.
        State has been updated in memory.md for future context continuity.

        **Next suggested steps:**
        1. Review the outputs in this file
        2. Update plan.md with any follow-up tasks
        3. Run `python run_agent.py` again to continue
    """),
}


def _mock_content_for(goal: str, tasks: list[str]) -> str:
    text = (goal + " " + " ".join(tasks)).lower()
    for keyword, content in _MOCK_CONTENT_MAP.items():
        if keyword != "default" and keyword in text:
            return content
    return _MOCK_CONTENT_MAP["default"]


class MockBackend(LLMBackend):
    """Deterministic mock backend for tests and demo mode."""

    name = "mock"

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        # Extract goal/tasks from prompt for contextual mock output
        goal_m = re.search(r"GOAL:\s*(.+)", prompt)
        task_matches = re.findall(r"- \[.\] (.+)", prompt)
        goal = goal_m.group(1).strip() if goal_m else ""
        return _mock_content_for(goal, task_matches)


# ── DryRun backend ────────────────────────────────────────────────────────────

class DryRunBackend(LLMBackend):
    """Dry-run backend: echoes what would be sent, generates no real output."""

    name = "dry-run"

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        lines = prompt.splitlines()
        goal_line = next((l for l in lines if l.startswith("GOAL:")), "GOAL: (not found)")
        task_lines = [l for l in lines if re.match(r"\s*- \[.\]", l)]
        summary = [
            "### Dry-Run Summary",
            "",
            f"**{goal_line}**",
            "",
            f"**Tasks ({len(task_lines)}):**",
        ] + [f"  {t}" for t in task_lines] + [
            "",
            f"*Prompt length: {len(prompt)} characters / ~{len(prompt)//4} tokens*",
            "*No LLM was called. Remove `--dry-run` to generate real output.*",
        ]
        return "\n".join(summary)


# ── Retry wrapper ─────────────────────────────────────────────────────────────

class RetryBackend(LLMBackend):
    """Wraps any backend with retry logic and optional fallback to mock."""

    def __init__(
        self,
        backend: LLMBackend,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        fallback_to_mock: bool = False,
    ) -> None:
        self._backend = backend
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._fallback_to_mock = fallback_to_mock

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._backend.name

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        last_exc: Exception | None = None
        for attempt in range(1 + self._max_retries):
            try:
                return self._backend.generate(prompt, max_tokens)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._max_retries:
                    print(
                        f"[retry] Attempt {attempt + 1} failed: {exc}. "
                        f"Retrying in {self._retry_delay}s…"
                    )
                    time.sleep(self._retry_delay)

        if self._fallback_to_mock:
            print(
                f"[retry] All {1 + self._max_retries} attempt(s) failed. "
                "Falling back to mock backend."
            )
            return MockBackend().generate(prompt, max_tokens)

        raise RuntimeError(
            f"Backend '{self._backend.name}' failed after "
            f"{1 + self._max_retries} attempt(s). Last error: {last_exc}\n"
            "Tip: set AGENT_FALLBACK_TO_MOCK=true to use mock output instead."
        ) from last_exc


# ── Anthropic backend ────────────────────────────────────────────────────────

class AnthropicBackend(LLMBackend):
    """Backend using the Anthropic Claude API."""

    name = "anthropic"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Install anthropic: pip install anthropic>=0.40.0"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text


# ── OpenAI backend ───────────────────────────────────────────────────────────

class OpenAIBackend(LLMBackend):
    """Backend using the OpenAI API (or compatible endpoint)."""

    name = "openai"

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Install openai: pip install openai>=1.0.0"
            ) from exc
        base_url = os.getenv("OPENAI_BASE_URL", None)
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""


# ── llama-cpp-python backend ─────────────────────────────────────────────────

class LlamaBackend(LLMBackend):
    """Backend using a local GGUF model via llama-cpp-python."""

    name = "llama"

    def __init__(self, model_path: str) -> None:
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "Install llama-cpp-python: pip install llama-cpp-python>=0.2.0"
            ) from exc
        n_ctx = int(os.getenv("LLAMA_N_CTX", "4096"))
        n_threads = int(os.getenv("LLAMA_N_THREADS", "4"))
        n_gpu_layers = int(os.getenv("LLAMA_N_GPU_LAYERS", "0"))
        self._llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        output = self._llm(
            prompt,
            max_tokens=max_tokens,
            stop=["</s>", "Human:", "User:"],
            echo=False,
        )
        return output["choices"][0]["text"].strip()


# ── factory ──────────────────────────────────────────────────────────────────

def get_backend(
    override: Optional[str] = None,
    dry_run: bool = False,
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    fallback_to_mock: Optional[bool] = None,
) -> LLMBackend:
    """
    Auto-detect the best available LLM backend.

    Priority:
      1. ``dry_run=True`` or ``override="dry-run"`` → DryRunBackend
      2. ``override`` argument (one of: mock, anthropic, openai, llama)
      3. LLAMA_MODEL_PATH env var → llama-cpp-python
      4. ANTHROPIC_API_KEY env var → Anthropic Claude
      5. OPENAI_API_KEY env var → OpenAI
      6. MockBackend (always available, no keys required)

    Retry settings come from arguments or env vars:
      AGENT_MAX_RETRIES   (default 2)
      AGENT_RETRY_DELAY   (default 1.0)
      AGENT_FALLBACK_TO_MOCK (default false)
    """
    if dry_run or override == "dry-run":
        return DryRunBackend()

    if override == "mock":
        return MockBackend()

    raw: LLMBackend

    if override == "llama" or (
        override is None and os.getenv("LLAMA_MODEL_PATH")
    ):
        model_path = os.getenv("LLAMA_MODEL_PATH", "")
        if Path(model_path).exists():
            raw = LlamaBackend(model_path)
        else:
            raw = MockBackend()
    elif override == "anthropic" or (
        override is None and os.getenv("ANTHROPIC_API_KEY")
    ):
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if key:
            raw = AnthropicBackend(key)
        else:
            raw = MockBackend()
    elif override == "openai" or (
        override is None and os.getenv("OPENAI_API_KEY")
    ):
        key = os.getenv("OPENAI_API_KEY", "")
        if key:
            raw = OpenAIBackend(key)
        else:
            raw = MockBackend()
    else:
        raw = MockBackend()

    # Don't wrap mock or dry-run in retry — they never fail
    if isinstance(raw, MockBackend):
        return raw

    # Resolve retry config from args or env
    _retries = max_retries if max_retries is not None else int(os.getenv("AGENT_MAX_RETRIES", "2"))
    _delay = retry_delay if retry_delay is not None else float(os.getenv("AGENT_RETRY_DELAY", "1.0"))
    _fallback = (
        fallback_to_mock
        if fallback_to_mock is not None
        else os.getenv("AGENT_FALLBACK_TO_MOCK", "false").lower() in ("1", "true", "yes")
    )

    if _retries > 0 or _fallback:
        return RetryBackend(raw, max_retries=_retries, retry_delay=_delay, fallback_to_mock=_fallback)
    return raw
