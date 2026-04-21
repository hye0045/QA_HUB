from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional, List
import uuid
import logging

from core.security import get_current_user, require_tester
from db.database import get_db
from db.models import Testcase

logger = logging.getLogger("qa_hub.testcases")
router = APIRouter(prefix="/testcases", tags=["Testcases"])


# -------------------------------------------------------------------
# Pydantic schemas
# -------------------------------------------------------------------
class TestcaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    steps: Optional[str] = None
    expected_result: Optional[str] = None
    status: Optional[str] = "draft"       # draft | active | deprecated
    model_id: Optional[str] = None
    test_type: Optional[str] = None
    precondition: Optional[str] = None


# -------------------------------------------------------------------
# CRUD Endpoints
# -------------------------------------------------------------------
@router.get("/")
async def list_testcases(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Testcase).order_by(Testcase.created_at.desc()))
    return result.scalars().all()


@router.post("/", dependencies=[Depends(require_tester)])
async def create_testcase(
    tc: TestcaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from services.ai_service import get_embedding

    combined_content = (
        f"{tc.title}. {tc.description or ''}. "
        f"Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    )
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

    logger.info(f"[TESTCASE] CREATED id={new_tc.id} title='{tc.title}' by={current_user['id']}")
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
    existing_tc.is_affected = False  # Reset khi user tự sửa

    from services.ai_service import get_embedding
    combined_content = (
        f"{tc.title}. {tc.description or ''}. "
        f"Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    )
    existing_tc.embedding = get_embedding(combined_content) or None

    await db.commit()
    logger.info(f"[TESTCASE] UPDATED id={tc_id} by={current_user['id']}")
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
    logger.info(f"[TESTCASE] DELETED id={tc_id} by={current_user['id']}")
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


# -------------------------------------------------------------------
# AI Suggest Endpoint (RAG)
# -------------------------------------------------------------------
@router.post("/ai-suggest")
async def suggest_testcase(
    prompt: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """[AI] Gợi ý Testcase dựa trên RAG từ các Testcase Active trong hệ thống."""
    from services.ai_service import get_embedding, retrieve_top_k_similar
    from core.config import settings

    # Lấy toàn bộ testcase Active có embedding
    result = await db.execute(
        select(Testcase).where(
            Testcase.status == "active",
            Testcase.embedding.isnot(None)
        )
    )
    active_tcs = result.scalars().all()

    candidates = [
        {
            "title": tc.title,
            "description": tc.description or "",
            "steps": tc.steps or "",
            "embedding": tc.embedding
        }
        for tc in active_tcs
    ]

    # RAG: semantic search để tìm testcase tương tự
    similar = retrieve_top_k_similar(prompt, candidates, k=3, threshold=0.2) if candidates else []

    context_text = ""
    if similar:
        context_text = "Similar existing testcases (do NOT duplicate these):\n"
        for item in similar:
            context_text += f"- {item['title']}: {item.get('description', '')}\n"

    # Gọi Ollama AI để sinh gợi ý
    try:
        from services.ai_service import call_llm
        system_msg = (
            "You are a senior QA engineer at Thundersoft. "
            "Suggest effective, clear test cases. "
            "Do NOT duplicate existing testcases from context."
        )
        user_msg = f"{context_text}\n\nFeature to test: {prompt}"
        suggestion = await call_llm(user_msg, system_prompt=system_msg)
    except Exception as e:
        logger.error(f"[AI SUGGEST] Ollama call failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {str(e)}")

    return {
        "suggestion": suggestion,
        "similar_testcases": similar,
    }


class GenerateTestcaseRequest(BaseModel):
    spec_text: str
    base_model: str

@router.post("/generate")
async def generate_testcases_from_spec_endpoint(
    req: GenerateTestcaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """[AI] Tự động sinh hàng loạt Testcase từ tài liệu Spec kết hợp RAG model"""
    from services.ai_service import generate_testcases_from_spec
    
    # Mock behavior: lấy 1-2 testcases mẫu từ base_model
    # Trong thực tế: result = await db.execute(select(Testcase).where(Testcase.model_id == req.base_model).limit(2))
    base_tcs = []
    result = await db.execute(
        select(Testcase)
        .where(Testcase.status == "active")
        .limit(2)
    )
    for tc in result.scalars().all():
        base_tcs.append({
            "title": tc.title,
            "precondition": tc.precondition or "",
            "steps": tc.steps or "",
            "expected": tc.expected_result or ""
        })

    # Nếu không có mẫu, tạo 1 mẫu cứng làm base prompt
    if not base_tcs:
        base_tcs = [{
            "title": "Kiểm tra màn hình hiển thị",
            "precondition": "Thiết bị được bật nguồn.",
            "steps": "1. Mở ứng dụng.\n2. Quan sát màn hình chính.",
            "expected": "Màn hình chính hiển thị đầy đủ icon không bị vỡ layout."
        }]

    ai_response = await generate_testcases_from_spec(req.spec_text, base_tcs)
    
    return ai_response
