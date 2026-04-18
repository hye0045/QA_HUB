import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "QA HUB API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/QA_HUB")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "your_groq_api_key")
    
    # Redmine Configs
    REDMINE_URL: str = os.getenv("REDMINE_URL", "https://redhornet.csg.kyocera.co.jp/redmine")
    REDMINE_API_KEY: str = os.getenv("REDMINE_API_KEY", "96feffe2043d29abf8fd7055b4e3c68561fcff")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "eb1236")
    
    # JWT Auth Configs
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-qa-hub")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days expiry

    class Config:
        env_file = ".env"

settings = Settings()
