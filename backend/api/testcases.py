from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional, List
import uuid

from core.security import get_current_user, require_tester
from db.database import get_db
from db.models import Testcase

router = APIRouter(prefix="/testcases", tags=["Testcases"])

class TestcaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    steps: Optional[str] = None
    expected_result: Optional[str] = None
    status: Optional[str] = "Draft"
    model_id: Optional[str] = None
    test_type: Optional[str] = None
    precondition: Optional[str] = None

@router.get("/")
async def list_testcases(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Testcase).order_by(Testcase.created_at.desc()))
    tcs = result.scalars().all()
    return tcs

@router.post("/", dependencies=[Depends(require_tester)])
async def create_testcase(
    tc: TestcaseCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    from services.ai_service import get_embedding
    
    # Combine content for embedding
    combined_content = f"{tc.title}. {tc.description or ''}. Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    embedding_vector = get_embedding(combined_content)

    new_tc = Testcase(
        title=tc.title,
        description=tc.description,
        steps=tc.steps,
        expected_result=tc.expected_result,
        status=tc.status,
        model_id=tc.model_id,
        test_type=tc.test_type,
        precondition=tc.precondition,
        embedding=embedding_vector if embedding_vector else None,
        created_by=uuid.UUID(current_user['id'])
    )
    db.add(new_tc)
    await db.commit()
    await db.refresh(new_tc)
    
    return {"message": "Testcase created successfully", "id": new_tc.id}

@router.put("/{tc_id}", dependencies=[Depends(require_tester)])
async def update_testcase(
    tc_id: str, 
    tc: TestcaseCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Testcase).where(Testcase.id == uuid.UUID(tc_id)))
    existing_tc = result.scalars().first()
    
    if not existing_tc:
        raise HTTPException(status_code=404, detail="Testcase not found")
        
    existing_tc.title = tc.title
    existing_tc.description = tc.description
    existing_tc.steps = tc.steps
    existing_tc.expected_result = tc.expected_result
    existing_tc.status = tc.status
    existing_tc.model_id = tc.model_id
    existing_tc.test_type = tc.test_type
    existing_tc.precondition = tc.precondition
    
    from services.ai_service import get_embedding
    combined_content = f"{tc.title}. {tc.description or ''}. Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    embedding_vector = get_embedding(combined_content)
    existing_tc.embedding = embedding_vector if embedding_vector else None
    
    # If the user manually edits the testcase, reset `is_affected`
    existing_tc.is_affected = False

    await db.commit()
    return {"message": "Testcase updated successfully"}

@router.delete("/{tc_id}", dependencies=[Depends(require_tester)])
async def delete_testcase(
    tc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Testcase).where(Testcase.id == uuid.UUID(tc_id)))
    tc = result.scalars().first()
    
    if not tc:
        raise HTTPException(status_code=404, detail="Testcase not found")
        
    await db.delete(tc)
    await db.commit()
    return {"message": "Testcase deleted successfully"}

@router.get("/{tc_id}")
async def get_testcase(
    tc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Testcase).where(Testcase.id == uuid.UUID(tc_id)))
    tc = result.scalars().first()
    if not tc:
         raise HTTPException(status_code=404, detail="Testcase not found")
    return tc
