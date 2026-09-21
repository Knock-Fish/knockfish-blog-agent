"""JWT 验签 + 全局鉴权中间件（验证 Spring Boot 签发的 RS256 token）

- Spring Boot 持私钥签发，本 Agent 只持公钥验签；即使被攻破也无法伪造 token。
- token 用户字段为 `userId`（驼峰），与 JwtUtil 一致。
- AuthMiddleware 实现 secure-by-default：默认全部请求需合法 token，仅白名单放行。
"""
import logging
import os
from pathlib import Path

import jwt
from fastapi import Request
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .config import settings
from .exception import UnauthorizedException

logger = logging.getLogger(__name__)

_PUBLIC_KEY_PATH = Path(
    os.getenv(
        "JWT_PUBLIC_KEY_PATH",
        str(Path(__file__).resolve().parent.parent / "certs" / "jwt_public_key.pem"),
    )
)


def _load_public_key() -> str:
    if not _PUBLIC_KEY_PATH.exists():
        raise RuntimeError(f"JWT 公钥文件不存在: {_PUBLIC_KEY_PATH}")
    return _PUBLIC_KEY_PATH.read_text(encoding="utf-8")


_PUBLIC_KEY: str = _load_public_key()

# 放行白名单
AUTH_WHITELIST: list[str] = ["/api/v1/health",  "/redoc", "/openapi.json"]


def verify_token(token: str) -> int:
    """验签单个 token，返回 user_id；失败抛 UnauthorizedException。"""
    try:
        payload = jwt.decode(
            token,
            _PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER if settings.JWT_ISSUER else None,
        )
    except ExpiredSignatureError:
        raise UnauthorizedException("登录已过期，请重新登录")
    except InvalidTokenError as exc:
        logger.warning("JWT 验签失败: %s", exc)
        raise UnauthorizedException("身份校验失败，token 无效")
    user_id = payload.get("userId")
    if user_id is None:
        raise UnauthorizedException("token 中缺少用户标识")
    return int(user_id)


def get_current_user(request: Request) -> int:
    """路由依赖：优先取中间件已验好的 user_id（不重复验签），否则从头验。"""
    user_id = getattr(request.state, "user_id", None)
    if user_id is not None:
        return int(user_id)
    auth = request.headers.get("Authorization", "")
    if not auth or not auth.lower().startswith("bearer "):
        raise UnauthorizedException("缺少 Authorization 请求头")
    return verify_token(auth[7:].strip())


class AuthMiddleware(BaseHTTPMiddleware):
    """secure-by-default：默认拦截一切，仅白名单 / CORS 预检放行。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or self._whitelisted(request.url.path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth or not auth.lower().startswith("bearer "):
            return self._unauthorized("缺少或格式错误的 Authorization 请求头")
        try:
            user_id = verify_token(auth[7:].strip())
        except UnauthorizedException as exc:
            # 中间件位于 ExceptionMiddleware 外层，此处 raise 会被最外层
            # ServerErrorMiddleware 兜底成 500，因此必须直接返回统一 401 响应体。
            return self._unauthorized(exc.message)
        request.state.user_id = user_id
        return await call_next(request)

    @staticmethod
    def _unauthorized(message: str) -> JSONResponse:
        """构造统一 401 响应体，格式与 exception.py 保持一致。"""
        return JSONResponse(
            status_code=401,
            content={"code": 401, "message": message, "data": None},
        )

    @staticmethod
    def _whitelisted(path: str) -> bool:
        for item in AUTH_WHITELIST:
            base = item.rstrip("/")
            if path == base or path.startswith(base + "/"):
                return True
        return False
