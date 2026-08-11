"""
HTTP 状态码常量及错误消息映射
"""
from typing import Dict


class HTTPStatus:
    """HTTP 状态码常量"""
    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # 4xx Client Error
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429

    # 5xx Server Error
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# 状态码 → 默认错误消息映射
DEFAULT_ERROR_MESSAGES: Dict[int, str] = {
    HTTPStatus.BAD_REQUEST: "请求参数错误",
    HTTPStatus.UNAUTHORIZED: "身份验证失败，请重新登录",
    HTTPStatus.FORBIDDEN: "权限不足，无法执行此操作",
    HTTPStatus.NOT_FOUND: "请求的资源不存在",
    HTTPStatus.METHOD_NOT_ALLOWED: "请求方法不允许",
    HTTPStatus.CONFLICT: "资源冲突，请检查后重试",
    HTTPStatus.UNPROCESSABLE_ENTITY: "请求格式正确但语义错误",
    HTTPStatus.TOO_MANY_REQUESTS: "请求过于频繁，请稍后再试",
    HTTPStatus.INTERNAL_SERVER_ERROR: "服务器内部错误，请稍后重试",
    HTTPStatus.BAD_GATEWAY: "网关错误，请稍后重试",
    HTTPStatus.SERVICE_UNAVAILABLE: "服务暂不可用，请稍后重试",
    HTTPStatus.GATEWAY_TIMEOUT: "网关超时，请稍后重试",
}


def get_default_error_message(status_code: int) -> str:
    """根据状态码获取默认错误消息"""
    return DEFAULT_ERROR_MESSAGES.get(
        status_code,
        f"请求失败 (HTTP {status_code})"
    )