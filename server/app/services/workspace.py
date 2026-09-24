"""工作空间业务逻辑：用例编排 + 事务边界。

- 仓储只 flush，`async with session.begin()` 决定提交 / 回滚（一个用例一个事务）
- 领域异常在这里抛（如 NotFoundError），HTTP 状态码由 app.exceptions 的处理器决定
- 不感知 HTTP，也不写 SQL
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace
from app.database.repositories.workspace import WorkspaceRepository
from app.exceptions import NotFoundError
from app.schemas.workspace import WorkspaceCreateRequest


async def list_workspaces(session: AsyncSession) -> tuple[list[Workspace], int]:
    """列出全部工作空间（按创建时间倒序）与总数"""
    repository = WorkspaceRepository(session)
    return await repository.list_all(), await repository.count()


async def create_workspace(session: AsyncSession, payload: WorkspaceCreateRequest) -> Workspace:
    """创建工作空间"""
    repository = WorkspaceRepository(session)
    workspace = Workspace(name=payload.name, description=payload.description)

    async with session.begin():
        await repository.add(workspace)

    return workspace


async def get_workspace(session: AsyncSession, workspace_id: str) -> Workspace:
    """取单个工作空间（画布用它展示当前工作空间名称）

    :raises NotFoundError: 工作空间不存在（由处理器转成 404）
    """
    return await _get_or_raise(WorkspaceRepository(session), workspace_id)


async def delete_workspace(session: AsyncSession, workspace_id: str) -> None:
    """删除工作空间

    :raises NotFoundError: 工作空间不存在（由处理器转成 404）
    """
    repository = WorkspaceRepository(session)

    async with session.begin():
        workspace = await _get_or_raise(repository, workspace_id)
        await repository.delete(workspace)


async def _get_or_raise(repository: WorkspaceRepository, workspace_id: str) -> Workspace:
    """取不到就抛 NotFoundError；"不存在" 的报错口径只在这里维护"""
    workspace = await repository.get_by_id(workspace_id)
    if workspace is None:
        raise NotFoundError(f"工作空间不存在：{workspace_id}")
    return workspace
