from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional
from groq import Groq
import uuid

from core.security import get_current_user
from db.database import get_db
from db.models import ChatHistory, ChatMode, Testcase
from core.config import settings
from services.ai_service import retrieve_top_k_similar, mask_sensitive_data

router = APIRouter(prefix="/chat", tags=["AI Chatbot (Multi-Agent & RAG)"])
client = Groq(api_key=settings.GROQ_API_KEY)
MODEL_NAME = "llama-3.1-70b-versatile"

class ChatRequest(BaseModel):
    mode: str # 'qa', 'translate', 'suggest'
    prompt: str
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None

@router.post("/")
async def chat_endpoint(
    req: ChatRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    # 1. Mask sensitive user info initially (Security Step)
    safe_prompt = mask_sensitive_data(req.prompt)
    
    context = ""
    # 2. Retriever Agent logic (RAG)
    if req.mode in ["qa", "suggest"]:
        # Fetch all testcases to find similar data
        result = await db.execute(select(Testcase.title, Testcase.description, Testcase.steps, Testcase.embedding))
        tcs = result.all()
        
        candidates = []
        for tc in tcs:
            if tc.embedding:
                candidates.append({
                    "title": tc.title,
                    "desc": tc.description,
                    "steps": tc.steps,
                    "embedding": tc.embedding
                })
        
        top_k = retrieve_top_k_similar(safe_prompt, candidates, k=3, threshold=0.2)
        if top_k:
            context = "Context from existing testing database:\n"
            for item in top_k:
                context += f"- Title: {item['title']}. Desc: {item['desc']}. Steps: {item['steps']}\n"
    
    # 3. Agents Routing (Generator/Translator/QA Strategy)
    if req.mode == "qa":
        system_msg = "You are an expert QA Chatbot for Thundersoft. Use the provided Context to accurately answer questions safely."
        user_msg = f"{context}\n\nUser Question: {safe_prompt}"
        
    elif req.mode == "suggest":
        system_msg = "You are a senior QA engineer. Suggest highly effective test cases based on the user's prompt. Do NOT duplicate existing testcases found in the Context."
        user_msg = f"{context}\n\nUser Request: {safe_prompt}"
        
    elif req.mode == "translate":
        src = req.source_lang or "Auto"
        tgt = req.target_lang or "English"
        system_msg = f"You are a professional IT Translator at Thundersoft. Translate from {src} to {tgt}. Provide STRICTLY the translation only, with no commentary."
        user_msg = safe_prompt
        
    else:
        system_msg = "You are a helpful AI assistant."
        user_msg = safe_prompt

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]

    try:
        # 4. Call Groq API
        response = client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,
        )
        ai_reply = response.choices[0].message.content
        
        try:
             chat_mode_enum = ChatMode(req.mode)
        except ValueError:
             chat_mode_enum = ChatMode.qa
             
        # 5. Save History via SQLAlchemy
        history = ChatHistory(
            user_id=uuid.UUID(current_user['id']),
            mode=chat_mode_enum,
            prompt=req.prompt, # Save original safe prompt in history
            response=ai_reply
        )
        db.add(history)
        await db.commit()
        
        return {"response": ai_reply, "mode": req.mode}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

