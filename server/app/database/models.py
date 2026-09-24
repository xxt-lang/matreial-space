"""ORM 表定义：只写表结构与约束，查询逻辑放 repositories/。

时间统一存 UTC（SQLite 不保存时区），接口层序列化时再补 +00:00 标记。
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def new_id() -> str:
    """主键：uuid4 十六进制（32 位），避免自增 id 被遍历"""
    return uuid4().hex


def utcnow() -> datetime:
    """统一的创建 / 更新时间取值"""
    return datetime.now(UTC)


class TimestampMixin:
    """公共时间戳列"""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Workspace(Base, TimestampMixin):
    """工作空间：一张素材画布的容器"""

    __tablename__ = "workspace"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255), default="")

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name!r}>"
