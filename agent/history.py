"""History display and export helpers for memory.md sessions."""

from __future__ import annotations

from .parser import Memory


def format_history(memory: Memory, max_sessions: int = 0) -> str:
    """Return a formatted Markdown string of session history.

    Args:
        memory: Parsed Memory object.
        max_sessions: If >0, show only the last N sessions.
    """
    if not memory.sessions:
        return (
            "No sessions recorded yet.\n"
            "Run `python run_agent.py` to create the first session."
        )

    sessions = memory.sessions
    total = len(sessions)
    if max_sessions > 0:
        sessions = sessions[-max_sessions:]
    shown = len(sessions)
    offset = total - shown  # index of first shown session (0-based)

    lines: list[str] = []
    lines.append("# Session History")
    lines.append(f"*{total} session(s) total — showing {shown}*")
    lines.append("")

    for i, session in enumerate(sessions, start=offset + 1):
        lines.append(f"## Session {i} — {session.timestamp}")
        lines.append(f"**Goal:** {session.goal}")
        if session.tasks_completed:
            lines.append(f"**Tasks ({len(session.tasks_completed)}):**")
            for t in session.tasks_completed:
                lines.append(f"  - {t}")
        if session.summary:
            lines.append(f"**Summary:** {session.summary[:300]}")
        lines.append("")

    if memory.state:
        lines.append("## Current State")
        for k, v in memory.state.items():
            lines.append(f"- **{k}**: {v}")

    return "\n".join(lines)


def format_history_compact(memory: Memory) -> str:
    """Return a compact one-line-per-session summary table."""
    if not memory.sessions:
        return "  (no sessions recorded)"
    lines = []
    lines.append(f"  {'#':>3}  {'Timestamp':<26}  {'Tasks':>5}  Goal")
    lines.append(f"  {'─'*3}  {'─'*26}  {'─'*5}  {'─'*40}")
    for i, s in enumerate(memory.sessions, 1):
        tasks_n = len(s.tasks_completed)
        goal_trunc = s.goal[:48] + ("…" if len(s.goal) > 48 else "")
        lines.append(f"  {i:>3}  {s.timestamp:<26}  {tasks_n:>5}  {goal_trunc}")
    return "\n".join(lines)


def export_html(output_text: str, title: str = "Agent Output") -> str:
    """Convert Markdown-like output text to a minimal standalone HTML page."""
    import html as html_lib
    import re

    def md_to_html(text: str) -> str:
        lines_out: list[str] = []
        in_table = False
        in_code = False
        ul_stack: list[str] = []

        for line in text.splitlines():
            # Code blocks
            if line.startswith("```"):
                if in_code:
                    lines_out.append("</code></pre>")
                    in_code = False
                else:
                    lang = line[3:].strip()
                    lines_out.append(f'<pre><code class="language-{lang}">')
                    in_code = True
                continue
            if in_code:
                lines_out.append(html_lib.escape(line))
                continue

            # Headings
            h_m = re.match(r"^(#{1,6})\s+(.*)", line)
            if h_m:
                level = len(h_m.group(1))
                content = _inline_md(h_m.group(2))
                lines_out.append(f"<h{level}>{content}</h{level}>")
                continue

            # Horizontal rules
            if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", line.strip()):
                lines_out.append("<hr>")
                continue

            # Table rows
            if line.strip().startswith("|"):
                if not in_table:
                    lines_out.append("<table>")
                    in_table = True
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                # Skip separator rows like |---|---|
                if all(re.match(r"^[-:]+$", c) for c in cells if c):
                    continue
                row_html = "".join(f"<td>{_inline_md(c)}</td>" for c in cells)
                lines_out.append(f"<tr>{row_html}</tr>")
                continue
            elif in_table:
                lines_out.append("</table>")
                in_table = False

            # List items
            li_m = re.match(r"^(\s*)- \[( |x|X)\] (.*)", line)
            if li_m:
                checked = li_m.group(2).lower() == "x"
                text_content = _inline_md(li_m.group(3))
                icon = "✓" if checked else "○"
                style = "color:#27ae60" if checked else "color:#999"
                lines_out.append(
                    f'<li><span style="{style}">{icon}</span> {text_content}</li>'
                )
                continue
            ul_m = re.match(r"^(\s*)[-*] (.*)", line)
            if ul_m:
                lines_out.append(f"<li>{_inline_md(ul_m.group(2))}</li>")
                continue

            # Blank line → paragraph break
            if not line.strip():
                lines_out.append("<br>")
                continue

            # Plain paragraph line
            lines_out.append(f"<p>{_inline_md(line)}</p>")

        if in_table:
            lines_out.append("</table>")
        return "\n".join(lines_out)

    def _inline_md(text: str) -> str:
        """Apply inline Markdown: bold, italic, code, strikethrough."""
        text = html_lib.escape(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
        return text

    body = md_to_html(output_text)
    safe_title = html_lib.escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           max-width: 860px; margin: 40px auto; padding: 0 20px;
           line-height: 1.6; color: #333; }}
    h1 {{ border-bottom: 2px solid #eee; padding-bottom: 8px; }}
    h2 {{ border-bottom: 1px solid #eee; padding-bottom: 4px; margin-top: 28px; }}
    code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }}
    pre  {{ background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }}
    pre code {{ background: none; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    td, th {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    hr {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}
    li {{ margin: 4px 0; }}
    em {{ font-style: italic; }}
    del {{ color: #999; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def export_plain(output_text: str) -> str:
    """Strip Markdown decorations and return plain text."""
    import re
    text = output_text
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # Remove inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove strikethrough
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    return text
