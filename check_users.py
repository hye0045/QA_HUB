import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv("backend/.env")

async def test():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT email, role FROM users"))
        users = r.fetchall()
        print(f"User count: {len(users)}")
        for u in users:
            print(f"- {u.email} ({u.role})")

if __name__ == "__main__":
    asyncio.run(test())
