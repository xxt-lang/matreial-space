"""路由汇总：新增模块在这里挂载

最终路径 = /api（main.py 里挂载的前缀）+ 各模块 prefix
"""

from fastapi import APIRouter

from app.api import gen, health, upload

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(gen.router, prefix="/gen", tags=["gen"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
