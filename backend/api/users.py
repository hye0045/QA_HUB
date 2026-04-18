from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import uuid
from typing import List

from db.database import get_db
from core.security import require_qa_lead, get_current_user
from db.models import User, MentorAssignment, UserRole

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
