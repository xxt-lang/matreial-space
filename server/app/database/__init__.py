"""数据库层：唯一允许出现 SQL / ORM 的地方。

- base.py           Base / engine / async_session_maker / get_session() 依赖
- models.py         ORM 表定义
- repositories/     仓储（一个聚合一个文件），不负责 commit

事务边界在 services 层；本层不感知 HTTP，也不写业务规则。
详见 docs/backend-standards.md 第 7 节。
"""
