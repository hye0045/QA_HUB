from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import uuid

from core.security import get_current_user
from db.database import get_db
from db.models import DeliveryDocument, DocStatus, UserRole

router = APIRouter(prefix="/delivery", tags=["Delivery Workflow"])

class DeliveryCreate(BaseModel):
    title: str

@router.get("/")
async def list_deliveries(
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(DeliveryDocument))
    return result.scalars().all()

@router.post("/")
async def create_delivery(
    doc: DeliveryCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    new_doc = DeliveryDocument(
        title=doc.title,
        status=DocStatus.draft,
        created_by=uuid.UUID(current_user['id'])
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return {"message": "Document drafted", "id": new_doc.id}

@router.post("/{doc_id}/submit_to_mentor")
async def submit_to_mentor(
    doc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status != DocStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft documents can be submitted to Mentor")
        
    if not doc.mentor_id:
        raise HTTPException(status_code=400, detail="This document does not have an assigned mentor. Please assign a mentor first.")
        
    doc.status = DocStatus.pending_mentor
    await db.commit()
    return {"message": "Document submitted to mentor", "status": doc.status.value}

@router.post("/{doc_id}/approve_mentor")
async def approve_by_mentor(
    doc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status != DocStatus.pending_mentor:
        raise HTTPException(status_code=400, detail="Document is not pending mentor approval")
        
    if not current_user['is_mentor']:
        raise HTTPException(status_code=403, detail="Only Mentors can approve this stage")
        
    doc.status = DocStatus.pending_qa_lead
    await db.commit()
    return {"message": "Document approved by mentor and forwarded to QA Lead", "status": doc.status.value}

@router.post("/{doc_id}/approve_lead")
async def approve_by_lead(
    doc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status != DocStatus.pending_qa_lead:
        raise HTTPException(status_code=400, detail="Document is not pending QA Lead approval")
        
    if current_user['role'] not in [UserRole.qa_lead.value, UserRole.admin.value]:
        raise HTTPException(status_code=403, detail="Only QA Leads or Admins can lock documents")
        
    doc.status = DocStatus.locked
    await db.commit()
    return {"message": "Document Approved and Locked", "status": doc.status.value}

@router.post("/{doc_id}/reject")
async def reject_document(
    doc_id: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if doc.status == DocStatus.locked:
        raise HTTPException(status_code=400, detail="Cannot reject a locked document")
        
    doc.status = DocStatus.draft
    await db.commit()
    return {"message": "Document rejected and returned to draft", "status": doc.status.value}
