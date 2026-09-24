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
from app.database.base import dispose_db, init_db
from app.exceptions import AppError, app_error_handler

logger = logging.getLogger("material_space")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动钩子：建表 /（将来的）模型加载、任务队列初始化都放这里，退出时统一释放"""
    settings = get_settings()
    logger.info("上传目录：%s", settings.upload_path.resolve())
    await init_db()
    logger.info("数据库：%s", settings.database_url)
    yield
    await dispose_db()


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

    # 领域异常统一转成 { code, message }，路由层就不必写 try/except
    app.add_exception_handler(AppError, app_error_handler)

    app.include_router(api_router, prefix="/api")

    # 本地存储的上传结果直接静态托管，返回的 url 可直接被前端 <img> 使用
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")

    return app


app = create_app()
