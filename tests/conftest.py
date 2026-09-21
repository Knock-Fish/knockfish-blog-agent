"""共享测试夹具。

只在测试进程的内存中修改 app 单例，**不回写任何 app/ 源码文件**：
1. 关闭 lifespan —— 避免测试时连 PostgreSQL 建表；
2. 移除全局 AuthMiddleware —— 否则每个请求都要真 RS256 token；
3. 用 dependency_overrides 注入固定用户 —— 跳过验签。
"""
import pytest
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import AuthMiddleware, get_current_user


@asynccontextmanager
async def _no_lifespan(app):
    yield


# 1) 关闭 lifespan，不连真实 PG
app.router.lifespan_context = _no_lifespan

# 2) 移除全局鉴权中间件
app.user_middleware = [m for m in app.user_middleware if m.cls is not AuthMiddleware]
app.build_middleware_stack()

# 3) 注入固定用户，跳过 RS256 验签
app.dependency_overrides[get_current_user] = lambda: 1


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
