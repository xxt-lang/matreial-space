"""工作空间接口的请求 / 响应模型

与前端 web/src/views/home/api/workspace.js 一一对应。
时间统一以 ISO 8601（UTC，带 +00:00）返回，前端可直接 new Date() 转本地时间。
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class WorkspaceCreateRequest(BaseModel):
    """创建工作空间"""

    name: str = Field(min_length=1, max_length=64, description="工作空间名称")
    description: str = Field(default="", max_length=255, description="备注 / 描述")

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        """去首尾空白；全是空白按非法值处理（422），避免出现看不见名字的空间"""
        name = value.strip()
        if not name:
            raise ValueError("工作空间名称不能为空白")
        return name

    @field_validator("description")
    @classmethod
    def _normalize_description(cls, value: str) -> str:
        return value.strip()


class WorkspaceResponse(BaseModel):
    """工作空间详情"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="工作空间 id")
    name: str = Field(description="工作空间名称")
    description: str = Field(description="备注 / 描述")
    created_at: datetime = Field(description="创建时间（UTC）")
    updated_at: datetime = Field(description="更新时间（UTC）")

    @field_serializer("created_at", "updated_at")
    def _serialize_time(self, value: datetime) -> str:
        """SQLite 存的是无时区时间（值为 UTC），补上时区标记再输出"""
        return value.replace(tzinfo=UTC).isoformat()


class WorkspaceListResponse(BaseModel):
    """工作空间列表：对象包一层，便于后续加分页字段"""

    items: list[WorkspaceResponse] = Field(default_factory=list, description="工作空间列表")
    total: int = Field(description="总数")
