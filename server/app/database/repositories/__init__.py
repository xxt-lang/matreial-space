"""仓储层：一个聚合一个文件，封装该聚合的数据访问。

- 方法只做增删查改与 flush，不 commit（事务边界在 services 层）
- 返回值可以是 ORM 对象，由 service 转成 schema 后再交给上层
"""
