from fastapi import APIRouter
from .endpoints.health import router as health_router
from .endpoints.chat import router as chat_router


api_router = APIRouter(prefix="/api/v1")


api_router.include_router(health_router, tags=["健康检查"])
api_router.include_router(chat_router, tags=["聊天"])

