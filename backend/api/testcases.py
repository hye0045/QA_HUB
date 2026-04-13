from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from core.security import get_current_user, require_tester
from core.rate_limit import check_rate_limit
from db.supabase_client import supabase

router = APIRouter(prefix="/testcases", tags=["Testcases"])

class TestcaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    steps: Optional[str] = None
    expected_result: Optional[str] = None
    spec_ids: Optional[List[str]] = [] # For testcase_spec_link

@router.get("/")
def list_testcases(current_user: dict = Depends(check_rate_limit("fetch_testcase"))):
    data = supabase.table("testcase").select("*").execute()
    return data.data

@router.post("/")
def create_testcase(testcase: TestcaseCreate, current_user: dict = Depends(require_tester)):
    user_id = current_user['id']
    inserted = supabase.table("testcase").insert({
        "title": testcase.title,
        "description": testcase.description,
        "steps": testcase.steps,
        "expected_result": testcase.expected_result,
        "created_by": user_id
    }).execute()
    
    new_testcase = inserted.data[0]
    
    if testcase.spec_ids:
        links = [{"testcase_id": new_testcase['id'], "specification_id": sid} for sid in testcase.spec_ids]
        supabase.table("testcase_spec_link").insert(links).execute()
        
    return new_testcase

@router.get("/{testcase_id}")
def get_testcase(testcase_id: str, current_user: dict = Depends(get_current_user)):
    data = supabase.table("testcase").select("*").eq("id", testcase_id).single().execute()
    if not data.data:
         raise HTTPException(status_code=404, detail="Testcase not found")
    return data.data

@router.put("/{testcase_id}")
def update_testcase(testcase_id: str, testcase: TestcaseCreate, current_user: dict = Depends(require_tester)):
    updated = supabase.table("testcase").update({
        "title": testcase.title,
        "description": testcase.description,
        "steps": testcase.steps,
        "expected_result": testcase.expected_result,
    }).eq("id", testcase_id).execute()
    return updated.data[0]
