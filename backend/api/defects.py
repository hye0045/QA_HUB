from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from core.security import get_current_user
from db.supabase_client import supabase

router = APIRouter(prefix="/defects", tags=["Defects"])

class DefectSync(BaseModel):
    redmine_id: int
    title: str
    status: str
    severity: str
    model_id: str

@router.get("/")
def list_defects(current_user: dict = Depends(get_current_user)):
    res = supabase.table("defect").select("*").order("synced_at", desc=True).limit(50).execute()
    return res.data

@router.post("/sync")
def sync_defects(defects: List[DefectSync], current_user: dict = Depends(get_current_user)):
    for defect in defects:
        existing = supabase.table("defect").select("*").eq("redmine_id", defect.redmine_id).execute()
        
        if existing.data:
            # Update and add history
            d = existing.data[0]
            if d['status'] != defect.status:
                supabase.table("defect").update({
                    "status": defect.status,
                    "synced_at": "now()"
                }).eq("id", d['id']).execute()
                
                supabase.table("defect_history").insert({
                    "defect_id": d['id'],
                    "status": defect.status
                }).execute()
        else:
            # Insert new
            inserted = supabase.table("defect").insert({
                "redmine_id": defect.redmine_id,
                "title": defect.title,
                "status": defect.status,
                "severity": defect.severity,
                "model_id": defect.model_id
            }).execute()
            
            supabase.table("defect_history").insert({
                "defect_id": inserted.data[0]['id'],
                "status": defect.status
            }).execute()
            
    return {"message": f"{len(defects)} defects synced"}

@router.get("/analytics")
def defects_analytics(current_user: dict = Depends(get_current_user)):
    # Basic aggregation
    res = supabase.table("defect").select("status, severity, model_id").execute()
    data = res.data
    
    # Grouping logic
    analytics = {
        "by_status": {},
        "by_severity": {},
        "by_model": {}
    }
    
    for d in data:
        st = d['status']
        sev = d['severity']
        mod = d['model_id']
        
        analytics["by_status"][st] = analytics["by_status"].get(st, 0) + 1
        analytics["by_severity"][sev] = analytics["by_severity"].get(sev, 0) + 1
        analytics["by_model"][mod] = analytics["by_model"].get(mod, 0) + 1
        
    return analytics

