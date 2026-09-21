"""所有对外响应模型的基类

全局约定（wire format）：
    Agent 对外（前端 / 跨服务）统一使用 **驼峰** 字段名，与 Spring Boot 后端
    （Jackson 默认驼峰）保持一致，避免前端 / 多服务之间维护两套命名。

实现：
    - alias_generator=to_camel：Pydantic 在序列化时把 snake_case 字段名转成驼峰
      （thread_id -> threadId，created_at -> createdAt）。
    - populate_by_name=True：内部仍可用 snake_case 字段名构造模型（从 ORM 对象、
      服务层代码构造响应时无需切换命名）。
    - ORMModel：在 CamelModel 基础上启用 from_attributes，供读取 ORM 对象的响应模型继承。
"""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """全局统一响应信封，与 Spring Boot 的 {code, msg, data} 对齐。

    约定（wire format）：
        - code：业务状态码；成功为 200（与前端 ApiStatus.success 一致）。
        - msg：提示信息；成功为 "success"，失败时为具体错误文案（前端拦截器读取此字段）。
        - data：业务数据；成功时携带，失败时为 null。

    用法：所有 REST 成功响应都通过本模型包裹后再返回，例如
        return ApiResponse(data=thread_out)
    嵌套的 data 若为 CamelModel（如 ThreadOut），其字段在序列化时自动转驼峰。
    """

    code: int = 200
    msg: str = "success"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: T = None, msg: str = "success") -> "ApiResponse[T]":
        return cls(code=200, msg=msg, data=data)


class CamelModel(BaseModel):
    """响应模型基类：对外序列化统一输出驼峰字段名。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ORMModel(CamelModel):
    """可读取 ORM 对象属性的响应模型基类。

    在 CamelModel 的基础上启用 from_attributes，使响应模型能直接从 SQLAlchemy
    行对象构造（FastAPI 的 response_model 转换也会用到）。
    """

    model_config = ConfigDict(from_attributes=True)
