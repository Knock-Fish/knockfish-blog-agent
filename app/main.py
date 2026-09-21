import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Windows 下 psycopg3 异步连接池不支持默认的 ProactorEventLoop，需切到 SelectorEventLoop
# （asyncpg 两种 loop 都兼容，故此切换对业务表连接同样安全）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import app.graph.workflow as workflow
from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import init_models
from app.core.exception import register_exception_handlers
from app.core.security import AuthMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动预热：幂等建表（memory_items 等新增表），再构建带 PostgreSQL checkpointer 的图
    await init_models()
    await workflow.get_graph()
    yield
    # 关闭时释放 psycopg 连接池
    await workflow.close_pool()


app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)

# CORS 中间件必须位于最外层（先于 AuthMiddleware 注册），
# 否则 OPTIONS 预检请求会先被 AuthMiddleware 透传到路由层、因无 OPTIONS 端点返回 405。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 全局鉴权中间件（secure-by-default）：默认拦截所有请求，仅 AUTH_WHITELIST 放行
app.add_middleware(AuthMiddleware)
# 注册聚合路由
app.include_router(api_router)

# -------- 本地调试入口 --------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app")
