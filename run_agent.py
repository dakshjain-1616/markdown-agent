#!/usr/bin/env python3
"""
Markdown Agent Runner
=====================
Run the agent once or watch plan.md for changes.

Usage:
    python run_agent.py                          # single run
    python run_agent.py --watch                  # watch mode
    python run_agent.py --dry-run                # show plan without calling LLM
    python run_agent.py --backend mock           # force mock backend
    python run_agent.py --plan my_plan.md        # custom file paths
    python run_agent.py --history                # view session history
    python run_agent.py --history --history-n 5  # view last 5 sessions
    python run_agent.py --template research      # bootstrap plan.md from template
    python run_agent.py --list-templates         # list available templates
    python run_agent.py --export html            # export output.md to HTML
    python run_agent.py --export json            # export output.md + metadata to JSON
    python run_agent.py --export plain           # export output.md as plain text
    python run_agent.py --verbose-prompt         # print the LLM prompt before generating
    python run_agent.py --version                # print version and exit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from markdown_agent_3_fil import execute, __version__
from markdown_agent_3_fil.backends import get_backend

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


def _banner() -> None:
    """Print the Rich startup banner with project name, version, and NEO attribution."""
    panel = Panel(
        f"[bold cyan]Markdown Agent[/bold cyan]  [dim]v{__version__}[/dim]\n"
        "[dim]3 files · stateful AI · runs in terminal[/dim]\n"
        "[dim]Built with [link=https://heyneo.so]NEO[/link] — heyneo.so[/dim]",
        title="[bold white]✦ NEO[/bold white]",
        border_style="cyan",
        padding=(0, 2),
        expand=False,
    )
    console.print(panel)
    console.print()


def _run_once(args: argparse.Namespace) -> None:
    """Execute the agent once, writing output.md and updating memory.md."""
    plan_path = Path(args.plan)
    memory_path = Path(args.memory)
    output_path = Path(args.output)

    if not plan_path.exists():
        console.print(f"[bold red][error][/bold red] plan file not found: [cyan]{plan_path}[/cyan]")
        console.print("        Create plan.md or pass --plan <path>")
        console.print("        [yellow]Tip:[/yellow] use --template <name> to bootstrap a plan.md")
        sys.exit(1)

    backend_name = args.backend if args.backend != "auto" else None
    backend = get_backend(
        backend_name,
        dry_run=args.dry_run,
        max_retries=args.retries,
        retry_delay=args.retry_delay,
        fallback_to_mock=args.fallback_to_mock,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        console=console,
        transient=True,
        disable=args.quiet,
    ) as progress:
        task = progress.add_task("[cyan]Running agent…[/cyan]", total=None)
        execute(
            plan_path=plan_path,
            memory_path=memory_path,
            output_path=output_path,
            backend=backend,
            verbose=not args.quiet,
            dry_run=args.dry_run,
            verbose_prompt=args.verbose_prompt,
        )
        progress.update(task, description="[green]Done[/green]")

    if not args.quiet:
        suffix = " [yellow](dry-run — no LLM called, memory not updated)[/yellow]" if args.dry_run else ""
        console.print(f"\n[green][agent] Done.[/green] Output written to [cyan]{output_path}[/cyan]{suffix}")

    # Auto-export if requested
    if args.export:
        _export(output_path, args.export, quiet=args.quiet)


def _watch(args: argparse.Namespace) -> None:
    """Watch plan.md for changes and re-run the agent automatically on each save."""
    plan_path = Path(args.plan)
    interval = float(os.getenv("AGENT_WATCH_INTERVAL", "2"))
    last_mtime: float = 0.0

    console.print(f"[yellow][watch][/yellow] Watching [cyan]{plan_path}[/cyan] every {interval}s — Ctrl+C to stop")
    while True:
        try:
            mtime = plan_path.stat().st_mtime if plan_path.exists() else 0.0
            if mtime != last_mtime:
                last_mtime = mtime
                if mtime != 0.0:
                    console.print(f"\n[yellow][watch][/yellow] Change detected — running agent…")
                    _run_once(args)
            time.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow][watch][/yellow] Stopped.")
            break


def _show_history(args: argparse.Namespace) -> None:
    """Display session history from memory.md, optionally in compact table format."""
    from markdown_agent_3_fil.parser import parse_memory
    from markdown_agent_3_fil.history import format_history, format_history_compact

    memory_path = Path(args.memory)
    if not memory_path.exists():
        console.print(f"[bold red][error][/bold red] memory file not found: [cyan]{memory_path}[/cyan]")
        console.print("        Run the agent at least once to create it.")
        sys.exit(1)

    memory = parse_memory(memory_path.read_text(encoding="utf-8"))

    if args.compact:
        if not memory.sessions:
            console.print("[dim](no sessions recorded)[/dim]")
            return
        table = Table(title=f"Session History — {memory_path}", show_lines=False, border_style="dim")
        table.add_column("#", style="dim", justify="right", width=4)
        table.add_column("Timestamp", style="cyan", min_width=26)
        table.add_column("Tasks", justify="right", width=5)
        table.add_column("Goal", style="white", max_width=60)
        for i, s in enumerate(memory.sessions, 1):
            goal_trunc = s.goal[:58] + ("…" if len(s.goal) > 58 else "")
            table.add_row(str(i), s.timestamp, str(len(s.tasks_completed)), goal_trunc)
        console.print(table)
    else:
        n = args.history_n if args.history_n > 0 else 0
        console.print(format_history(memory, max_sessions=n))


def _apply_template(args: argparse.Namespace) -> None:
    """Bootstrap plan.md from a named built-in template."""
    from markdown_agent_3_fil.templates import get_template, list_templates

    plan_path = Path(args.plan)
    name = args.template

    try:
        content = get_template(name)
    except KeyError as exc:
        console.print(f"[bold red][error][/bold red] {exc}")
        console.print(f"\nAvailable templates: [cyan]{', '.join(list_templates())}[/cyan]")
        sys.exit(1)

    if plan_path.exists() and not args.force:
        console.print(f"[bold red][error][/bold red] {plan_path} already exists. Use [cyan]--force[/cyan] to overwrite.")
        sys.exit(1)

    plan_path.write_text(content, encoding="utf-8")
    console.print(f"[green][template][/green] Written template '[cyan]{name}[/cyan]' to [cyan]{plan_path}[/cyan]")
    console.print(f"           Edit the file to fill in the placeholders, then run:")
    console.print(f"           [bold cyan]python run_agent.py[/bold cyan]")


def _list_templates() -> None:
    """Print all available plan templates as a Rich table."""
    import re as _re
    from markdown_agent_3_fil.templates import list_templates, get_template

    table = Table(title="Built-in Plan Templates", border_style="cyan", show_lines=True)
    table.add_column("Template", style="bold cyan", min_width=18)
    table.add_column("Goal", style="white")

    for name in list_templates():
        content = get_template(name)
        m = _re.search(r"## Goal\s*\n(.+)", content)
        hint = m.group(1).strip()[:72] if m else ""
        table.add_row(name, hint)

    console.print(table)
    console.print(f"\nUsage: [bold cyan]python run_agent.py --template <name>[/bold cyan]")


def _export(output_path: Path, fmt: str, quiet: bool = False) -> None:
    """Export output.md to html, json, or plain text format."""
    if not output_path.exists():
        console.print(f"[bold red][error][/bold red] output file not found: [cyan]{output_path}[/cyan]")
        console.print("        Run the agent first to generate output.")
        sys.exit(1)

    output_text = output_path.read_text(encoding="utf-8")
    stem = output_path.stem
    out_dir = output_path.parent

    if fmt == "html":
        from markdown_agent_3_fil.history import export_html
        dest = out_dir / f"{stem}.html"
        dest.write_text(export_html(output_text, title=stem), encoding="utf-8")

    elif fmt == "json":
        bundle = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(output_path),
            "char_count": len(output_text),
            "word_count": len(output_text.split()),
            "line_count": len(output_text.splitlines()),
            "content": output_text,
        }
        dest = out_dir / f"{stem}.json"
        dest.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    elif fmt == "plain":
        from markdown_agent_3_fil.history import export_plain
        dest = out_dir / f"{stem}.txt"
        dest.write_text(export_plain(output_text), encoding="utf-8")

    else:
        console.print(f"[bold red][error][/bold red] Unknown export format '[cyan]{fmt}[/cyan]'. Choose: html, json, plain")
        sys.exit(1)

    if not quiet:
        size = dest.stat().st_size
        console.print(f"[green][export][/green] {fmt.upper()} saved to [cyan]{dest}[/cyan] ({size} bytes)")


def _parse_args() -> argparse.Namespace:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Markdown Agent — edit plan.md and watch the AI execute it",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Version ────────────────────────────────────────────────────────────
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"Markdown Agent {__version__}",
        help="Print version and exit",
    )

    # ── File paths ─────────────────────────────────────────────────────────
    parser.add_argument(
        "--plan",
        default=os.getenv("AGENT_PLAN_FILE", "plan.md"),
        help="Path to plan markdown file (default: plan.md)",
    )
    parser.add_argument(
        "--memory",
        default=os.getenv("AGENT_MEMORY_FILE", "memory.md"),
        help="Path to memory markdown file (default: memory.md)",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("AGENT_OUTPUT_FILE", "output.md"),
        help="Path to output markdown file (default: output.md)",
    )

    # ── Backend ────────────────────────────────────────────────────────────
    parser.add_argument(
        "--backend",
        choices=["auto", "mock", "anthropic", "openai", "llama", "dry-run"],
        default=os.getenv("AGENT_BACKEND", "auto"),
        help="LLM backend to use (default: auto-detect)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=int(os.getenv("AGENT_MAX_RETRIES", "2")),
        metavar="N",
        help="Number of retries on LLM failure (default: 2)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=float(os.getenv("AGENT_RETRY_DELAY", "1.0")),
        metavar="SECS",
        help="Delay between retries in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--fallback-to-mock",
        action="store_true",
        default=os.getenv("AGENT_FALLBACK_TO_MOCK", "false").lower() in ("1", "true", "yes"),
        help="Fall back to mock output if LLM fails after all retries",
    )

    # ── Run modes ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--watch",
        action="store_true",
        default=False,
        help="Watch plan.md for changes and re-run automatically",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would execute without calling the LLM",
    )
    parser.add_argument(
        "--verbose-prompt",
        action="store_true",
        default=os.getenv("AGENT_VERBOSE_PROMPT", "false").lower() in ("1", "true", "yes"),
        help="Print the full LLM prompt before generating",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        help="Suppress informational output",
    )

    # ── History ────────────────────────────────────────────────────────────
    parser.add_argument(
        "--history",
        action="store_true",
        default=False,
        help="View session history from memory.md",
    )
    parser.add_argument(
        "--history-n",
        type=int,
        default=0,
        metavar="N",
        help="Show only the last N sessions (default: all)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="Show history in compact one-line format (use with --history)",
    )

    # ── Templates ──────────────────────────────────────────────────────────
    parser.add_argument(
        "--template",
        default=None,
        metavar="NAME",
        help="Bootstrap plan.md from a built-in template",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        default=False,
        help="List all available plan templates",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing plan.md when using --template",
    )

    # ── Export ─────────────────────────────────────────────────────────────
    parser.add_argument(
        "--export",
        choices=["html", "json", "plain"],
        default=None,
        metavar="FORMAT",
        help="Export output.md after running: html, json, or plain",
    )

    return parser.parse_args()


def main() -> None:
    """Entry point: parse args, show banner, and dispatch to the appropriate sub-command."""
    args = _parse_args()  # --version action exits here before the banner
    _banner()

    # Dispatch sub-commands first (they don't run the agent)
    if args.list_templates:
        _list_templates()
        return

    if args.history:
        _show_history(args)
        return

    if args.template:
        _apply_template(args)
        return

    # Run / watch
    if args.watch:
        _watch(args)
    else:
        _run_once(args)


if __name__ == "__main__":
    main()
