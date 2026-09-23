"""FastAPI 入口：中间件、路由挂载、启动钩子

本地启动（在 server/ 目录下）：
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
接口文档：http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings

logger = logging.getLogger("material_space")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动钩子：目前只做日志，预留模型加载 / 任务队列初始化等位置"""
    logger.info("上传目录：%s", get_settings().upload_path.resolve())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    # StaticFiles 挂载时会检查目录存在，所以先建好
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="material-space API", version="0.1.0", lifespan=lifespan)

    # 开发期前端常直接访问后端（不经 vite 代理），这里放开配置里的来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    # 本地存储的上传结果直接静态托管，返回的 url 可直接被前端 <img> 使用
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")

    return app


app = create_app()
