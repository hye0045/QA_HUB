import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import settings

async def run_migration():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        with open("migrations/add_device_profiles.sql", "r", encoding="utf-8") as f:
            sql = f.read()
        for statement in sql.split(";"):
            if statement.strip():
                from sqlalchemy import text
                await conn.execute(text(statement))
        print("Migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
