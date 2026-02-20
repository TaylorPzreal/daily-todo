"""Storage layer: resolve paths, read/write daily Markdown, parse/serialize task lists."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


# Status: [ ] = pending, [x] = done, [~] = abandoned
CHECK_PENDING = " "
CHECK_DONE = "x"
CHECK_ABANDONED = "~"

TASK_SECTION_HEADER = "## 任务"
ABANDONED_SECTION_HEADER = "## 已废弃"
SUMMARY_SECTION_HEADER = "## 日总结"


def get_base_dir() -> Path:
    """Return DAILY_TODO_DIR or default ./daily-todo under cwd."""
    raw = os.environ.get("DAILY_TODO_DIR", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.cwd() / "daily-todo"


def path_for_date(base_dir: Path, d: date) -> Path:
    """Path to YYYY-MM-DD.md under base_dir."""
    return base_dir / f"{d.isoformat()}.md"


def ensure_dir(p: Path) -> None:
    """Create parent directories if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Task:
    """Single task with 1-based index for display/edits."""

    index: int
    title: str
    status: str  # " ", "x", "~"
    raw_line: str  # original line for minimal-diff writes

    @property
    def is_pending(self) -> bool:
        return self.status == CHECK_PENDING

    @property
    def is_done(self) -> bool:
        return self.status == CHECK_DONE

    @property
    def is_abandoned(self) -> bool:
        return self.status == CHECK_ABANDONED

    def to_markdown(self) -> str:
        return f"- [{self.status}] {self.title}"


# Match: - [ ] xxx, - [x] xxx, - [~] xxx (optional leading whitespace)
_TASK_LINE = re.compile(r"^\s*-\s*\[([ x~])\]\s*(.*)$", re.IGNORECASE)


def _parse_task_line(line: str, index: int) -> Task | None:
    m = _TASK_LINE.match(line.strip())
    if not m:
        return None
    status = m.group(1).lower()
    if status == "x":
        status = CHECK_DONE
    elif status == "~":
        status = CHECK_ABANDONED
    else:
        status = CHECK_PENDING
    title = m.group(2).strip()
    return Task(index=index, title=title, status=status, raw_line=line.rstrip())


def parse_tasks_from_markdown(content: str) -> list[Task]:
    """
    Parse ## 任务 and ## 已废弃 sections into a single list of Task.
    Tasks in 已废弃 get status CHECK_ABANDONED.
    """
    tasks: list[Task] = []
    in_tasks = False
    in_abandoned = False
    index = 0

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == TASK_SECTION_HEADER:
            in_tasks = True
            in_abandoned = False
            continue
        if stripped == ABANDONED_SECTION_HEADER:
            in_abandoned = True
            in_tasks = False
            continue
        if stripped.startswith("## "):
            in_tasks = False
            in_abandoned = False
            continue

        if in_tasks or in_abandoned:
            t = _parse_task_line(line, index + 1)
            if t:
                index += 1
                if in_abandoned:
                    t = Task(index=t.index, title=t.title, status=CHECK_ABANDONED, raw_line=t.raw_line)
                tasks.append(t)

    return tasks


def serialize_tasks_to_section(tasks: list[Task]) -> str:
    """Produce ## 任务 and optionally ## 已废弃 markdown. Pending/done in 任务, abandoned in 已废弃."""
    main = [t for t in tasks if not t.is_abandoned]
    abandoned = [t for t in tasks if t.is_abandoned]

    lines = [TASK_SECTION_HEADER, ""]
    for t in main:
        lines.append(t.to_markdown())
    if abandoned:
        lines.append("")
        lines.append(ABANDONED_SECTION_HEADER)
        lines.append("")
        for t in abandoned:
            lines.append(t.to_markdown())
    return "\n".join(lines)


def read_daily_md(base_dir: Path, d: date) -> str:
    """Read full content of YYYY-MM-DD.md; return empty string if missing."""
    p = path_for_date(base_dir, d)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def write_daily_md(base_dir: Path, d: date, content: str) -> None:
    """Write full content to YYYY-MM-DD.md, creating dirs if needed."""
    p = path_for_date(base_dir, d)
    ensure_dir(p)
    p.write_text(content, encoding="utf-8")


def replace_tasks_section(content: str, new_tasks_section: str) -> str:
    """
    Replace ## 任务 (and ## 已废弃 if present) in content with new_tasks_section.
    If ## 任务 is missing, append it after the first heading or at start.
    """
    out: list[str] = []
    replaced = False
    i = 0
    lines = content.splitlines()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped == TASK_SECTION_HEADER:
            out.append(new_tasks_section)
            replaced = True
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("## "):
                i += 1
            continue
        if stripped == ABANDONED_SECTION_HEADER:
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("## "):
                i += 1
            continue
        out.append(line)
        i += 1

    if not replaced:
        if out and out[-1].strip() != "":
            out.append("")
        out.append(new_tasks_section)
    return "\n".join(out)


def get_task_section_only(content: str) -> str:
    """Extract only ## 任务 and ## 已废弃 (and their items) for LLM input."""
    lines = content.splitlines()
    result: list[str] = []
    in_section = False
    for line in lines:
        s = line.strip()
        if s == TASK_SECTION_HEADER or s == ABANDONED_SECTION_HEADER:
            in_section = True
            result.append(line)
            continue
        if in_section:
            if s.startswith("## "):
                in_section = False
            else:
                result.append(line)
    return "\n".join(result) if result else ""


def replace_summary_section(content: str, summary_text: str) -> str:
    """
    Replace ## 日总结 section with new content, or append it after ## 任务 / at end if missing.
    """
    lines = content.splitlines()
    out: list[str] = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped == SUMMARY_SECTION_HEADER:
            out.append(SUMMARY_SECTION_HEADER)
            out.append("")
            out.append(summary_text.strip())
            replaced = True
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("## "):
                i += 1
            continue
        out.append(line)
        i += 1
    if not replaced:
        if out and out[-1].strip() != "":
            out.append("")
        out.append(SUMMARY_SECTION_HEADER)
        out.append("")
        out.append(summary_text.strip())
    return "\n".join(out)
