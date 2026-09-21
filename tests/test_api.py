"""HTTP 接口契约测试（不连 DB，绕开鉴权）。"""
from fastapi.testclient import TestClient

from app.main import app


def test_openapi_schema_reachable(client: TestClient):
    # 验证 app 装配正常、鉴权已绕过、路由可达
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_health_no_db_dependency(client: TestClient):
    # /api/v1/health 不查库，验证基础可用性
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
