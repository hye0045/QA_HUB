import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "QA HUB API"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/QA_HUB")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "your_groq_api_key")
    
    # JWT Auth Configs
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-qa-hub")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days expiry

    class Config:
        env_file = ".env"

settings = Settings()
