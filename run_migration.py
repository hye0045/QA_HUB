import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def run_migration():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url, echo=True)
    
    with open("backend/migrations/add_feature_model_audit.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    async with engine.begin() as conn:
        for statement in sql.split(";"):
            if statement.strip():
                await conn.execute(text(statement.strip()))
    
    print("Migration successful")

if __name__ == "__main__":
    asyncio.run(run_migration())
