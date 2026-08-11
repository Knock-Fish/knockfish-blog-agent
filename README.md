# knockfish-blog-agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-1C3C3C)
![LangChain](https://img.shields.io/badge/LangChain-latest-1C3C3C)
![License](https://img.shields.io/badge/license-MIT-blue)

## 相关项目

| 项目 | 说明 |
| --- | --- |
| [knockfish-blog-backend](https://github.com/Knock-Fish/knockfish-blog-backend) | Spring Boot 后端服务 |
| [knockfish-blog-frontend](https://github.com/Knock-Fish/knockfish-blog-frontend) | Vue 3 前台展示端 |
| [knockfish-blog-admin](https://github.com/Knock-Fish/knockfish-blog-admin) | Vue 3 后台管理端 |
| **knockfish-blog-agent** | **FastAPI + LangGraph AI Agent（当前仓库）** |

KnockFish 博客系统的 AI Agent 服务，基于 LangGraph + FastAPI 构建，通过调用后端 Agent 接口实现博客内容检索与问答。

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 框架 | FastAPI + Uvicorn |
| 语言 | Python 3.12 |
| Agent 编排 | LangGraph（StateGraph + AsyncSqliteSaver 检查点） |
| LLM 接入 | LangChain（兼容 OpenAI 协议，默认接入通义千问 qwen3.8-max） |
| HTTP 客户端 | httpx（异步） |
| 配置管理 | Pydantic Settings（自动读取 .env） |
| 会话存储 | SQLite（data/graph_memory.db，多轮对话上下文持久化） |

## 工作原理

```
入口(chat_llm) ──► LLM 决策 ──┬── 需要工具 ──► tools 节点 ──► 回到 LLM 循环
                              └── 无需工具 ──► 结束并返回
```

- 通过 LangGraph 编排「LLM 决策 + 工具调用」的 ReAct 循环
- 使用 AsyncSqliteSaver 作为 checkpointer，按 session_id 维度保存多轮对话状态
- 聊天接口以 SSE（Server-Sent Events）方式流式返回 LLM 增量文本
- JWT 通过请求头 `Authorization: Bearer <token>` 透传，注入到工具调用上下文，供其请求后端 Agent 接口鉴权

## 已注册工具

工具统一在 `app/tools/registry.py` 注册，按模块分组：

| 分组 | 工具 |
| --- | --- |
| 文章相关 | search_blog_posts、get_blog_post、get_blog_posts_by_tag、get_all_tags |
| 代码片段相关 | search_code_snippets、get_code_snippets_by_category、get_all_code_categories |
| 笔记相关 | search_notes、get_note |
| 友链 & 站点导航 | get_links、get_site_list |
| 资源 & 基础信息 | get_files_by_reference、get_site_info、get_blogger_info |

所有工具均为异步函数，统一进行异常处理（APIError / 超时 / 连接错误 / 兜底），返回格式化的中文文案结果（带 emoji 标识）。

## 目录结构

```
app/
├── api/
│   └── v1/
│       ├── __init__.py          # 聚合路由（/api/v1 前缀）
│       └── endpoints/
│           ├── chat.py          # /chat 流式聊天接口（SSE）
│           └── health.py       # 健康检查
├── core/
│   ├── config.py                # Settings 全局配置（Pydantic）
│   ├── exceptions.py            # 全局异常处理器
│   └── llm.py                   # LLM 客户端初始化
├── graph/
│   ├── state.py                # AgentState 定义
│   ├── nodes.py                # chat_llm 节点、tools 节点、路由判断
│   └── workflow.py             # StateGraph 构建与编译（含 SQLite 检查点）
├── prompt/
│   ├── role.md                 # 角色设定
│   └── article_agent_system.md # Agent 系统提示
├── tools/
│   ├── registry.py              # 工具注册中心
│   └── springboot_api.py        # 调用后端 Agent 接口的 13 个工具函数
├── utils/
│   ├── http_client.py           # 兼容旧版 HTTP 客户端
│   └── http/
│       ├── client.py            # 异步 HTTP 客户端 + token 上下文
│       └── status.py            # HTTP 状态码映射
└── main.py                     # FastAPI 入口（CORS + 异常处理 + 路由）
data/
└── graph_memory.db              # SQLite 检查点数据库（自动创建）
```

## 快速开始

### 环境要求

- Python 3.12+
- 可访问的后端服务（默认 http://localhost:8081/api/agent）

### 配置

编辑 `.env` 文件：

```
APP_NAME="鱼博客Agent"
APP_HOST=0.0.0.0
APP_PORT=8000

# LLM 配置
LLM_API_KEY="<你的 API Key>"
LLM_BASE_URL="<兼容 OpenAI 协议的接口地址>"
LLM_MODEL_ID="qwen3.8-max"
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=60

# 后端 Agent 接口地址
HTTP_BASE_URL="http://localhost:8081/api/agent"
HTTP_TIMEOUT=10
```

### 安装与运行

```sh
# 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 安装依赖
pip install -r requirements.txt

# 启动（支持热重载）
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后：

- 服务端口：8000
- 健康检查：http://localhost:8000/api/v1/health
- 聊天接口：http://localhost:8000/api/v1/chat（POST，SSE 流式响应）

## 接口示例

```sh
curl -N http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{"message": "帮我搜索一下 Spring 相关的文章", "session_id": "test-001"}'
```

响应为 SSE 流，每个数据块格式：`data: {"content": "..."}\n\n`，结束时发送 `data: [DONE]\n\n`。