"""异常体系 + FastAPI 全局异常处理器

分层异常：
- FishAgentsException：项目基础异常（不直接抛出）
  |- AppException：可向用户呈现、附带 HTTP 状态码的业务异常
  |- LLMException / AgentException / ToolException / ConfigException
     （供内部捕获，最终会映射为 AppException 或 500）

全局处理器通过 register_exception_handlers(app) 挂载到 FastAPI。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


# -------- 基础异常 --------
class FishAgentsException(Exception):
    """项目基础异常类"""


class AppException(FishAgentsException):
    """可安全对外暴露的业务异常

    被全局处理器捕获后会返回：
    {"code": status_code, "message": message, "data": extra}
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


class ConfigException(FishAgentsException):
    """配置相关异常"""


class LLMException(FishAgentsException):
    """LLM 调用相关异常"""


class AgentException(FishAgentsException):
    """Agent 编排相关异常"""


class ToolException(FishAgentsException):
    """工具执行相关异常"""


# -------- 全局响应构造 --------
def _error_body(status_code: int, message: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"code": status_code, "message": message}
    if extra:
        body["data"] = extra
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """将全局异常处理器挂载到 FastAPI 应用上"""

    @app.exception_handler(AppException)
    async def _app_exception(_req: Request, exc: AppException) -> JSONResponse:
        logger.warning("AppException: %s (status=%s)", exc.message, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.status_code, exc.message, exc.extra),
        )

    @app.exception_handler(ValidationError)
    async def _validation_error(_req: Request, exc: ValidationError) -> JSONResponse:
        # Pydantic 运行时校验错误（非请求参数校验，那个 FastAPI 自己处理）
        logger.warning("ValidationError: %s", exc)
        return JSONResponse(
            status_code=422,
            content=_error_body(422, "请求数据校验失败", {"details": exc.errors()}),
        )

    @app.exception_handler(FishAgentsException)
    async def _fish_exception(_req: Request, exc: FishAgentsException) -> JSONResponse:
        # 内部异常：不直接暴露细节，统一打日志后返回 500
        logger.exception("Unhandled FishAgentsException")
        return JSONResponse(
            status_code=500,
            content=_error_body(500, "服务内部错误，请稍后重试"),
        )

    @app.exception_handler(Exception)
    async def _unexpected(_req: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content=_error_body(500, "服务内部错误，请稍后重试"),
        )
