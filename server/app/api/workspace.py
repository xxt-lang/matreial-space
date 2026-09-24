"""工作空间管理接口

GET    /api/workspaces           列表 → { items, total }
POST   /api/workspaces           创建 → 工作空间对象（201）
GET    /api/workspaces/{id}      详情 → 工作空间对象（不存在则 404）
DELETE /api/workspaces/{id}      删除 → 204（不存在则 404）

路由层只做协议转换：校验入参 → 调 service → 组装响应。
会话对象只是透传给 service（不在路由里执行任何查询），业务异常由
app.exceptions 的处理器统一映射，所以这里没有 try/except。
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from app.services import workspace as workspace_service

router = APIRouter()


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(session: AsyncSession = Depends(get_session)) -> WorkspaceListResponse:
    """列出全部工作空间"""
    workspaces, total = await workspace_service.list_workspaces(session)
    return WorkspaceListResponse(
        items=[WorkspaceResponse.model_validate(item) for item in workspaces],
        total=total,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> WorkspaceResponse:
    """创建工作空间"""
    workspace = await workspace_service.create_workspace(session, payload)
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
) -> WorkspaceResponse:
    """取单个工作空间（画布用它展示当前工作空间名称）"""
    workspace = await workspace_service.get_workspace(session, workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """删除工作空间（前端会在调用前做二次确认）"""
    await workspace_service.delete_workspace(session, workspace_id)
