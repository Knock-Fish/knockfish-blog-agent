# knockfish-blog-agent

![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-latest-1C3C3C)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1)
![License](https://img.shields.io/badge/license-MIT-blue)

## 相关项目

| 项目 | 说明 |
| --- | --- |
| [knockfish-blog-backend](https://github.com/Knock-Fish/knockfish-blog-backend) | Spring Boot 后端服务 |
| [knockfish-blog-frontend](https://github.com/Knock-Fish/knockfish-blog-frontend) | Vue 3 前台展示端 |
| [knockfish-blog-admin](https://github.com/Knock-Fish/knockfish-blog-admin) | Vue 3 后台管理端 |
| **knockfish-blog-agent** | **FastAPI + LangGraph AI Agent（当前仓库）** |

KnockFish 博客系统的 AI Agent 服务，基于 LangGraph + FastAPI 构建。除了通过工具调用后端接口完成博客内容检索与问答外，还具备**长期记忆**能力：自动沉淀用户画像与偏好，并在后续对话中注入系统提示词，实现个性化回答。

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 框架 | FastAPI + Uvicorn |
| 语言 | Python 3.12 |
| Agent 编排 | LangGraph（StateGraph + AsyncPostgresSaver 检查点） |
| LLM 接入 | LangChain-OpenAI（兼容 OpenAI 协议） |
| HTTP 客户端 | aiohttp（异步） |
| 配置管理 | Pydantic Settings（自动读取 `.env`） |
| 数据库 | PostgreSQL（业务表 SQLAlchemy async + LangGraph 检查点共用） |
| 鉴权 | PyJWT RS256 公钥验签 + 全局鉴权中间件 |

## 工作原理

```
请求 ──► AuthMiddleware(RS256 验签)
         └─► 路由 ──► 回忆长期记忆 ──► 注入系统提示词
                        └─► LangGraph: LLM 决策 ──┬── 需要工具 ──► tools 节点 ──► 回到 LLM 循环
                                                  └── 无需工具 ──► 结束
                             └─► 消息落库 ──► SSE 流式返回
```

- **ReAct 循环**：通过 LangGraph 编排「LLM 决策 + 工具调用」，递归上限 25 步防死循环
- **PostgreSQL 检查点**：`AsyncPostgresSaver` 按 `thread_id` 维度持久化多轮对话状态
- **长期记忆**：`remember_user_fact` 在对话中抽取用户事实写入 `memory_items`，下次对话自动 `recall_user_profile` 并注入系统提示词占位符
- **SSE 流式**：`/chat/stream` 以 `text/event-stream` 逐 token 推送增量文本
- **安全设计**：Spring Boot 持私钥签发 JWT，Agent 只持公钥验签，即使 Agent 被攻破也无法伪造 token；`AuthMiddleware` 为 secure-by-default，默认拦截全部请求，仅 `/health`、`/redoc`、`/openapi.json` 放行

## 已注册工具

工具统一在 `app/tools/registry.py` 注册，共 16 个：

| 分组 | 工具 |
| --- | --- |
| 文章检索 | `search_articles`、`get_blog_post`、`get_blog_posts_by_tag`、`get_all_tags` |
| 笔记检索 | `search_notes`、`get_note` |
| 代码片段 | `search_code_snippets` |
| 站点信息 | `get_site_info`、`get_blogger_info` |
| 时间计算 | `get_current_time`、`convert_timezone`、`calculate_time_difference`、`countdown`、`parse_date` |
| 长期记忆 | `remember_user_fact`、`recall_user_profile` |

新增工具需在 `registry.py` 中导入并加入 `tools` 列表，否则 Agent 无法感知。

## 目录结构

```
app/
├── api/v1/
│   ├── __init__.py                 # 聚合路由（/api/v1 前缀）
│   └── endpoints/
│       ├── chat.py                # /chat（非流式）、/chat/stream（SSE）
│       ├── health.py              # /health 健康检查（鉴权白名单）
│       └── memory.py              # /threads 会话新建与列表
├── certs/
│   └── jwt_public_key.pem         # RS256 公钥（私钥由 Spring Boot 持有）
├── core/
│   ├── config.py                  # Settings 全局配置（Pydantic Settings）
│   ├── db.py                      # SQLAlchemy 异步引擎与会话工厂
│   ├── exception.py               # 统一异常与错误响应信封
│   ├── llm.py                     # ChatOpenAI 客户端单例
│   ├── request_context.py         # user_id / token 上下文变量
│   └── security.py                # JWT 验签 + AuthMiddleware
├── graph/
│   ├── state.py                   # AgentState 定义
│   ├── nodes.py                   # LLM 节点、工具节点
│   └── workflow.py                # StateGraph 构建（PostgreSQL checkpointer）
├── models/
│   ├── conversation.py            # threads / messages 表
│   └── memory.py                  # memory_items 表（长期记忆）
├── prompts/
│   ├── registry.py                # 提示词模板注册表
│   ├── system_prompt.md           # 主系统提示词
│   └── summary_prompt.md          # 摘要提示词
├── repositories/                  # 数据访问层（thread / message / memory）
├── schemas/                       # 请求响应模型（含 SSE 事件定义）
├── services/
│   ├── chat_service.py            # 对话编排 + SSE 事件生成
│   ├── memory_service.py          # 会话与消息持久化
│   └── long_term_memory_service.py# 长期记忆抽取与回忆
├── tools/
│   ├── registry.py                # 工具注册中心
│   ├── springboot_api.py          # 调用后端 Agent 接口
│   ├── time_tools.py              # 时间计算工具
│   └── memory_tools.py            # 记忆读写工具
├── utils/http/
│   ├── client.py                  # 异步 HTTP 客户端 + token 上下文
│   └── status.py                  # HTTP 状态码映射
└── main.py                        # FastAPI 入口（CORS + 鉴权 + 路由）
tests/                             # pytest 用例（API / 提示词注册表）
```

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 16（业务表与 LangGraph 检查点共用同一库）
- 可访问的 Spring Boot 后端服务

### 配置

在项目根目录创建 `.env`（**该文件已被 `.gitignore` 排除，请勿提交**）：

```ini
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

# 数据库（异步驱动，注意 scheme 用 +asyncpg 或 +psycopg）
DATABASE_URL="postgresql+asyncpg://<用户名>:<密码>@localhost:5432/knockfish"

# JWT（验证 Spring Boot 签发的 token）
JWT_ALGORITHM="RS256"
JWT_ISSUER=""
```

> **注意**：`DATABASE_URL` 必须带异步驱动前缀（`postgresql+asyncpg://` 或 `postgresql+psycopg://`），裸 `postgresql://` 会导致 SQLAlchemy 异步引擎初始化失败。

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

启动时 `lifespan` 会自动幂等建表（`threads` / `messages` / `memory_items`）并初始化带 PostgreSQL checkpointer 的图。

启动成功后：

- 服务端口：8000
- 健康检查：<http://localhost:8000/api/v1/health>
- 交互式文档：<http://localhost:8000/docs>

### 运行测试

```sh
pytest
```

## 接口

所有接口除白名单外均需在请求头携带 `Authorization: Bearer <jwt>`，用户身份以 token 解析结果为准（覆盖请求体中的 `user_id`，防止越权）。

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | 健康检查 | ❌ 白名单 |
| `POST` | `/api/v1/chat/` | 非流式对话，返回完整结果 | ✅ |
| `POST` | `/api/v1/chat/stream` | SSE 流式对话 | ✅ |
| `POST` | `/api/v1/threads` | 新建会话 | ✅ |
| `GET` | `/api/v1/threads` | 获取会话列表 | ✅ |

### SSE 事件协议

流式接口返回 `text/event-stream`，每帧格式 `data: {...}\n\n`，事件类型：

| type | 字段 | 说明 |
| --- | --- | --- |
| `token` | `content` | 逐 token 增量文本 |
| `done` | `threadId` | 流正常结束，携带本次会话 ID |
| `error` | `message` | 流内捕获的业务错误 |

字段名统一转驼峰输出，与前端 `Api.Agent.*` 类型保持同一 wire format。

### 请求示例

```sh
curl -N http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{"message": "帮我搜索一下 Spring 相关的文章", "thread_id": "<uuid>"}'
```

## 数据模型

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `threads` | 会话 | `thread_id`(uuid)、`user_id`、`title`、`created_at` |
| `messages` | 消息 | `message_id`、`thread_id`、`role`、`content`、`tool_calls`、`tokens` |
| `memory_items` | 长期记忆条目 | `user_id`、`key`、`value`、`category` |

## License

MIT
