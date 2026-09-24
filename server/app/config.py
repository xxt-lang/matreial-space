"""应用配置：统一从环境变量 / .env 读取，避免散落的 os.getenv"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全部配置项，默认值可直接本地跑起来（见 .env.example）"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 服务
    host: str = "127.0.0.1"
    port: int = 8000

    # 跨域来源（逗号分隔；开发期走 vite 代理时其实用不到）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 上传
    upload_dir: str = "uploads"
    upload_max_bytes: int = 5 * 1024 * 1024

    # 数据库：默认 SQLite，文件落在 data/ 目录（见 app/database/base.py）
    data_dir: str = "data"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # 生成
    gen_timeout_seconds: int = 300
    gen_mock_delay_seconds: float = 2.4

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的字符串拆成列表"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def upload_path(self) -> Path:
        """上传目录路径（相对 server/ 运行目录）"""
        return Path(self.upload_dir)

    @property
    def data_path(self) -> Path:
        """数据库文件所在目录（相对 server/ 运行目录）"""
        return Path(self.data_dir)


@lru_cache
def get_settings() -> Settings:
    """配置只解析一次，全局复用"""
    return Settings()
