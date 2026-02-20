"""CLI commands: generate, list, update, summary."""

from __future__ import annotations

from datetime import date, timedelta

import typer

from storage import (
    get_base_dir,
    path_for_date,
    read_daily_md,
    replace_tasks_section,
    replace_summary_section,
    serialize_tasks_to_section,
    write_daily_md,
    parse_tasks_from_markdown,
    Task,
    TASK_SECTION_HEADER,
    SUMMARY_SECTION_HEADER,
    CHECK_ABANDONED,
    CHECK_DONE,
    CHECK_PENDING,
)
from llm import (
    generate_today_tasks,
    parse_update_intent,
    summarize_daily,
    summarize_weekly,
)


def _parse_date(s: str) -> date:
  return date.fromisoformat(s)


def cmd_generate(
    date_str: str | None = typer.Option(None,
                                        "--date",
                                        "-d",
                                        help="日期 YYYY-MM-DD，默认今天"),
) -> None:
  """根据昨天未完成事项生成今天的任务列表；首次无历史任务时不自动添加任务。"""
  base = get_base_dir()
  today = date.fromisoformat(date_str) if date_str else date.today()
  yesterday = today - timedelta(days=1)
  yesterday_md = read_daily_md(base, yesterday)
  yesterday_tasks = parse_tasks_from_markdown(yesterday_md)
  yesterday_pending = [t.title for t in yesterday_tasks if t.is_pending]
  today_iso = today.isoformat()

  # 首次生成：昨天没有未完成任务时，只创建空任务区，不调用 LLM
  if not yesterday_pending:
    empty_section = f"{TASK_SECTION_HEADER}\n\n"
    existing = read_daily_md(base, today)
    if not existing.strip():
      full = f"# {today_iso}\n\n{empty_section}"
    else:
      full = replace_tasks_section(existing, empty_section)
    write_daily_md(base, today, full)
    typer.echo(
        f"已创建 {today_iso} 的日程文件（无历史任务，未添加任务）。{path_for_date(base, today)}")
    return

  tasks_md = generate_today_tasks(yesterday_pending, today_iso)
  if TASK_SECTION_HEADER not in tasks_md:
    tasks_md = f"{TASK_SECTION_HEADER}\n\n" + tasks_md
  existing = read_daily_md(base, today)
  if not existing.strip():
    full = f"# {today_iso}\n\n{tasks_md}\n"
  else:
    full = replace_tasks_section(existing, tasks_md)
  write_daily_md(base, today, full)
  typer.echo(f"已生成 {today_iso} 的日程并写入 {path_for_date(base, today)}")


def cmd_list(
    date_str: str | None = typer.Option(None,
                                        "--date",
                                        "-d",
                                        help="日期 YYYY-MM-DD，默认今天"),
) -> None:
  """查看指定日期的任务列表与状态。"""
  base = get_base_dir()
  d = date.fromisoformat(date_str) if date_str else date.today()
  content = read_daily_md(base, d)
  tasks = parse_tasks_from_markdown(content)
  if not tasks:
    typer.echo(f"{d.isoformat()} 暂无任务，或文件不存在。")
    return
  status_char = {CHECK_PENDING: "○", CHECK_DONE: "✓", CHECK_ABANDONED: "~"}
  for t in tasks:
    sc = status_char.get(t.status, "?")
    typer.echo(f"  {t.index}. [{sc}] {t.title}")


def cmd_update(
    message: str = typer.Argument(..., help="自然语言描述要做的更新，如：完成第1项、新增写周报、废弃第3项"),
    date_str: str | None = typer.Option(None,
                                        "--date",
                                        "-d",
                                        help="日期 YYYY-MM-DD，默认今天"),
) -> None:
  """根据自然语言更新当日任务（完成/新增/废弃/改描述）。"""
  base = get_base_dir()
  d = date.fromisoformat(date_str) if date_str else date.today()
  content = read_daily_md(base, d)
  tasks = parse_tasks_from_markdown(content)
  # 无任务时仍可「新增」；无文件时用当日标题创建
  if not content.strip():
    content = f"# {d.isoformat()}\n\n{TASK_SECTION_HEADER}\n\n"
  from storage import get_task_section_only
  section_only = get_task_section_only(content)
  edits = parse_update_intent(section_only, message)
  # Apply completed_indices
  completed = set(edits.get("completed_indices") or [])
  for t in tasks:
    if t.index in completed:
      t.status = CHECK_DONE
  # Apply abandoned_indices
  abandoned = set(edits.get("abandoned_indices") or [])
  for t in tasks:
    if t.index in abandoned:
      t.status = CHECK_ABANDONED
  # Apply text_edits
  text_edits = {
      e["index"]: e["new_title"]
      for e in edits.get("text_edits") or []
      if "index" in e and "new_title" in e
  }
  for t in tasks:
    if t.index in text_edits:
      t.title = text_edits[t.index]
  # Apply new_tasks (append as pending)
  new_titles = edits.get("new_tasks") or []
  max_idx = max(t.index for t in tasks) if tasks else 0
  for i, title in enumerate(new_titles):
    tasks.append(
        Task(index=max_idx + 1 + i,
             title=title,
             status=CHECK_PENDING,
             raw_line=""))
  new_section = serialize_tasks_to_section(tasks)
  new_content = replace_tasks_section(content, new_section)
  write_daily_md(base, d, new_content)
  typer.echo("已按你的描述更新任务列表。")


def cmd_summary(
    kind: str = typer.Argument("daily", help="daily 或 weekly"),
    date_str: str | None = typer.Option(
        None, "--date", "-d", help="日期 YYYY-MM-DD，默认今天；weekly 时表示结束日"),
) -> None:
  """日总结：写入当日 md 的「日总结」区并输出；周总结：对过去 7 天做汇总。"""
  base = get_base_dir()
  end_date = date.fromisoformat(date_str) if date_str else date.today()
  if kind == "daily":
    content = read_daily_md(base, end_date)
    summary = summarize_daily(content, end_date.isoformat())
    if content.strip():
      new_content = replace_summary_section(content, summary)
    else:
      new_content = f"# {end_date.isoformat()}\n\n{TASK_SECTION_HEADER}\n\n\n{SUMMARY_SECTION_HEADER}\n\n{summary}"
    write_daily_md(base, end_date, new_content)
    typer.echo("已写入当日文档的「日总结」区。")
    typer.echo(summary)
  elif kind == "weekly":
    mds: list[tuple[str, str]] = []
    for i in range(6, -1, -1):
      d = end_date - timedelta(days=i)
      c = read_daily_md(base, d)
      mds.append((d.isoformat(), c))
    summary = summarize_weekly(mds)
    typer.echo(summary)
  else:
    typer.echo("请使用 daily 或 weekly。", err=True)
    raise typer.Exit(1)
