# Daily TODO

Daily TODO CLI：在环境变量指定的目录下管理按日期命名的 Markdown 文件，并用 LLM 生成当日计划、理解自然语言更新任务、做日/周总结。

## 功能

1. **管理 Markdown**：在 `DAILY_TODO_DIR` 指定的文件夹下按 `YYYY-MM-DD.md` 管理每日文件。
2. **生成当日日程**：基于「昨天」的 Markdown 内容，用 LLM 生成「今天」的任务列表并写入当日文件。
3. **查看与更新**：查看任务列表与状态；用自然语言更新（完成、新增、废弃、改描述），由 LLM 解析意图并写回文件。
4. **总结**：对单日或过去一周的日程做 LLM 总结。

## 环境变量

| 变量              | 说明                                                                |
| ----------------- | ------------------------------------------------------------------- |
| `DAILY_TODO_DIR`  | 存放每日 Markdown 的目录；未设置时使用当前目录下的 `./daily-todo`。 |
| `OPENAI_API_KEY`  | **必填**。OpenAI 或兼容 API 的密钥（如 DeepSeek、Friday 等）。      |
| `OPENAI_BASE_URL` | 可选。API 地址，例如 `https://api.deepseek.com`。                   |
| `OPENAI_MODEL`    | 可选。模型名，默认 `gpt-4o-mini`。                                  |

### 本地测试：用 .env 加载配置

在项目根目录（与 `main.py` 同级）新建 `.env`，把环境变量写进去即可，启动时会自动加载，无需在 shell 里 export。

```bash
# .env 示例
DAILY_TODO_DIR=/path/to/your/daily-notes
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

## 安装与运行

### 方式一：本机全局命令（推荐，无需发布）

在项目目录下**可编辑安装**，之后在任意目录可用 `daily-todo` 命令：

```bash
cd app-demo/daily-todo
uv sync
uv pip install -e .
```

或使用 pip：

```bash
cd app-demo/daily-todo
pip install -e .
```

安装后可直接使用：

```bash
daily-todo list
daily-todo generate
daily-todo update "新增任务xxx"
```

（依赖当前激活的 Python/venv；若用 `uv run` 进该项目的 venv，需先 `source .venv/bin/activate` 或在该目录下用 `uv run daily-todo ...`。）

### 方式二：不安装，每次用 uv 运行

```bash
cd app-demo/daily-todo
uv sync
uv run python main.py <子命令> [选项]
```

### 发布后（可选）

若将项目发布到 PyPI，他人可：

```bash
pip install daily-todo
# 或
uv tool install daily-todo
```

本仓库未发布也可通过 Git 安装（需在仓库根目录或指定子路径）：

```bash
pip install -e 'git+https://github.com/你的用户名/ai-demo-collection.git#subdirectory=app-demo/daily-todo'
```

## 命令示例

```bash
# 根据昨天生成今天的任务并写入今日文件（默认今天）
uv run python main.py generate
uv run python main.py generate --date 2025-02-21

# 查看今日任务列表与状态
uv run python main.py list
uv run python main.py list --date 2025-02-20

# 用自然语言更新当日任务
uv run python main.py update "完成第1项"
uv run python main.py update "新增写周报、废弃第3项" --date 2025-02-20

# 日总结（指定日期，默认今天）
uv run python main.py summary daily
uv run python main.py summary daily --date 2025-02-20

# 周总结（过去 7 天，默认到今天）
uv run python main.py summary weekly
uv run python main.py summary weekly --date 2025-02-20
```

## 每日文件格式

- 文件名为 `YYYY-MM-DD.md`。
- 建议结构：
  - `# 日期` 或简短标题
  - `## 任务`：每行 `- [ ]` / `- [x]` / `- [~]` 表示未完成 / 已完成 / 已废弃。
  - 可选：`## 进展`、`## 备注` 等自由文本，供 LLM 总结与生成下一日参考。
