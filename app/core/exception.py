"""全局异常处理

提供：
1. 业务异常基类与常用子类（业务层 raise，由全局 handler 转成统一 JSON）
2. 统一错误响应体 {"code", "msg", "data"}（与 Spring Boot 的 {code,msg,data} 对齐）
3. 各类异常 handler 与注册入口 register_exception_handlers(app)

"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..utils.http.status import HTTPStatus, get_default_error_message

logger = logging.getLogger(__name__)


# 业务异常
class AppException(Exception):
    """业务异常基类

    用法：raise NotFoundException("会话不存在")
    约定：可预期的业务错误用本类，不可预期的系统错误让它冒泡到兜底 handler。
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int = HTTPStatus.BAD_REQUEST,
        code: int | None = None,
        data=None,
    ):
        self.message = message or get_default_error_message(status_code)
        self.status_code = status_code
        self.code = code or status_code
        self.data = data
        super().__init__(self.message)


class BadRequestException(AppException):
    """400 请求参数错误"""

    def __init__(self, message: str = "请求参数错误"):
        super().__init__(message=message, status_code=HTTPStatus.BAD_REQUEST)


class UnauthorizedException(AppException):
    """401 未认证"""

    def __init__(self, message: str = "身份验证失败，请重新登录"):
        super().__init__(message=message, status_code=HTTPStatus.UNAUTHORIZED)


class ForbiddenException(AppException):
    """403 无权限"""

    def __init__(self, message: str = "权限不足，无法执行此操作"):
        super().__init__(message=message, status_code=HTTPStatus.FORBIDDEN)


class NotFoundException(AppException):
    """404 资源不存在"""

    def __init__(self, message: str = "请求的资源不存在"):
        super().__init__(message=message, status_code=HTTPStatus.NOT_FOUND)


class ConflictException(AppException):
    """409 资源冲突"""

    def __init__(self, message: str = "资源冲突，请检查后重试"):
        super().__init__(message=message, status_code=HTTPStatus.CONFLICT)


# ------------------------------------------------------------ 统一响应体
def _error_response(
    status_code: int, message: str, code: int | None = None, data=None
) -> JSONResponse:
    """构造统一错误响应：{"code", "msg", "data"}（与成功信封、Spring Boot 格式一致）"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code if code is not None else status_code,
            "msg": message,
            "data": data,
        },
    )


# ---------------------------------------------------------------- handler
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """业务异常：属于预期内错误，warn 级即可"""
    logger.warning("业务异常 path=%s code=%s msg=%s", request.url.path, exc.code, exc.message)
    return _error_response(exc.status_code, exc.message, exc.code, exc.data)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """FastAPI / Starlette 原生 HTTPException（fastapi.HTTPException 是其子类）"""
    logger.warning("HTTP 异常 path=%s status=%s detail=%s",
                   request.url.path, exc.status_code, exc.detail)
    return _error_response(exc.status_code, exc.detail)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic 参数校验失败：默认 422 响应体可读性差，整理成中文提示"""
    errors = exc.errors()
    first = errors[0] if errors else None
    loc = ".".join(str(x) for x in first["loc"] if x != "body") if first else ""
    detail = f"参数 {loc} {first['msg']}" if first else "请求参数校验失败"
    return _error_response(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        f"参数校验失败：{detail}",
        data=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：记录完整栈便于排查，对外只给通用提示，避免泄漏内部细节"""
    logger.exception("未捕获异常 path=%s", request.url.path)
    return _error_response(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        get_default_error_message(HTTPStatus.INTERNAL_SERVER_ERROR),
    )


# ---------------------------------------------------------------- 注册入口
def register_exception_handlers(app: FastAPI) -> None:
    """在 main.py 中 app.include_router(...) 之前调用：
        from app.core.exception import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)  # 兜底放最后
