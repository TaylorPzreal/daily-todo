"""Daily TODO CLI entrypoint."""

from dotenv import load_dotenv

load_dotenv()  # 本地测试时从 .env 加载环境变量，生产环境无 .env 则无影响

import typer

from cli import cmd_generate, cmd_list, cmd_update, cmd_summary

app = typer.Typer(
    name="daily-todo",
    help="Daily TODO CLI：基于 LLM 的日程管理，包括生成/更新/总结",
)

app.command("generate", help="根据昨天生成今天的任务列表")(cmd_generate)
app.command("list", help="查看某日任务列表与状态")(cmd_list)
app.command("update", help="用自然语言更新当日任务")(cmd_update)
app.command("summary", help="日总结或周总结")(cmd_summary)

if __name__ == "__main__":
  app()
