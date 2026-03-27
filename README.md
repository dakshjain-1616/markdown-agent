# Markdown-Agent – AI agent in three plain text files

> *Made autonomously using [NEO](https://heyneo.so) · [![Install NEO Extension](https://img.shields.io/badge/VS%20Code-Install%20NEO-7B61FF?logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=NeoResearchInc.heyneo)*

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-89%20passed-brightgreen.svg)]()

> Edit `plan.md` in any text editor, run one command, and read the AI's response in `output.md` — no server, no database, no cloud account needed.

## Install

```bash
git clone https://github.com/dakshjain-1616/markdown-agent
cd markdown-agent
pip install -r requirements.txt
```

## The Problem

AI agent frameworks like LangChain, AutoGPT, and CrewAI force you to stand up server processes, configure vector databases, and navigate proprietary DSLs before your agent does anything useful. Persistent memory usually means wiring up managed databases where your agent's knowledge is locked in opaque tables you cannot read, edit, or commit to Git.

## Who it's for

This is for developers building local-first tools or prototyping agent workflows who need full transparency over state. You are tired of black-box agent memory and want to `git diff` your agent's thoughts, hand-edit its context, and run inference locally without cloud dependencies.

## Quickstart

```bash
# 1. Define your goal in plan.md
echo "# Create a summary of the project" > plan.md

# 2. Initialize memory (empty file)
touch memory.md

# 3. Run the agent
python examples/01_quick_start.py

# 4. Read the result
cat output.md
```

## Key features

- **Three-file architecture** — All agent state lives in `plan.md`, `memory.md`, and `output.md`; no database, no server
- **Local LLM support** — Runs with `llama-cpp-python` for offline GGUF models or switches to cloud APIs via environment variables
- **Git-friendly state** — Memory accumulates in plain text files that can be version-controlled, audited, and hand-edited
- **No code required** — Define agent behavior entirely through Markdown structure without writing Python logic

## Run tests

```bash
pytest tests/ -q
# 89 passed
```

## Project structure

```
markdown-agent/
├── markdown_agent_3_fil/  ← main library
├── examples/              ← usage demos
├── tests/                 ← test suite
└── requirements.txt
```