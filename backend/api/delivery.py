from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from core.security import get_current_user, require_tester, require_qa_lead
from db.supabase_client import supabase

router = APIRouter(prefix="/delivery", tags=["DeliveryDocuments"])

class DeliveryCreate(BaseModel):
    title: str
    content: str
    mentor_id: str = None

class ActionReason(BaseModel):
    reason: str

@router.post("/")
def create_draft(doc: DeliveryCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    role = current_user['role']
    
    if role == 'intern' and not doc.mentor_id:
        raise HTTPException(status_code=400, detail="Interns must provide a mentor_id")
        
    inserted = supabase.table("delivery_document").insert({
        "title": doc.title,
        "status": "draft",
        "created_by": user_id,
        "mentor_id": doc.mentor_id
    }).execute()
    
    doc_id = inserted.data[0]['id']
    
    supabase.table("delivery_version").insert({
        "delivery_document_id": doc_id,
        "content": doc.content,
        "created_by": user_id
    }).execute()
    
    return inserted.data[0]

@router.put("/{doc_id}/approve")
def approve_doc(doc_id: str, current_user: dict = Depends(get_current_user)):
    # Must be mentor, QA lead, or admin
    doc = supabase.table("delivery_document").select("*").eq("id", doc_id).single().execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")
        
    user_id = current_user['id']
    d = doc.data
    
    if current_user['role'] == 'intern':
         raise HTTPException(status_code=403, detail="Interns cannot approve")
         
    if d['status'] == 'locked':
         raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Document is locked")
         
    # Update status
    new_status = 'approved'
    if current_user['role'] == 'tester' and d['mentor_id'] == user_id:
        new_status = 'mentor_reviewed' # Step 1 of approval
        
    supabase.table("delivery_document").update({"status": new_status}).eq("id", doc_id).execute()
    return {"message": "Document updated", "new_status": new_status}

@router.put("/{doc_id}/lock")
def lock_doc(doc_id: str, payload: ActionReason, current_user: dict = Depends(require_qa_lead)):
    # Lock document (HTTP 423 enforcement on edits)
    supabase.table("delivery_document").update({"status": "locked"}).eq("id", doc_id).execute()
    
    # Audit trail
    supabase.table("audit_log").insert({
        "user_id": current_user['id'],
        "action": "lock",
        "entity_type": "delivery_document",
        "entity_id": doc_id,
        "reason": payload.reason
    }).execute()
    
    return {"message": "Document locked"}
