import asyncio
from sqlalchemy.future import select
from db.database import AsyncSessionLocal, engine
from db.models import User
from core.security import get_password_hash

async def fix_password():
    async with AsyncSessionLocal() as session:
        # Tìm tài khoản admin
        result = await session.execute(select(User).where(User.email == "admin@thundersoft.com"))
        admin_user = result.scalars().first()
        
        if admin_user:
            # Ghi đè lại mật khẩu chuẩn xác băm từ thư viện nội bộ
            admin_user.password_hash = get_password_hash("admin123")
            await session.commit()
            print("✅ Đã khôi phục mật khẩu chuẩn cho admin@thundersoft.com thành 'admin123'!")
        else:
            print("❌ Không tìm thấy admin@thundersoft.com trong Database.")

if __name__ == "__main__":
    asyncio.run(fix_password())
