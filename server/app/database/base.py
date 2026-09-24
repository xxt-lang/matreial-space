"""数据库基础设施：引擎、会话工厂、建表与会话依赖。

- 连接串来自 `settings.database_url`（默认 SQLite，文件在 server/data/app.db）
- 事务边界在 services 层：仓储只 flush，不 commit
- 本层不感知 HTTP 与业务规则
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

_settings = get_settings()


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""


# 连接是懒建立的，所以此时 data/ 目录还不存在也没关系（init_db 会先建目录）
engine = create_async_engine(_settings.database_url)

# expire_on_commit=False：提交后对象属性仍可读，service 层可直接把 ORM 对象交给上层转换
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：一个请求一个会话。

    这里不提交也不回滚，事务由 service 用 `async with session.begin()` 控制。
    """
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    """建表（开发期方案；表结构稳定后改用 Alembic 迁移）"""
    # 延迟导入：确保所有模型都注册进 Base.metadata 之后再建表
    from app.database import models  # noqa: F401

    _settings.data_path.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """关闭连接池（lifespan 退出时调用）"""
    await engine.dispose()
