from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./aom.db"

    # Parse 兼容配置
    APPLICATION_ID: str = "game.ignite.aom.prd"
    MASTER_KEY: str = secrets.token_hex(32)

    # JWT 配置
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 365

    # Google OAuth 配置 (可选)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 1337

    class Config:
        env_file = ".env"


settings = Settings()
