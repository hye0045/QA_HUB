import os
from pydantic_settings import BaseSettings


def _require_env(key: str) -> str:
    """Đọc biến môi trường bắt buộc. Raise ValueError nếu thiếu."""
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"[CONFIG ERROR] Environment variable '{key}' is not set. "
            f"Please add it to your .env file."
        )
    return value


class Settings(BaseSettings):
    PROJECT_NAME: str = "QA HUB API"

    # Database (bắt buộc)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/QA_HUB"
    )

    # AI Integration (bắt buộc - không có default)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Redmine Integration (bắt buộc - không có default secrets)
    REDMINE_URL: str = os.getenv("REDMINE_URL", "https://redhornet.csg.kyocera.co.jp/redmine")
    REDMINE_API_KEY: str = os.getenv("REDMINE_API_KEY", "")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "")

    # JWT Auth (bắt buộc - không có default)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 ngày

    def validate_secrets(self):
        """Gọi hàm này lúc startup để đảm bảo tất cả secret bắt buộc đã được set."""
        required = {
            "SECRET_KEY": self.SECRET_KEY,
            "REDMINE_API_KEY": self.REDMINE_API_KEY,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"[STARTUP FAILED] Missing required environment variables: {missing}. "
                f"Please check your .env file."
            )

    class Config:
        env_file = ".env"


settings = Settings()
settings.validate_secrets()
