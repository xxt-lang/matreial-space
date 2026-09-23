"""生成任务（占位实现）

现状：等待一小段时间后返回一张 SVG 占位图，用于打通
「前端触发 → 后端 → 前端展示 / 中断」整条链路。

接入真实模型时建议：
1. 任务化：提交到任务队列（RQ / Celery / 自建 GPU 队列），接口先返回任务 id，
   前端再轮询或走 SSE 订阅进度（当前前端是等一次性响应，可先保持同步返回）。
2. 中断：前端点「中断」会 abort 请求、连接随之断开；
   这里用 `request.is_disconnected()` 周期性检测，真实实现应据此取消排队 / 中止推理。
3. 超时：settings.gen_timeout_seconds（默认 300s）。
"""

import asyncio
import random
from urllib.parse import quote

from fastapi import Request

from app.config import get_settings
from app.schemas.gen import GenRequest

# 占位图配色（仅模拟用）
_MOCK_COLORS = ["#f0a63d", "#4f9cf9", "#7ee787", "#e06c9f", "#b692f6"]


class GenerationCancelled(Exception):
    """客户端在生成过程中断开（前端点了「中断」）"""


def _mock_image(seed: int) -> str:
    """造一张 SVG 占位图（data URL），接入真实模型后删除"""
    color = _MOCK_COLORS[seed % len(_MOCK_COLORS)]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
        "<defs><linearGradient id=\"g\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">"
        f'<stop offset="0" stop-color="{color}" stop-opacity="0.9" />'
        '<stop offset="1" stop-color="#0d1117" stop-opacity="0.95" />'
        "</linearGradient></defs>"
        '<rect width="256" height="256" fill="url(#g)" />'
        '<text x="50%" y="50%" fill="#ffffff" font-family="sans-serif" font-size="28"'
        f' text-anchor="middle" dominant-baseline="middle">mock {seed}</text>'
        "</svg>"
    )
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


async def generate_image(payload: GenRequest, request: Request) -> str:
    """执行一次生成，返回图片地址

    :param payload: 生成参数（前端节点上的配置 + 提示词 + 上游节点）
    :param request: 用于检测客户端是否已断开
    :raises GenerationCancelled: 客户端断开时抛出，由路由层处理
    """
    settings = get_settings()

    # 模拟推理耗时；每 0.2s 检查一次客户端连接
    remaining = settings.gen_mock_delay_seconds
    while remaining > 0:
        if await request.is_disconnected():
            raise GenerationCancelled
        await asyncio.sleep(min(0.2, remaining))
        remaining -= 0.2

    # TODO: 用 payload.setting / payload.text / payload.nodes 调用真实模型
    _ = (payload.text, payload.nodes, settings.gen_timeout_seconds)
    return _mock_image(random.randint(0, 999))
