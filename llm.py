"""LLM layer: OpenAI-compatible client and prompts for generate / update / summary."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


def _client() -> OpenAI:
  api_key = os.environ.get("OPENAI_API_KEY", "").strip()
  base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
  if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")
  return OpenAI(api_key=api_key, base_url=base_url)


def _model() -> str:
  return os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def call_system_user(system: str, user: str) -> str:
  """Single chat completion; returns assistant message content."""
  client = _client()
  resp = client.chat.completions.create(
      model=_model(),
      messages=[
          {
              "role": "system",
              "content": system
          },
          {
              "role": "user",
              "content": user
          },
      ],
  )
  msg = resp.choices[0].message
  return (msg.content or "").strip()


def generate_today_tasks(yesterday_pending_titles: list[str], today_iso: str) -> str:
    """
    根据昨天未完成的事项生成今天的任务区段。
    昨天未完成的事项必须全部迁移到当天；不随意添加新任务。
    """
    system = """你是每日日程助手。根据「昨天」未完成的事项，生成「今天」的任务列表。
要求：
1. 昨天未完成的事项必须全部迁移到今天，每行格式：- [ ] 任务描述
2. 只输出 Markdown：必须有 "## 任务" 标题，下面每行 - [ ]，不要代码块或多余说明
3. 不要添加列表以外的其他任务"""
    pending_list = "\n".join(f"- {t}" for t in yesterday_pending_titles) if yesterday_pending_titles else "（无）"
    user = f"今天日期：{today_iso}\n\n昨天未完成的事项（须全部迁移到今天）：\n{pending_list}"
    return call_system_user(system, user)


# --- Update intent (structured JSON) ---


def parse_update_intent(today_md: str, user_message: str) -> dict[str, Any]:
  """
    Parse user's natural language into structured edits.
    Returns JSON with: completed_indices (1-based), new_tasks (list of title str),
    abandoned_indices (1-based), optional text_edits (list of {index, new_title}).
    """
  system = """你是一个任务列表解析助手。用户会给出当前日的任务列表（Markdown）和一句自然语言。
请理解用户意图，并输出一个 JSON 对象，且只输出该 JSON，不要用 markdown 代码块包裹。
字段说明：
- completed_indices: 用户要求「完成」的任务的序号列表（从 1 开始），如 [1, 3]
- abandoned_indices: 用户要求「废弃」的任务的序号列表，如 [2]
- new_tasks: 用户要求「新增」的任务描述列表，如 ["写周报", "开会"]
- text_edits: 用户要求「修改」某任务描述时的列表，每项 { "index": 1, "new_title": "新描述" }
若某项没有则填空列表 [] 或省略该字段。"""
  user = f"当前任务列表（Markdown）：\n\n{today_md}\n\n用户说：{user_message}"
  raw = call_system_user(system, user)
  # Strip possible markdown code fence
  if raw.startswith("```"):
    lines = raw.split("\n")
    if lines[0].startswith("```"):
      lines = lines[1:]
    if lines and lines[-1].strip() == "```":
      lines = lines[:-1]
    raw = "\n".join(lines)
  try:
    return json.loads(raw)
  except json.JSONDecodeError:
    return {
        "completed_indices": [],
        "abandoned_indices": [],
        "new_tasks": [],
        "text_edits": [],
    }


def summarize_daily(md: str, date_iso: str) -> str:
  """生成真实、简要的日总结，适合写入当日文档。"""
  system = "你是日程总结助手。根据当日日程 Markdown 写一句真实、简要的日总结（一两句话），只写事实与进展，不要空话。只输出总结正文，不要标题。"
  user = f"日期：{date_iso}\n\n内容：\n\n{md or '（无内容）'}"
  return call_system_user(system, user)


def summarize_weekly(mds: list[tuple[str, str]]) -> str:
  """Summarize multiple (date_iso, content) into one weekly summary in Chinese."""
  parts = "\n\n---\n\n".join(f"## {d}\n\n{c}" for d, c in mds)
  system = "你是一个周报总结助手。下面是一周内几天的日程内容，请用简短中文做一周汇总总结，突出完成情况与重点。只输出总结正文。"
  user = "一周日程：\n\n" + parts
  return call_system_user(system, user)
