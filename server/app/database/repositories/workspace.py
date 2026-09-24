"""工作空间的数据访问。

只负责「怎么存取」，不含业务规则（如存在性校验后的报错口径），
也不 commit：提交 / 回滚由 services 层的事务控制。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workspace


class WorkspaceRepository:
    """工作空间仓储"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Workspace]:
        """按创建时间倒序列出全部工作空间"""
        result = await self._session.scalars(select(Workspace).order_by(Workspace.created_at.desc()))
        return list(result)

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        """按 id 取单个工作空间，不存在返回 None"""
        return await self._session.get(Workspace, workspace_id)

    async def count(self) -> int:
        """总数（列表接口的 total 字段）"""
        return await self._session.scalar(select(func.count()).select_from(Workspace)) or 0

    async def add(self, workspace: Workspace) -> Workspace:
        """新增；flush 拿到主键与默认时间，提交交给上层事务"""
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def delete(self, workspace: Workspace) -> None:
        """删除；只交给会话标记，实际生效在事务提交时"""
        await self._session.delete(workspace)
        await self._session.flush()
