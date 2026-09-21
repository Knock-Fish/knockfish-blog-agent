"""全局配置（Pydantic Settings 自动读取 .env）"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用全局配置
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用元信息
    APP_NAME: str = Field(default="KnockFish Blog Agent", description="应用名称")
    APP_ENV: str = Field(default="dev", description="运行环境: dev / staging / prod")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    APP_RELOAD: bool = Field(default=True, description="uvicorn 热重载（仅开发环境启用）")

    # LLM
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL_ID: str
    LLM_TIMEOUT: int = Field(default=60, description="LLM 请求超时秒数")
    LLM_TEMPERATURE: float = Field(default=0.7, description="默认采样温度")

    # HTTP
    HTTP_BASE_URL: str
    HTTP_TIMEOUT: int = Field(default=30, description="HTTP 请求超时秒数")

    # Database
    # 连接串内含数据库账号密码，必须由 .env 提供；代码里不保留任何默认值
    DATABASE_URL: str = Field(
        description="PostgreSQL 异步连接串（业务表 + LangGraph 检查点共用），"
        "格式：postgresql+asyncpg://user:password@host:5432/dbname",
    )

    # JWT（验证 Spring Boot 签发的 RS256 token）
    JWT_ALGORITHM: str = Field(default="RS256", description="JWT 验签算法，须与 Spring Boot 一致")
    JWT_ISSUER: str | None = Field(default=None, description="可选：校验 token 签发方(iss)，不填则不校验")

    # CORS（默认仅放行本地开发端口；生产域名请通过环境变量 CORS_ALLOW_ORIGINS 覆盖，勿写入代码）
    CORS_ALLOW_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:8081",
            "http://localhost:8000",
        ],
        description="显式允许的前端源白名单（默认仅本地开发端口）",
    )
    CORS_ALLOW_ORIGIN_REGEX: str = Field(
        default=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        description="兜底正则：放行所有 localhost / 127.0.0.1 任意端口（开发环境）",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True, description="是否允许携带凭据（Authorization/Cookie）；启用后不能用通配符源"
    )


"""一个缓存的 Settings 实例，确保配置只被加载一次。"""
settings = Settings()
