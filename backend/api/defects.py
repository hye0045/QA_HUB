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

@router.get("/")
async def list_defects(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
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
    
    return {
        "total": total_defects,
        "by_model": by_model,
        "by_status": by_status
    }
