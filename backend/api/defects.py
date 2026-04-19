from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel

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
    """Lấy danh sách Defect từ DB (không tự động sync Redmine mỗi lần gọi)."""
    result = await db.execute(select(Defect).order_by(Defect.redmine_id.desc()))
    return result.scalars().all()


from services.ai_service import clean_and_classify_bug

from db.models import DeviceModelProfile
import uuid

class ModelProfileCreate(BaseModel):
    name: str
    project_id: str
    tracker_id: int = 38

@router.get("/profiles")
async def get_model_profiles(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(DeviceModelProfile).order_by(DeviceModelProfile.created_at.desc()))
    return res.scalars().all()

@router.post("/profiles")
async def create_model_profile(profile: ModelProfileCreate, db: AsyncSession = Depends(get_db)):
    new_profile = DeviceModelProfile(
        name=profile.name,
        project_id=profile.project_id,
        tracker_id=profile.tracker_id
    )
    db.add(new_profile)
    await db.commit()
    return {"message": "Profile created successfully"}

class SyncRequest(BaseModel):
    profile_id: str

@router.post("/sync")
async def sync_defects(
    req: SyncRequest,
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    """
    Gọi thực tế Redmine API lấy Bug, lưu DB theo Profile ID.
    """
    res = await db.execute(select(DeviceModelProfile).where(DeviceModelProfile.id == uuid.UUID(req.profile_id)))
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Device Config Not Found")

    from services.redmine_service import RedmineClient
    client = RedmineClient()
    
    redmine_bugs = await client.fetch_issues(project_id=profile.project_id, tracker_id=profile.tracker_id)
    
    if not redmine_bugs:
        return {"message": "Không tìm thấy Bug nào mới từ Redmine hoặc có lỗi kết nối."}

    synced_count = 0
    for d in redmine_bugs:
        # 2. Gọi AI Classify
        ai_result = await clean_and_classify_bug(d["title"], d.get("description", ""))
        
        # 3. Lưu vào Database
        result = await db.execute(select(Defect).where(Defect.redmine_id == d["redmine_id"]))
        existing_defect = result.scalars().first()
        
        if existing_defect:
            existing_defect.title = d["title"]
            existing_defect.status = d["status"]
            existing_defect.severity = d["severity"]
            existing_defect.model_id = profile.name
            existing_defect.cleaned_description = ai_result.get("cleaned_description")
            existing_defect.bug_category = ai_result.get("bug_category")
            existing_defect.root_cause_guess = ai_result.get("root_cause_guess")
            existing_defect.module = ai_result.get("module")
        else:
            new_defect = Defect(
                redmine_id=d["redmine_id"],
                title=d["title"],
                status=d["status"],
                severity=d["severity"],
                model_id=profile.name,
                cleaned_description=ai_result.get("cleaned_description"),
                bug_category=ai_result.get("bug_category"),
                root_cause_guess=ai_result.get("root_cause_guess"),
                module=ai_result.get("module")
            )
            db.add(new_defect)
        synced_count += 1
        
    await db.commit()
    return {"message": f"Successfully synced and classified {synced_count} defects"}

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
    
    # 4. Defect by Category (for AI Analytics)
    category_res = await db.execute(
        select(Defect.bug_category, func.count(Defect.id))
        .group_by(Defect.bug_category)
    )
    by_category = [{"category": row[0] or "Uncategorized", "count": row[1]} for row in category_res.all()]

    # [Mock] 5. Defect by Assignee (Giả lập do DB chưa có trường này từ Redmine)
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
        "by_category": by_category,
        "by_assignee": mock_assignees
    }
