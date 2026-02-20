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
| `OPENAI_API_KEY`  | **必填**。OpenAI 或兼容 API 的密钥（如 DeepSeek、OpenAI 等）。      |
| `OPENAI_BASE_URL` | 可选。API 地址，例如 `https://api.deepseek.com`。                   |
| `OPENAI_MODEL`    | 可选。模型名，默认 `gpt-4o-mini`。                                  |


## 安装使用

```bash
pip install daily-todo
# 或
uv tool install daily-todo
```

配置 env 到 `.zshrc`，完成后执行一次 `source ~/.zshrc`：

```sh
cat >> ~/.zshrc << 'EOF'

# daily-todo
alias dcli=daily-todo
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export OPENAI_MODEL=qwen2.5:7b-instruct
export DAILY_TODO_DIR="$HOME/.daily-todos"
EOF

source ~/.zshrc
```

```bash
daily-todo --help

# use alias
dcli --help
```

## 命令示例

```bash
# 根据昨天生成今天的任务并写入今日文件（默认今天）
dcli generate
dcli generate --date 2025-02-21

# 查看今日任务列表与状态
dcli list
dcli list --date 2025-02-20

# 用自然语言更新当日任务
dcli update "完成第1项"
dcli update "新增写周报、废弃第3项" --date 2025-02-20

# 日总结（指定日期，默认今天）
dcli summary daily
dcli summary daily --date 2025-02-20

# 周总结（过去 7 天，默认到今天）
dcli summary weekly
dcli summary weekly --date 2025-02-20
```

## 每日文件格式

- 文件名为 `YYYY-MM-DD.md`。
- 建议结构：
  - `# 日期` 或简短标题
  - `## 任务`：每行 `- [ ]` / `- [x]` / `- [~]` 表示未完成 / 已完成 / 已废弃。
  - 可选：`## 进展`、`## 备注` 等自由文本，供 LLM 总结与生成下一日参考。

示例：

```md
# 2026-02-20

## 任务

- [x] 开发CLI
- [ ] 发布到PyPI

## 日总结

今日完成开发任务。
```

## Development

### 本机调试

```bash
cd daily-todo
uv sync

cp env.example .env

uv run python main.py generate   # 或 list / update / summary 等
```

内容参考项目根目录 `env.example`，按需改成本地路径与 API 配置即可。
