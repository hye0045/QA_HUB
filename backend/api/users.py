from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import uuid
from typing import List

from db.database import get_db
from core.security import require_qa_lead, get_current_user
from db.models import User, MentorAssignment, UserRole
from services.audit_service import write_audit_log

router = APIRouter(prefix="/users", tags=["Users & Mentorship"])

class AssignMentorRequest(BaseModel):
    mentor_id: str
    intern_id: str

@router.post("/assign-mentor", dependencies=[Depends(require_qa_lead)])
async def assign_mentor(req: AssignMentorRequest, db: AsyncSession = Depends(get_db)):
    """
    [UC_F2] QA Lead gán quyền mentor cho Tester/QA Lead để kèm cặp một Intern.
    """
    try:
        m_id = uuid.UUID(req.mentor_id)
        i_id = uuid.UUID(req.intern_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    # 1. Kiểm tra tồn tại và Role của Mentor
    mentor_res = await db.execute(select(User).where(User.id == m_id))
    mentor = mentor_res.scalars().first()
    if not mentor:
         raise HTTPException(status_code=404, detail="Mentor not found in database")
    if mentor.role not in [UserRole.tester, UserRole.qa_lead, UserRole.admin]:
         raise HTTPException(status_code=400, detail="Assigned mentor must be a Tester or QA Lead")

    # 2. Kiểm tra tồn tại và Role của Intern
    intern_res = await db.execute(select(User).where(User.id == i_id))
    intern = intern_res.scalars().first()
    if not intern:
         raise HTTPException(status_code=404, detail="Intern not found in database")
    if intern.role != UserRole.intern:
         raise HTTPException(status_code=400, detail="Target user is not an Intern")

    # 3. Kiểm tra xem Intern này đã có Mentor chưa (Upsert logic to avoid UniqueViolation)
    assignment_res = await db.execute(select(MentorAssignment).where(MentorAssignment.intern_id == i_id))
    existing_assignment = assignment_res.scalars().first()

    if existing_assignment:
        # Nếu đã có mentor, update sang mentor mới
        existing_assignment.mentor_id = m_id
    else:
        # Nếu chưa có, tạo mới
        new_assignment = MentorAssignment(mentor_id=m_id, intern_id=i_id)
        db.add(new_assignment)

    # 4. Tự động set cờ is_mentor = True cho người đóng vai trò Mentor
    mentor.is_mentor = True

    try:
        await write_audit_log(
            db, current_user['id'],
            action="ASSIGN_MENTOR",
            entity_type="MentorAssignment",
            entity_id=str(i_id),
            reason=f"Mentor: {mentor.email}"
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": f"Successfully assigned {mentor.email} as mentor for {intern.email}"}

@router.get("/{user_id}/mentees")
async def get_mentees(
    user_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Xem một user (Mentor) đang kèm cặp những interns nào.
    Bất kỳ ai đã đăng nhập cũng xem được.
    """
    try:
        u_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    result = await db.execute(
        select(User)
        .join(MentorAssignment, MentorAssignment.intern_id == User.id)
        .where(MentorAssignment.mentor_id == u_id)
    )
    mentees = result.scalars().all()
    
    return [
        {
            "id": str(m.id),
            "email": m.email,
            "full_name": m.full_name,
            "role": m.role.value
        } for m in mentees
    ]

# --- Admin Operations (CRUD Users) ---
from db.models import RoleDelegation
from core.security import require_admin

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str

@router.get("/", dependencies=[Depends(require_admin)])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_mentor": u.is_mentor} for u in users]

@router.post("/", dependencies=[Depends(require_admin)])
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    from core.security import get_password_hash
    # Check if exists
    res = await db.execute(select(User).where(User.email == user.email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        role=UserRole(user.role),
        password_hash=get_password_hash(user.password)
    )
    db.add(new_user)
    await db.commit()
    return {"message": "User created successfully"}

@router.delete("/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}

# --- QA_LEAD Operations (Delegate) ---
class DelegateRequest(BaseModel):
    tester_id: str
    duration_hours: int

@router.post("/delegate", dependencies=[Depends(require_qa_lead)])
async def create_delegation(req: DelegateRequest, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from datetime import datetime, timedelta
    
    tester_id_uuid = uuid.UUID(req.tester_id)
    
    # Veryify tester
    res = await db.execute(select(User).where(User.id == tester_id_uuid))
    tester = res.scalars().first()
    if not tester or tester.role != UserRole.tester:
        raise HTTPException(status_code=400, detail="Target user is not a valid tester.")
        
    expires = datetime.utcnow() + timedelta(hours=req.duration_hours)
    
    delegation = RoleDelegation(
        delegator_id=uuid.UUID(current_user["id"]),
        delegatee_id=tester_id_uuid,
        expires_at=expires
    )
    db.add(delegation)
    
    await write_audit_log(
        db, current_user['id'],
        action="CREATE_DELEGATION",
        entity_type="RoleDelegation",
        entity_id=str(tester_id_uuid),
        reason=f"Duration: {req.duration_hours}h"
    )
    
    await db.commit()
    return {"message": f"Successfully delegated Final Approve to {tester.email} for {req.duration_hours} hours."}
