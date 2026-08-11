"""全局配置（Pydantic Settings 自动读取 .env）

职责：
- 单一真相源：所有环境变量 / 配置项集中在此声明
- 类型安全：启动时校验，配置缺项直接崩溃（Fail Fast）
- 关注点分离：本模块仅负责"读配置"，不负责创建 LLM/Graph 等对象
"""
from typing import List
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

    # 日志
    LOG_LEVEL: str = Field(default="INFO", description="日志级别: DEBUG/INFO/WARNING/ERROR")
    LOG_FORMAT: str = Field(
        default="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        description="标准 logging 格式",
    )

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = Field(
        default_factory=lambda: ["*"],
        description="CORS 允许来源列表，默认放行所有",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # LLM
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL_ID: str
    LLM_TIMEOUT: int = Field(default=60, description="LLM 请求超时秒数")
    LLM_TEMPERATURE: float = Field(default=0.7, description="默认采样温度")

    # HTTP
    HTTP_BASE_URL: str
    HTTP_TIMEOUT: int = Field(default=30, description="HTTP 请求超时秒数")

    # ---- LangGraph / 会话 ----
    # 是否启用 LangSmith 追踪（默认关，需要设置 LANGCHAIN_API_KEY 时开启）
    LANGSMITH_TRACING: bool = Field(default=False)


"""一个缓存的 Settings 实例，确保配置只被加载一次。"""
settings = Settings()
