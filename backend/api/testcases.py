from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
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
    from fastapi.concurrency import run_in_threadpool
    from services.ai_service import get_embedding

    combined_content = (
        f"{tc.title}. {tc.description or ''}. "
        f"Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    )
    embedding_vector = await run_in_threadpool(get_embedding, combined_content)

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

    from fastapi.concurrency import run_in_threadpool
    from services.ai_service import get_embedding
    combined_content = (
        f"{tc.title}. {tc.description or ''}. "
        f"Steps: {tc.steps or ''}. Expected: {tc.expected_result or ''}"
    )
    existing_tc.embedding = await run_in_threadpool(get_embedding, combined_content) or None

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


class RagGenerateRequest(BaseModel):
    spec_text: str               # Spec của dòng máy mới (paste text hoặc lấy từ SpecVersion)
    base_model_name: str         # Tên dòng máy gốc (VD: "Samsung S24")
    new_model_name: str          # Tên dòng máy mới cần sinh TC (VD: "Samsung S25")
    spec_id: Optional[str] = None  # Nếu có, tự lấy content từ SpecVersion mới nhất
    spec_version: Optional[int] = None
    tc_k: int = 5
    bug_k: int = 5
    base_tc_override: Optional[List[dict]] = None

class SaveGeneratedTCsRequest(BaseModel):
    model_id: str
    tc_type: str = "functional"
    testcases: List[dict]


@router.post("/upload-base-for-rag")
async def upload_base_testcases_for_rag(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload file Excel làm TC Base Model tạm thời (không lưu vào DB).
    Trả về list TC để dùng ngay trong RAG generation.
    Dùng khi base model chưa có TC trong DB.
    """
    import openpyxl, io

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .xlsx/.xls")

    contents = await file.read()
    wb = openpyxl.load_workbook(filename=io.BytesIO(contents), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        raise HTTPException(status_code=400, detail="File trống")

    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    if "title" not in headers:
        raise HTTPException(status_code=400, detail=f"Thiếu cột 'title'. Cột hiện có: {headers}")

    tcs = []
    for row in rows[1:]:
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        title = str(row_dict.get("title") or "").strip()
        if not title:
            continue
        tcs.append({
            "title": title,
            "precondition": str(row_dict.get("precondition") or ""),
            "steps": str(row_dict.get("steps") or ""),
            "expected_result": str(row_dict.get("expected_result") or ""),
        })

    return {"testcases": tcs, "count": len(tcs)}


@router.post("/generate-from-base-model")
async def generate_testcases_from_base_model(
    req: RagGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    [AI + RAG] Sinh Testcase cho dòng máy mới dựa trên:
      1. Spec của dòng máy mới (text hoặc spec_id)
      2. Testcase Active của base_model_name (học văn phong + coverage)
      3. Defect history của base_model_name (sinh bug-list TC)

    Output JSON:
    {
      "functional": [{id, title, precondition, steps, expected_result}],
      "bug_list":   [{id, title, precondition, steps, expected_result, ref_bug}],
      "_meta": {base_model, new_model, similar_tcs_found, similar_bugs_found}
    }
    """
    from services.rag_service import generate_testcases_rag
    from db.models import SpecVersion, Specification

    # Nếu có spec_id, lấy content từ phiên bản mới nhất
    spec_text = req.spec_text
    if req.spec_id and not spec_text.strip():
        try:
            spec_uuid = uuid.UUID(req.spec_id)
            stmt = select(SpecVersion).where(SpecVersion.specification_id == spec_uuid)
            if req.spec_version:
                stmt = stmt.where(SpecVersion.version_number == req.spec_version)
            else:
                stmt = stmt.order_by(SpecVersion.version_number.desc()).limit(1)
                
            ver_res = await db.execute(stmt)
            ver = ver_res.scalars().first()
            if ver:
                spec_text = ver.content
        except Exception as e:
            logger.warning(f"[TC GENERATE] Không lấy được spec_id: {e}")

    if not spec_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Cần cung cấp spec_text hoặc spec_id hợp lệ có content."
        )

    try:
        result = await generate_testcases_rag(
            db=db,
            spec_text=spec_text,
            base_model_name=req.base_model_name,
            new_model_name=req.new_model_name,
            tc_k=req.tc_k,
            bug_k=req.bug_k,
            base_tc_override=req.base_tc_override,
        )
        logger.info(
            f"[TC GENERATE RAG] user={current_user['id']} "
            f"base={req.base_model_name} → new={req.new_model_name} "
            f"functional={len(result.get('functional', []))} "
            f"bug_list={len(result.get('bug_list', []))}"
        )
        return result
    except RuntimeError as e:
        # Ollama không chạy hoặc model chưa có
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"[TC GENERATE RAG] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-from-base-model/save")
async def save_generated_testcases(
    req: SaveGeneratedTCsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lưu hàng loạt TC đã được AI sinh (sau khi Tester review và chọn).
    tc_type = 'bug_list' → tự động set test_type = 'regression'
    """
    from fastapi.concurrency import run_in_threadpool
    from services.ai_service import get_embedding

    created_ids = []
    for tc_data in req.testcases:
        combined = (
            f"{tc_data.get('title', '')}. "
            f"{tc_data.get('steps', '')}. "
            f"Expected: {tc_data.get('expected_result', '')}"
        )
        emb = await run_in_threadpool(get_embedding, combined)

        new_tc = Testcase(
            title=tc_data.get("title", ""),
            description=tc_data.get("ref_bug", "") if req.tc_type == "bug_list" else "",
            steps=tc_data.get("steps", ""),
            expected_result=tc_data.get("expected_result", ""),
            precondition=tc_data.get("precondition", ""),
            model_id=req.model_id,
            test_type="regression" if req.tc_type == "bug_list" else "functional",
            status="draft",
            embedding=emb if emb else None,
            created_by=uuid.UUID(current_user["id"])
        )
        db.add(new_tc)
        await db.flush()
        created_ids.append(str(new_tc.id))

    await db.commit()
    logger.info(f"[TC SAVE RAG] Saved {len(created_ids)} {req.tc_type} TCs for model={req.model_id}")
    return {"message": f"Đã lưu {len(created_ids)} testcase", "ids": created_ids}