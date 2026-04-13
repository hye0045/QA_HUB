import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "QA HUB API"
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "your_supabase_url")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "your_supabase_key")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "your_groq_api_key")

    class Config:
        env_file = ".env"

settings = Settings()
