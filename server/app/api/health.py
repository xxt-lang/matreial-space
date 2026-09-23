"""健康检查：部署探活、前端联调自检

GET /api/health
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
