"""工作空间接口测试：创建 → 列表 → 删除，以及参数校验与 404

用 conftest 的 client 装置（会跑 lifespan 建表），数据库是临时文件、会话间复用，
所以断言都用「相对变化」（新 id 在不在列表里），不依赖绝对条数。
"""

from fastapi.testclient import TestClient


def _create(client: TestClient, name: str = "素材画布", description: str = "") -> dict:
    response = client.post("/api/workspaces", json={"name": name, "description": description})
    assert response.status_code == 201
    return response.json()


def _list_ids(client: TestClient) -> list[str]:
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["items"])
    return [item["id"] for item in body["items"]]


def test_create_returns_workspace(client: TestClient) -> None:
    body = _create(client, "角色设定", "第一位主角的参考图")

    assert body["id"]
    assert body["name"] == "角色设定"
    assert body["description"] == "第一位主角的参考图"
    # 时间补上 UTC 标记，前端可直接 new Date()
    assert body["created_at"].endswith("+00:00")
    assert body["updated_at"].endswith("+00:00")


def test_created_workspace_appears_in_list(client: TestClient) -> None:
    created = _create(client, "场景氛围")

    assert created["id"] in _list_ids(client)


def test_create_trims_whitespace(client: TestClient) -> None:
    body = _create(client, "  留白  ", "  说明  ")

    assert body["name"] == "留白"
    assert body["description"] == "说明"


def test_create_rejects_blank_name(client: TestClient) -> None:
    assert client.post("/api/workspaces", json={"name": "   "}).status_code == 422
    assert client.post("/api/workspaces", json={"name": ""}).status_code == 422


def test_create_rejects_too_long_fields(client: TestClient) -> None:
    assert client.post("/api/workspaces", json={"name": "长" * 65}).status_code == 422
    assert client.post("/api/workspaces", json={"name": "ok", "description": "长" * 256}).status_code == 422


def test_get_workspace_by_id(client: TestClient) -> None:
    created = _create(client, "画布标题")

    response = client.get(f"/api/workspaces/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_workspace_returns_404(client: TestClient) -> None:
    response = client.get("/api/workspaces/not-exist")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "工作空间不存在：not-exist"}


def test_delete_removes_workspace(client: TestClient) -> None:
    workspace_id = _create(client, "待删除")["id"]

    assert client.delete(f"/api/workspaces/{workspace_id}").status_code == 204
    assert workspace_id not in _list_ids(client)


def test_delete_missing_workspace_returns_404(client: TestClient) -> None:
    response = client.delete("/api/workspaces/not-exist")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "工作空间不存在：not-exist"}
