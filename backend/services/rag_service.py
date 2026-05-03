"""
services/rag_service.py
RAG pipeline cho sinh Testcase từ Base Model.
Hai luồng:
  A) Functional TC  → cosine similarity trên Testcase.embedding của base_model
  B) Bug-list TC    → cosine similarity trên Defect.embedding của base_model
"""
import json
import logging
from typing import List, Dict, Any

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Testcase, Defect
from services.ai_service import get_embedding, cosine_similarity, call_llm, mask_sensitive_data

logger = logging.getLogger("qa_hub.rag_service")


def _retrieve_top_k(
    query_vec: List[float],
    candidates: List[Dict],   # mỗi phần tử có key "embedding" và "text"
    k: int = 5,
    threshold: float = 0.25
) -> List[str]:
    if not query_vec or not candidates:
        return []
    scored = []
    for cand in candidates:
        emb = cand.get("embedding")
        if emb:
            sim = cosine_similarity(query_vec, emb)
            if sim >= threshold:
                scored.append((sim, cand["text"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:k]]


async def retrieve_similar_testcases(
    db: AsyncSession,
    spec_text: str,
    base_model_name: str,
    k: int = 5,
    threshold: float = 0.25
) -> List[str]:
    """Luồng A: Lấy TC của base_model gần nhất với spec_text mới."""
    query_vec = await run_in_threadpool(get_embedding, spec_text[:2000])
    if not query_vec:
        return []

    result = await db.execute(
        select(Testcase).where(
            Testcase.model_id == base_model_name,
            Testcase.status == "active",
            Testcase.embedding.isnot(None)
        ).limit(200)
    )
    base_tcs = result.scalars().all()

    candidates = []
    for tc in base_tcs:
        candidates.append({
            "embedding": tc.embedding,
            "text": (
                f"Title: {tc.title}\n"
                f"Precondition: {tc.precondition or ''}\n"
                f"Steps: {tc.steps or ''}\n"
                f"Expected: {tc.expected_result or ''}"
            )
        })
    return _retrieve_top_k(query_vec, candidates, k=k, threshold=threshold)


async def retrieve_similar_defects(
    db: AsyncSession,
    spec_text: str,
    base_model_name: str,
    k: int = 5,
    threshold: float = 0.20
) -> List[str]:
    """Luồng B: Lấy Defect của base_model liên quan đến spec_text."""
    query_vec = await run_in_threadpool(get_embedding, spec_text[:2000])
    if not query_vec:
        return []

    result = await db.execute(
        select(Defect).where(
            Defect.model_id == base_model_name,
            Defect.bug_category.isnot(None),
            Defect.embedding.isnot(None)   # ← chỉ lấy defect đã có embedding
        ).limit(300)
    )
    defects = result.scalars().all()

    if not defects:
        # Fallback: nếu chưa có embedding, generate realtime (chậm hơn)
        result2 = await db.execute(
            select(Defect).where(
                Defect.model_id == base_model_name,
                Defect.bug_category.isnot(None)
            ).limit(100)
        )
        defects = result2.scalars().all()
        candidates = []
        for d in defects:
            embed_text = f"{d.title}. {d.cleaned_description or ''}. Module: {d.module or ''}"
            emb = await run_in_threadpool(get_embedding, embed_text[:500])
            if emb:
                candidates.append({
                    "embedding": emb,
                    "text": (
                        f"Bug: {d.title}\n"
                        f"Category: {d.bug_category}\n"
                        f"Root cause: {d.root_cause_guess or 'Unknown'}\n"
                        f"Module: {d.module or 'Unknown'}"
                    )
                })
    else:
        candidates = [
            {
                "embedding": d.embedding,
                "text": (
                    f"Bug: {d.title}\n"
                    f"Category: {d.bug_category}\n"
                    f"Root cause: {d.root_cause_guess or 'Unknown'}\n"
                    f"Module: {d.module or 'Unknown'}"
                )
            }
            for d in defects
        ]

    return _retrieve_top_k(query_vec, candidates, k=k, threshold=threshold)


def _build_prompts(
    spec_text: str,
    base_model_name: str,
    new_model_name: str,
    similar_tcs: List[str],
    similar_bugs: List[str]
) -> tuple:
    system = f"""Bạn là Test Engineer Senior tại Thundersoft.
Nhiệm vụ: Sinh testcase cho dòng máy mới "{new_model_name}" dựa trên:
  1. Specification mới (bên dưới)
  2. Testcase mẫu từ base model "{base_model_name}" (học văn phong + mức chi tiết)
  3. Bug đã biết từ base model (sinh "bug-list testcase" để regression test)

Sinh ra 2 nhóm, trả về JSON hợp lệ duy nhất (không markdown, không text thừa):
{{
  "functional": [
    {{"id":"F01","title":"...","precondition":"...","steps":"...","expected_result":"..."}}
  ],
  "bug_list": [
    {{"id":"B01","title":"...","precondition":"...","steps":"...","expected_result":"...","ref_bug":"tên bug gốc"}}
  ]
}}"""

    tc_ctx = "\n---\n".join(similar_tcs) if similar_tcs else "(không có TC mẫu phù hợp)"
    bug_ctx = "\n---\n".join(similar_bugs) if similar_bugs else "(không có bug liên quan)"

    user = f"""=== SPECIFICATION CẦN TEST ===
{spec_text[:3000]}

=== TC MẪU TỪ BASE MODEL ===
{tc_ctx}

=== BUG ĐÃ BIẾT TỪ BASE MODEL ===
{bug_ctx}"""

    return system, user


async def generate_testcases_rag(
    db: AsyncSession,
    spec_text: str,
    base_model_name: str,
    new_model_name: str,
    tc_k: int = 5,
    bug_k: int = 5,
    base_tc_override: list = None,
) -> Dict[str, Any]:
    safe_spec = mask_sensitive_data(spec_text)

    # Nếu có TC override từ file upload, dùng luôn thay vì query DB
    if base_tc_override:
        similar_tcs = [
            f"Title: {tc.get('title')}\nPrecondition: {tc.get('precondition','')}\n"
            f"Steps: {tc.get('steps','')}\nExpected: {tc.get('expected_result','')}"
            for tc in base_tc_override[:tc_k]
        ]
    else:
        similar_tcs = await retrieve_similar_testcases(db, safe_spec, base_model_name, k=tc_k)
    similar_bugs = await retrieve_similar_defects(db, safe_spec, base_model_name, k=bug_k)

    logger.info(f"[RAG] base={base_model_name}→{new_model_name} tcs={len(similar_tcs)} bugs={len(similar_bugs)}")

    system_p, user_p = _build_prompts(safe_spec, base_model_name, new_model_name, similar_tcs, similar_bugs)

    raw = await call_llm(user_p, system_prompt=system_p)

    # Strip markdown fences
    clean = raw.strip()
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                result = json.loads(part)
                break
            except Exception:
                continue
        else:
            result = {"functional": [], "bug_list": [], "_error": "JSON parse failed"}
    else:
        try:
            result = json.loads(clean)
        except json.JSONDecodeError:
            result = {"functional": [], "bug_list": [], "_error": f"Cannot parse: {clean[:100]}"}

    result["_meta"] = {
        "base_model": base_model_name,
        "new_model": new_model_name,
        "similar_tcs_found": len(similar_tcs),
        "similar_bugs_found": len(similar_bugs),
    }
    return result
