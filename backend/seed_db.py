import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_password_hash
from db.database import engine, Base, AsyncSessionLocal
from db.models import User, UserRole, Specification, SpecVersion, Testcase, Defect
from services.ai_service import get_embedding

async def seed_data():
    async with engine.begin() as conn:
        # Tùy chọn: Xóa data cũ nếu muốn làm mới hoàn toàn (Cẩn thận khi dùng thực tế)
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # ==========================================
        # 1. TẠO USER (Admin & Tester)
        # ==========================================
        admin_id = uuid.uuid4()
        tester_id = uuid.uuid4()
        
        # Kiểm tra xem user tồn tại chưa
        from sqlalchemy.future import select
        res = await session.execute(select(User).where(User.email == "admin@thundersoft.com"))
        if not res.scalars().first():
            admin = User(id=admin_id, email="admin@thundersoft.com", full_name="System Admin", 
                         password_hash=get_password_hash("admin123"), role=UserRole.admin, is_mentor=True)
            tester = User(id=tester_id, email="tester@thundersoft.com", full_name="John Doe QA", 
                          password_hash=get_password_hash("test1234"), role=UserRole.tester)
            session.add_all([admin, tester])
            print("[+] Đã tạo Users (Admin & Tester).")
        else:
            admin_id = res.scalars().first().id
            print("[-] Users đã tồn tại, bỏ qua tạo mới.")

        # ==========================================
        # 2. TẠO SPECIFICATION MẪU (Tính năng Login)
        # ==========================================
        spec_id = uuid.uuid4()
        content_spec = "System requires a Login form. It must have Email and Password fields. Password must be at least 8 characters long and contain numbers."
        
        spec = Specification(id=spec_id, title="Authentication Module", language="EN", created_by=admin_id)
        spec_ver = SpecVersion(specification_id=spec_id, version_number=1, content=content_spec, 
                               embedding=get_embedding(content_spec), created_by=admin_id)
        
        session.add_all([spec, spec_ver])

        # ==========================================
        # 3. TẠO TESTCASES MẪU (Dữ liệu cho AI RAG)
        # ==========================================
        tc1_content = "Verify successful login with valid credentials. Steps: 1. Enter admin@thundersoft.com. 2. Enter admin123. 3. Click Login. Expected: Redirect to Dashboard."
        tc1 = Testcase(title="Login Success Path", description="Valid credentials check", steps="1. Enter email\n2. Enter pass\n3. Submit", 
                       expected_result="Login dashboard appears", status="Locked", test_type="Functional", 
                       embedding=get_embedding(tc1_content), created_by=tester_id)
                       
        tc2_content = "Verify login fails with invalid password. Steps: 1. Enter email. 2. Enter wrong password. 3. Click Login. Expected: Show Error Message."
        tc2 = Testcase(title="Login Invalid Password", description="Check error handling", steps="1. Enter email\n2. Enter wrong pass\n3. Submit", 
                       expected_result="Error message: Invalid bounds", status="Locked", test_type="Negative", 
                       embedding=get_embedding(tc2_content), created_by=tester_id)

        session.add_all([tc1, tc2])

        # ==========================================
        # 4. TẠO DEFECTS MẪU TỪ REDMINE (Cho Analytics)
        # ==========================================
        d1 = Defect(redmine_id=1001, title="Crash when clicking login twice", status="open", severity="critical", model_id="Samsung S23")
        d2 = Defect(redmine_id=1002, title="Login button misaligned", status="resolved", severity="minor", model_id="iPhone 14")
        d3 = Defect(redmine_id=1003, title="Missing forgot password link", status="new", severity="major", model_id="All")
        
        session.add_all([d1, d2, d3])

        await session.commit()
        print("[+] Đã bơm dữ liệu ảo (Specs, Testcases, Defects) thành công!")

if __name__ == "__main__":
    asyncio.run(seed_data())
