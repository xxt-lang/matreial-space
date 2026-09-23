"""最小冒烟测试：健康检查、生成占位实现、上传校验

运行（在 server/ 目录下，已装 requirements-dev.txt）：
    pytest -q
"""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_returns_image() -> None:
    response = client.post("/api/gen", json={"id": "image-1", "text": "一只赛博朋克风格的猫"})
    assert response.status_code == 200
    assert response.json()["image"].startswith("data:image/svg+xml")


def test_upload_rejects_non_image() -> None:
    response = client.post(
        "/api/upload",
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 415


def test_upload_accepts_png() -> None:
    response = client.post(
        "/api/upload",
        files={"file": ("pixel.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["url"].startswith("/uploads/")
    assert body["type"] == "image/png"
