# """
# 通用异步 HTTP 客户端
# 支持 JWT 认证透传，统一错误处理，供所有需要调用外部 API 的模块使用
# """
# import aiohttp
# import asyncio
# from typing import Optional, Dict, Any
# from contextvars import ContextVar
# from ..core.config import settings
# # 配置
# HTTP_TIMEOUT = settings.HTTP_TIMEOUT
# HTTP_BASE_URL = settings.HTTP_BASE_URL
#
# # JWT 上下文（用于请求级别的认证透传）
# _jwt_token_var: ContextVar[str | None] = ContextVar("jwt_token", default=None)
#
#
# def set_current_token(token: str):
#     """
#     设置当前请求的 JWT Token
#     """
#     _jwt_token_var.set(token)
#
#
# def get_current_token() -> str:
#     """
#     获取当前请求的 JWT Token
#     """
#     token = _jwt_token_var.get()
#     if not token:
#         raise ValueError("JWT Token 未设置，请检查请求上下文")
#     return token
#
#
# def _get_headers() -> dict:
#     """
#     构建带 JWT 的请求头
#     """
#     return {
#         "Authorization": f"Bearer {get_current_token()}",
#         "Content-Type": "application/json"
#     }
#
#
# # 自定义异常
#
# class APIError(Exception):
#     """
#     API 调用异常（HTTP 错误 + 业务错误）
#     """
#
#     def __init__(self, code: int, msg: str, status_code: int = None):
#         self.code = code  # 业务错误码
#         self.msg = msg  # 错误信息
#         self.status_code = status_code  # HTTP 状态码
#         super().__init__(f"[{code}] {msg}")
#
#
# class APITimeoutError(APIError):
#     """请求超时异常"""
#     pass
#
#
# class APIConnectionError(APIError):
#     """网络连接异常"""
#     pass
#
#
# # 核心请求函数
#
# async def _request(
#         method: str,
#         path: str,
#         base_url: Optional[str] = None,
#         data: Optional[Dict] = None,
#         params: Optional[Dict] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     统一 HTTP 请求方法
#
#     Args:
#         method: HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
#         path: API 路径（相对路径，如 "/article/1"）
#         base_url: 基础 URL，默认使用 SPRINGBOOT_URL
#         data: POST/PUT 请求的 JSON body
#         params: 查询参数
#         headers: 额外的请求头（会合并到默认头）
#         timeout: 超时时间（秒）
#         extract_data: 是否自动提取统一响应格式中的 data 字段
#
#     Returns:
#         如果 extract_data=True，返回 result.get("data")
#         如果 extract_data=False，返回完整 JSON 响应
#
#     Raises:
#         APIError: HTTP 状态码异常或业务错误 (code != 200)
#         APITimeoutError: 超时
#         APIConnectionError: 网络连接问题
#     """
#     url = f"{base_url or HTTP_BASE_URL}{path}"
#
#     # 合并请求头
#     default_headers = _get_headers()
#     if headers:
#         default_headers.update(headers)
#
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.request(
#                     method=method,
#                     url=url,
#                     json=data,
#                     params=params,
#                     headers=default_headers,
#                     timeout=aiohttp.ClientTimeout(total=timeout)
#             ) as resp:
#                 # 处理 HTTP 状态码
#                 if resp.status == 401:
#                     raise APIError(401, "身份验证失败，请重新登录", status_code=resp.status)
#                 elif resp.status == 403:
#                     raise APIError(403, "权限不足，无法执行此操作", status_code=resp.status)
#                 elif resp.status == 404:
#                     raise APIError(404, "请求的资源不存在", status_code=resp.status)
#                 elif resp.status >= 500:
#                     raise APIError(resp.status, f"服务器内部错误 (HTTP {resp.status})", status_code=resp.status)
#                 elif resp.status != 200:
#                     raise APIError(resp.status, f"请求失败 (HTTP {resp.status})", status_code=resp.status)
#
#                 # 解析 JSON
#                 try:
#                     result = await resp.json()
#                 except aiohttp.ContentTypeError:
#                     text = await resp.text()
#                     raise APIError(500, f"响应格式异常: {text[:100]}", status_code=resp.status)
#
#                 # 如果不需要提取 data，直接返回完整结果
#                 if not extract_data:
#                     return result
#
#                 # 检查统一响应格式 Result<T>
#                 code = result.get("code")
#                 if code is None:
#                     # 没有 code 字段，可能是直接返回的数据（兼容旧接口）
#                     return result
#
#                 if code != 200:
#                     msg = result.get("msg", "未知错误")
#                     raise APIError(code, msg, status_code=resp.status)
#
#                 return result.get("data")
#
#     except asyncio.TimeoutError:
#         raise APITimeoutError(408, f"请求超时 ({timeout}s)")
#     except aiohttp.ClientConnectionError as e:
#         raise APIConnectionError(503, f"网络连接失败: {str(e)}")
#     except aiohttp.ClientError as e:
#         raise APIConnectionError(500, f"客户端错误: {str(e)}")
#
#
# # 对外暴露的便捷方法
#
# async def get(
#         path: str,
#         params: Optional[Dict] = None,
#         base_url: Optional[str] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     异步 GET 请求
#     """
#     return await _request("GET", path, base_url=base_url, params=params,
#                           headers=headers, timeout=timeout, extract_data=extract_data)
#
#
# async def post(
#         path: str,
#         data: Optional[Dict] = None,
#         base_url: Optional[str] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     异步 POST 请求
#     """
#     return await _request("POST", path, base_url=base_url, data=data,
#                           headers=headers, timeout=timeout, extract_data=extract_data)
#
#
# async def put(
#         path: str,
#         data: Optional[Dict] = None,
#         base_url: Optional[str] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     异步 PUT 请求
#     """
#     return await _request("PUT", path, base_url=base_url, data=data,
#                           headers=headers, timeout=timeout, extract_data=extract_data)
#
#
# async def patch(
#         path: str,
#         data: Optional[Dict] = None,
#         base_url: Optional[str] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     异步 PATCH 请求
#     """
#     return await _request("PATCH", path, base_url=base_url, data=data,
#                           headers=headers, timeout=timeout, extract_data=extract_data)
#
#
# async def delete(
#         path: str,
#         base_url: Optional[str] = None,
#         headers: Optional[Dict] = None,
#         timeout: int = HTTP_TIMEOUT,
#         extract_data: bool = True
# ) -> Any:
#     """
#     异步 DELETE 请求
#     """
#     return await _request("DELETE", path, base_url=base_url,
#                           headers=headers, timeout=timeout, extract_data=extract_data)