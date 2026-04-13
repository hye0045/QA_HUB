from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import httpx
from core.security import get_current_user
from db.supabase_client import supabase
from core.config import settings
from groq import Groq

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

client = Groq(api_key=settings.GROQ_API_KEY)
MODEL_NAME = "llama-3.1-70b-versatile" # Adjust as needed (e.g. mixstral, llama3)

class ChatRequest(BaseModel):
    mode: str # 'qa', 'translate', 'suggest'
    prompt: str
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    model_id: Optional[str] = None # used for context in suggest mode

def get_system_prompt(req: ChatRequest, context: str = "") -> str:
    if req.mode == "qa":
        return "You are an expert QA Chatbot. Answer the user's questions regarding testing and QA processes clearly."
    elif req.mode == "translate":
        src = req.source_lang or "Auto"
        tgt = req.target_lang or "English"
        return f"You are a professional translator. Translate the following text from {src} to {tgt}. Provide only the translation."
    elif req.mode == "suggest":
        base = "You are a senior QA engineer. Suggest test cases based on the user's prompt."
        if context:
            base += f"\nHere is context of existing testcases to avoid duplication:\n{context}"
        return base
    else:
        return "You are a helpful AI assistant."

@router.post("/")
def chat_endpoint(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user['id']
    
    context = ""
    # In 'suggest' mode, optionally fetch similar testcases using pgvector
    if req.mode == "suggest":
        # In a real scenario, convert req.prompt to embedding first, then rpc('match_testcases')
        # Here we simulate fetching existing testcase titles as context
        res = supabase.table("testcase").select("title, description").limit(5).execute()
        if res.data:
            context = "\n".join([f"- {t['title']}: {t['description']}" for t in res.data])

    system_prompt = get_system_prompt(req, context)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.prompt}
    ]

    try:
        response = client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,
        )
        ai_reply = response.choices[0].message.content
        
        # Save to chat history
        supabase.table("chat_history").insert({
            "user_id": user_id,
            "mode": req.mode,
            "prompt": req.prompt,
            "response": ai_reply
        }).execute()
        
        return {"response": ai_reply, "mode": req.mode}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
