"""领域异常：业务层抛出，由 main.py 注册的处理器统一转成 HTTP 响应。

约定（见 docs/backend-standards.md 第 9 节）：
- 业务代码不 import fastapi，也不自己决定 HTTP 状态码；
  异常自带 code / status_code，处理器负责序列化成 { code, message }。
- 因此 controller 里不需要 try/except，只管调用 service。
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("material_space.error")


class AppError(Exception):
    """领域异常基类"""

    code: str = "app_error"
    status_code: int = 400
    message: str = "请求处理失败"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(AppError):
    """资源不存在"""

    code = "not_found"
    status_code = 404
    message = "资源不存在"


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """把领域异常转成统一错误体；只在预期内，记 info 即可"""
    logger.info("业务异常：code=%s message=%s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )
