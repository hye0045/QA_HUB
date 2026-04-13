from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import difflib
from core.security import get_current_user
from db.supabase_client import supabase

router = APIRouter(prefix="/specs", tags=["Specifications"])

class SpecSync(BaseModel):
    title: str
    language: str
    content: str
    version_number: int

@router.get("/")
def list_specs(current_user: dict = Depends(get_current_user)):
    # Fetch all specs and their latest version content
    specs_res = supabase.table("specification").select("id, title, language, created_at").execute()
    data = specs_res.data
    
    # We will fetch latest versions for simplicity
    for s in data:
        ver = supabase.table("spec_version").select("version_number, content").eq("specification_id", s['id']).order("version_number", desc=True).limit(1).execute()
        if ver.data:
            s['latest_version'] = ver.data[0]['version_number']
            s['content'] = ver.data[0]['content']
        else:
            s['latest_version'] = 0
            s['content'] = ""

    return data

@router.post("/sync")
def sync_spec(spec: SpecSync, current_user: dict = Depends(get_current_user)):
    # Look for existing spec by title
    existing_spec = supabase.table("specification").select("*").eq("title", spec.title).execute()
    
    if existing_spec.data:
        spec_id = existing_spec.data[0]['id']
    else:
        new_spec = supabase.table("specification").insert({
            "title": spec.title,
            "language": spec.language,
            "created_by": current_user['id']
        }).execute()
        spec_id = new_spec.data[0]['id']
        
    # Check if this version exists
    existing_version = supabase.table("spec_version").select("*").eq("specification_id", spec_id).eq("version_number", spec.version_number).execute()
    if existing_version.data:
        return {"message": "Version already exists", "spec_id": spec_id}

    # Insert new version
    supabase.table("spec_version").insert({
        "specification_id": spec_id,
        "version_number": spec.version_number,
        "content": spec.content,
        "created_by": current_user['id']
        # Note: Embedding is handled asynchronously or here if Groq/OpenAI is called immediately
    }).execute()
    
    return {"message": "Spec synced successfully", "spec_id": spec_id}

@router.get("/{spec_id}/diff")
def spec_diff(spec_id: str, v1: int, v2: int, current_user: dict = Depends(get_current_user)):
    # Fetch both versions
    ver1 = supabase.table("spec_version").select("content").eq("specification_id", spec_id).eq("version_number", v1).single().execute()
    ver2 = supabase.table("spec_version").select("content").eq("specification_id", spec_id).eq("version_number", v2).single().execute()
    
    if not ver1.data or not ver2.data:
        raise HTTPException(status_code=404, detail="One or both versions not found")
        
    text1 = ver1.data['content'].splitlines(keepends=True)
    text2 = ver2.data['content'].splitlines(keepends=True)
    
    # Generate unified diff
    diff = list(difflib.unified_diff(text1, text2, fromfile=f'v{v1}', tofile=f'v{v2}'))
    
    return {"diff": "".join(diff)}

