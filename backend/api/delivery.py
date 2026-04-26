from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from core.security import get_current_user, require_qa_lead
from db.database import get_db
from db.models import DeliveryDocument, DocStatus, UserRole, MentorAssignment
from services.audit_service import write_audit_log

logger = logging.getLogger("qa_hub.delivery")
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
    """[UC_F3] Intern nộp tài liệu lên Mentor kiểm duyệt."""
    # Validate: chỉ Intern mới được nộp
    if current_user['role'] != 'intern':
        raise HTTPException(status_code=403, detail="Only Interns can submit to Mentor")

    # Validate: Intern phải được phân công mentor
    assign_res = await db.execute(
        select(MentorAssignment).where(
            MentorAssignment.intern_id == uuid.UUID(current_user['id'])
        )
    )
    if not assign_res.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="You must be assigned a Mentor before submitting. Contact QA Lead."
        )

    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft documents can be submitted to Mentor")
    if not doc.mentor_id:
        raise HTTPException(status_code=400, detail="This document does not have an assigned mentor.")

    old_status = doc.status
    doc.status = DocStatus.pending_mentor
    await db.commit()
    logger.info(f"[DELIVERY] doc={doc_id} status={old_status.value}->{doc.status.value} by user={current_user['id']}")
    return {"message": "Document submitted to mentor", "status": doc.status.value}

@router.post("/{doc_id}/approve_mentor")
async def approve_by_mentor(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mentor phê duyệt - chuyển sang pending_qa_lead."""
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocStatus.pending_mentor:
        raise HTTPException(status_code=400, detail="Document is not pending mentor approval")
    if not current_user['is_mentor']:
        raise HTTPException(status_code=403, detail="Only Mentors can approve this stage")

    old_status = doc.status
    doc.status = DocStatus.pending_qa_lead
    await db.commit()
    logger.info(f"[DELIVERY] doc={doc_id} status={old_status.value}->{doc.status.value} by mentor={current_user['id']}")
    return {"message": "Approved by mentor, forwarded to QA Lead", "status": doc.status.value}

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
    """Trả lại tài liệu về draft (Mentor hoặc QA Lead)."""
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status == DocStatus.locked:
        raise HTTPException(status_code=400, detail="Cannot reject a locked document")

    old_status = doc.status
    doc.status = DocStatus.draft
    await db.commit()
    logger.info(f"[DELIVERY] doc={doc_id} REJECTED status={old_status.value}->draft by={current_user['id']}")
    return {"message": "Document rejected and returned to draft", "status": doc.status.value}


@router.post("/{doc_id}/lock", dependencies=[Depends(require_qa_lead)])
async def lock_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """QA Lead khóa tài liệu sau khi đã phê duyệt."""
    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status == DocStatus.locked:
        raise HTTPException(status_code=400, detail="Document is already locked")

    doc.status = DocStatus.locked
    
    await write_audit_log(
        db, current_user['id'],
        action="LOCK_DOCUMENT",
        entity_type="DeliveryDocument",
        entity_id=doc_id
    )
    
    await db.commit()
    return {"message": "Document locked", "status": "locked"}


@router.post("/{doc_id}/unlock", dependencies=[Depends(require_qa_lead)])
async def unlock_document(
    doc_id: str,
    reason: str = Query(..., description="Lý do mở khóa (bắt buộc)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """QA Lead mở khóa tài liệu với lý do bắt buộc."""
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Unlock reason is mandatory")

    result = await db.execute(select(DeliveryDocument).where(DeliveryDocument.id == uuid.UUID(doc_id)))
    doc = result.scalars().first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != DocStatus.locked:
        raise HTTPException(status_code=400, detail="Document is not locked")

    doc.status = DocStatus.draft
    
    await write_audit_log(
        db, current_user['id'],
        action="UNLOCK_DOCUMENT",
        entity_type="DeliveryDocument",
        entity_id=doc_id,
        reason=reason
    )
    
    await db.commit()
    return {"message": "Document unlocked", "status": "draft", "reason": reason}
