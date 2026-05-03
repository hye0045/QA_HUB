import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("backend/.env")

MIGRATIONS = [
    "backend/migrations/add_device_profiles.sql",
    "backend/migrations/add_defect_ai_columns.sql",
    "backend/migrations/add_feature_model_audit.sql",
]

async def run_all_migrations():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        for migration_file in MIGRATIONS:
            print(f"Running: {migration_file}")
            with open(migration_file, "r", encoding="utf-8") as f:
                sql = f.read()
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.startswith("--"):
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        print(f"  ⚠️  Warning (có thể đã tồn tại): {e}")
            print(f"  ✅ Done: {migration_file}")

    print("\n✅ Tất cả migration đã chạy xong.")

if __name__ == "__main__":
    asyncio.run(run_all_migrations())
