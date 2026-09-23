"""图片上传接口

POST /api/upload
multipart/form-data，字段名 `file`；返回 { url, name, size, type }

限制与前端保持一致：仅图片类型、默认 5MB 上限（用环境变量 UPLOAD_MAX_BYTES 调整）。
文件先落在本地 uploads/ 并静态托管；接入对象存储后改为上传到 OSS/S3 并返回外链。
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.schemas.upload import UploadResponse

router = APIRouter()

# 允许的 MIME 前缀
ALLOWED_TYPE_PREFIX = "image/"

# 扩展名白名单（比 MIME 更可靠，防止 multipart 里伪造 content-type）
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


def _safe_suffix(filename: str | None) -> str:
    """取一个安全的扩展名，不在白名单内时返回空串"""
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in ALLOWED_SUFFIXES else ""


@router.post("", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()

    if not (file.content_type or "").startswith(ALLOWED_TYPE_PREFIX):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="仅支持图片文件")

    content = await file.read()
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片超过大小上限")

    settings.upload_path.mkdir(parents=True, exist_ok=True)
    # 用 uuid 命名，避免同名覆盖与路径穿越
    stored_name = f"{uuid.uuid4().hex}{_safe_suffix(file.filename)}"
    (settings.upload_path / stored_name).write_bytes(content)

    return UploadResponse(
        url=f"/uploads/{stored_name}",
        name=file.filename or stored_name,
        size=len(content),
        type=file.content_type or "",
    )
