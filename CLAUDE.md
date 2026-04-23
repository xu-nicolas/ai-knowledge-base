# AI Knowledge Base

自动从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent/RAG/ML/MLOps 领域的技术动态，经 MiniMax 大模型分析后结构化存储为 JSON，支持按需分发到 Telegram/飞书（本地存完整数据，分发渠道推简报摘要）。

## 技术栈

| 类别 | 选型 |
|---|---|
| 语言 | Python 3.12 |
| 开发工具 | Claude Code |
| Agent 框架 | LangGraph |
| LLM | MiniMax（OpenAI 兼容接口） |
| 未来兼容 | OpenClaw |

## 编码规范

- **PEP 8** 风格，snake_case 命名
- **Google 风格 docstring**，所有公开函数/类必须有文档
- **禁止裸 `print()`**，统一使用 `logging` 模块（级别：DEBUG 以上输出到控制台）
- **类型注解**：所有函数签名必须包含类型提示
- **import 分组**：标准库 → 第三方库 → 本地模块，组间空一行

## 项目结构

```
ai-knowledge-base/
├── CLAUDE.md
├── pyproject.toml
├── .env                       # MiniMax API key 等（不提交 git）
├── knowledge/
│   ├── raw/                   # 原始爬取数据
│   │   └── 2026-04-23/
│   │       ├── github_trending.html
│   │       └── hn_results.json
│   └── entries/               # 结构化知识条目 JSON
│       └── 2026-04-23-001.json
├── src/
│   ├── collectors/            # 数据采集（自爬）
│   │   ├── base.py
│   │   ├── github_trending.py
│   │   └── hacker_news.py
│   ├── analyzers/             # AI 分析
│   │   ├── base.py
│   │   └── minimax_analyzer.py
│   ├── distributors/          # 多渠道分发
│   │   ├── base.py
│   │   ├── telegram.py
│   │   └── feishu.py
│   ├── models/                # 数据模型
│   │   └── knowledge_entry.py
│   ├── pipeline.py            # LangGraph 主工作流
│   └── scheduler.py           # 定时任务
└── tests/
```

## 知识条目 JSON Schema

### 必填字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `string` | 格式 `YYYY-MM-DD-NNN`，如 `2026-04-23-001` |
| `title` | `string` | 文章/项目标题 |
| `source` | `enum` | `github_trending` / `hacker_news` |
| `source_url` | `string` | 原文链接 |
| `summary` | `string` | AI 生成的摘要（2-3 句话） |
| `tags` | `list[string]` | 标签，如 `["llm", "agent", "rag"]` |
| `status` | `enum` | `raw` → `analyzed` → `distributed` → `archived` |
| `collected_at` | `string` | ISO 8601 采集时间 |

### 可选字段（放在 `metadata` 对象中）

| 字段 | 类型 | 说明 |
|---|---|---|
| `metadata.published_at` | `string` | 原始内容发布时间 |
| `metadata.analyzed_at` | `string` | AI 分析时间 |
| `metadata.analysis` | `object` | AI 分析详情（技术亮点、适用场景、风险） |
| `metadata.author` | `string` | 原作者/维护者 |
| `metadata.stars` | `int` | GitHub star 数（仅 GitHub 源） |
| `metadata.channel` | `list[string]` | 已分发渠道，如 `["telegram", "feishu"]` |
| `metadata.duplicate_of` | `string` | 去重指向的已有 ID |

### 示例

```json
{
  "id": "2026-04-23-001",
  "title": "LangGraph: Stateful Multi-Agent Workflows",
  "source": "github_trending",
  "source_url": "https://github.com/langchain-ai/langgraph",
  "summary": "LangChain 推出的基于 LangGraph 的状态化多 Agent 工作流框架，支持条件分支、循环和持久化检查点。",
  "tags": ["agent", "langgraph", "workflow"],
  "status": "analyzed",
  "collected_at": "2026-04-23T09:00:00Z",
  "metadata": {
    "published_at": "2026-04-22",
    "analyzed_at": "2026-04-23T09:05:00Z",
    "analysis": {
      "highlights": ["条件分支", "检查点持久化"],
      "use_cases": ["多 Agent 编排", "复杂任务分解"],
      "risks": ["尚处早期，API 可能变动"]
    },
    "author": "langchain-ai",
    "stars": 12500
  }
}
```

## Agent 角色概览

| 角色 | 文件 | 职责 |
|---|---|---|
| **Collector（采集）** | `src/collectors/*.py` | 自爬 GitHub Trending 和 Hacker News，过滤 AI 相关内容（排除 crypto/web3），原始数据存入 `knowledge/raw/` |
| **Analyzer（分析）** | `src/analyzers/minimax_analyzer.py` | 调用 MiniMax 大模型对原始条目生成摘要、标签、技术分析，输出结构化 JSON |
| **Distributor（整理）** | `src/distributors/*.py` | 从 `knowledge/entries/` 读取完整 JSON，按渠道格式生成简报，推送到 Telegram/飞书 |

## 工作流（LangGraph Pipeline）

```
raw (每日定时触发)
  ↓
Collector → 自爬 + 过滤 + 去重（基于 source_url）
  ↓
Analyzer → MiniMax 分析 → 写入 entries/
  ↓
Distributor → 可选触发 → 渠道简报
  ↓
archived
```

## 错误处理

- **网络请求**：最多重试 3 次，指数退避（1s → 2s → 4s）
- **解析失败**：记录原始 HTML 到 `knowledge/raw/` 下的 `.error` 文件，状态标记为 `parse_failed`，不阻断整个流程
- **AI 分析失败**：保持 `status: raw`，下次采集周期重试
- **去重**：基于 `source_url` 做唯一判断，已存在的跳过

## 分发策略

- **本地**：始终保存完整 JSON 数据到 `knowledge/entries/`
- **渠道推送**：按需触发，各渠道仅推送简报摘要（标题 + 一句话摘要 + 链接），不推送完整分析

## 红线（绝对禁止）

- **禁止提交 `.env`、API key、任何密钥到 git**
- **禁止裸 `print()`**，必须用 `logging`
- **禁止修改已归档（`archived`）的 JSON 条目**
- **禁止在 `knowledge/` 目录存放可执行代码**（仅限数据文件）
- **禁止提交 `__pycache__/`、`.pyc`、虚拟环境目录到 git**
