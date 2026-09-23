"""生成接口

POST /api/gen
请求体：GenRequest（节点 id + 生成配置 + 提示词 + 上游节点）
响应：GenResponse（{ image: "<图片地址>" }）

中断：前端点「中断」会 abort 请求，服务端连接断开 → services 里检测到后取消任务。
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.schemas.gen import GenRequest, GenResponse
from app.services.generator import GenerationCancelled, generate_image

logger = logging.getLogger("material_space.gen")

router = APIRouter()

# 客户端已断开（499 是 nginx 的事实标准，FastAPI 允许自定义状态码）
CLIENT_CLOSED_REQUEST = 499


@router.post("", response_model=GenResponse)
async def create_generation(payload: GenRequest, request: Request) -> GenResponse:
    try:
        image = await generate_image(payload, request)
    except GenerationCancelled:
        logger.info("生成任务被客户端中断：node=%s", payload.id)
        raise HTTPException(CLIENT_CLOSED_REQUEST, detail="客户端已断开，任务已中断") from None

    return GenResponse(image=image)
