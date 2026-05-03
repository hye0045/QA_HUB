import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def fix():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url, echo=True, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        try:
            await conn.execute(text("CREATE TYPE testcase_status AS ENUM ('draft', 'active', 'deprecated');"))
            print("Created testcase_status ENUM")
        except Exception as e:
            pass
            
        try:
            await conn.execute(text("ALTER TABLE testcase ADD COLUMN status testcase_status NOT NULL DEFAULT 'draft';"))
            print("Added status column")
        except Exception as e:
            pass

        columns_to_add = [
            "model_id VARCHAR",
            "test_type VARCHAR",
            "precondition VARCHAR",
            "is_affected BOOLEAN NOT NULL DEFAULT FALSE"
        ]

        for col in columns_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE testcase ADD COLUMN {col};"))
                print(f"Added {col}")
            except Exception as e:
                pass

if __name__ == "__main__":
    asyncio.run(fix())
