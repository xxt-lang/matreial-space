"""pytest 公共装置：把数据库指向临时文件，避免测试污染 server/data/app.db

注意：环境变量必须在导入 app.main 之前设置 —— Settings 是 lru_cache，只解析一次。
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="material-space-test-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_TEMP_DIR / 'test.db').as_posix()}"

from app.main import app  # noqa: E402  （必须在设置 DATABASE_URL 之后导入）


@pytest.fixture()
def client():
    """使用 with 进入客户端，触发 lifespan（建表）后再发请求"""
    with TestClient(app) as test_client:
        yield test_client
