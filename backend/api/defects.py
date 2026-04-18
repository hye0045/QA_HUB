from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from core.security import get_current_user
from db.database import get_db
from db.models import Defect

router = APIRouter(prefix="/defects", tags=["Defects"])

class DefectSync(BaseModel):
    redmine_id: int
    title: str
    status: str
    severity: str
    model_id: str = None

from services.redmine_service import RedmineClient
from core.config import settings

@router.get("/")
async def list_defects(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # 1. Kéo dữ liệu tự động (Background Syncing) chạy trên mỗi Request
    client = RedmineClient()
    fresh_defects = await client.fetch_issues(settings.PROJECT_ID)
    
    if fresh_defects:
        for d in fresh_defects:
            result = await db.execute(select(Defect).where(Defect.redmine_id == d["redmine_id"]))
            existing = result.scalars().first()
            if existing:
                # Upsert updating old fields
                existing.title = d["title"]
                existing.status = d["status"]
                existing.severity = d["severity"]
            else:
                # Insert new defect
                new_defect = Defect(
                    redmine_id=d["redmine_id"],
                    title=d["title"],
                    status=d["status"],
                    severity=d["severity"],
                    model_id=d["model_id"]
                )
                db.add(new_defect)
        
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    # 2. Lấy dữ liệu ổn định từ Postgres trả về GUI
    result = await db.execute(select(Defect).order_by(Defect.redmine_id.desc()))
    return result.scalars().all()

@router.post("/sync")
async def sync_defects(
    defects: List[DefectSync], 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # Upsert logic can be complex in generic SQLAlchemy across DBs,
    # so we will do a simple check and update or insert.
    synced_count = 0
    for d in defects:
        result = await db.execute(select(Defect).where(Defect.redmine_id == d.redmine_id))
        existing_defect = result.scalars().first()
        
        if existing_defect:
            existing_defect.title = d.title
            existing_defect.status = d.status
            existing_defect.severity = d.severity
            existing_defect.model_id = d.model_id
        else:
            new_defect = Defect(
                redmine_id=d.redmine_id,
                title=d.title,
                status=d.status,
                severity=d.severity,
                model_id=d.model_id
            )
            db.add(new_defect)
        synced_count += 1
        
    await db.commit()
    return {"message": f"Successfully synced {synced_count} defects"}

@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # 1. Total defects count
    total_res = await db.execute(select(func.count(Defect.id)))
    total_defects = total_res.scalar()
    
    # 2. Defect by Model (GroupBy query)
    model_res = await db.execute(
        select(Defect.model_id, func.count(Defect.id))
        .group_by(Defect.model_id)
    )
    by_model = [{"model": row[0] or "Unknown", "count": row[1]} for row in model_res.all()]
    
    # 3. Defect by Status (GroupBy query)
    status_res = await db.execute(
        select(Defect.status, func.count(Defect.id))
        .group_by(Defect.status)
    )
    by_status = [{"status": row[0], "count": row[1]} for row in status_res.all()]
    
    # [Mock] 4. Defect by Assignee (Giả lập do DB chưa có trường này từ Redmine)
    import random
    mock_assignees = [
        {"name": "Trần Văn Intern", "count": random.randint(5, 15)},
        {"name": "Lê Thị Tester", "count": random.randint(8, 20)},
        {"name": "Nguyễn QA Lead", "count": random.randint(1, 5)},
        {"name": "Unassigned", "count": random.randint(0, 3)}
    ]
    
    return {
        "total": total_defects,
        "by_model": by_model,
        "by_status": by_status,
        "by_assignee": mock_assignees
    }
