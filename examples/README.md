# Examples

Runnable scripts demonstrating Markdown Agent features.
Each script works from any directory — no setup beyond `pip install -r requirements.txt`.

## Running an example

```bash
# From the project root
python examples/01_quick_start.py
python examples/02_advanced_usage.py
python examples/03_custom_config.py
python examples/04_full_pipeline.py
```

## Scripts

| Script | What it demonstrates |
|--------|---------------------|
| [`01_quick_start.py`](01_quick_start.py) | Minimal working example — write a plan, run the agent, print the output (10-20 lines) |
| [`02_advanced_usage.py`](02_advanced_usage.py) | Multi-run sessions with persistent memory, `format_history`, `format_history_compact`, HTML and plain-text export |
| [`03_custom_config.py`](03_custom_config.py) | Customising behaviour via env vars (`AGENT_MAX_TOKENS`, `AGENT_BACKEND`), dry-run mode, explicit backend selection |
| [`04_full_pipeline.py`](04_full_pipeline.py) | End-to-end workflow: bootstrap from template → 3 agent runs → session history → HTML / plain / JSON export |

## Environment variables (optional)

All examples run in mock mode with zero configuration. To use a real LLM:

```bash
# Anthropic Claude
export ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
export OPENAI_API_KEY=sk-...

# Local GGUF model
export LLAMA_MODEL_PATH=/path/to/model.gguf
```

See `.env.example` in the project root for the full list of options.
