from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import logging

from core.security import get_current_user
from db.database import get_db
from db.models import Specification, SpecVersion, Testcase, testcase_spec_link

logger = logging.getLogger("qa_hub.specs")
router = APIRouter(prefix="/specs", tags=["Specifications"])


class SpecSync(BaseModel):
    title: str
    language: str
    content: str
    version_number: int


@router.get("/")
async def list_specs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Specification))
    specs = result.scalars().all()

    data = []
    for s in specs:
        ver_res = await db.execute(
            select(SpecVersion)
            .where(SpecVersion.specification_id == s.id)
            .order_by(SpecVersion.version_number.desc())
            .limit(1)
        )
        ver = ver_res.scalars().first()
        data.append({
            "id": str(s.id),
            "title": s.title,
            "language": s.language,
            "latest_version": ver.version_number if ver else 0,
            "content": ver.content if ver else ""
        })

    return data


@router.post("/sync")
async def sync_spec(
    spec: SpecSync,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Đồng bộ một Spec mới hoặc cập nhật phiên bản. Ghi SyncLog kết quả."""
    try:
        # Tìm hoặc tạo Spec cha
        result = await db.execute(select(Specification).where(Specification.title == spec.title))
        existing_spec = result.scalars().first()

        if existing_spec:
            spec_id = existing_spec.id
        else:
            new_spec = Specification(
                title=spec.title,
                language=spec.language,
                created_by=uuid.UUID(current_user['id'])
            )
            db.add(new_spec)
            await db.flush()
            spec_id = new_spec.id

        # Kiểm tra version đã tồn tại chưa
        ver_res = await db.execute(select(SpecVersion).where(
            SpecVersion.specification_id == spec_id,
            SpecVersion.version_number == spec.version_number
        ))
        if ver_res.scalars().first():
            await db.commit()
            return {"message": "Version already exists", "spec_id": str(spec_id)}

        # Đánh dấu testcases liên quan là is_affected
        linked_tcs_res = await db.execute(
            select(testcase_spec_link.c.testcase_id)
            .where(testcase_spec_link.c.specification_id == spec_id)
        )
        linked_tc_ids = [row[0] for row in linked_tcs_res.all()]

        if linked_tc_ids:
            await db.execute(
                update(Testcase)
                .where(Testcase.id.in_(linked_tc_ids))
                .values(is_affected=True)
            )
            logger.info(f"[SPEC SYNC] Marked {len(linked_tc_ids)} testcases as affected for spec={spec_id}")

        # Tạo embedding vector
        from services.ai_service import get_embedding
        embedding_vector = get_embedding(spec.content)

        # Tạo version mới
        new_version = SpecVersion(
            specification_id=spec_id,
            version_number=spec.version_number,
            content=spec.content,
            embedding=embedding_vector if embedding_vector else None,
            created_by=uuid.UUID(current_user['id'])
        )
        db.add(new_version)
        await db.commit()

        logger.info(f"[SPEC SYNC] SUCCESS spec_id={spec_id} version={spec.version_number}")
        return {"message": "Spec synced successfully and trigger executed", "spec_id": str(spec_id)}

    except Exception as e:
        await db.rollback()
        logger.error(f"[SPEC SYNC] FAILED title='{spec.title}' error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{spec_id}/diff")
async def spec_diff(
    spec_id: str,
    v1: int,
    v2: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    import difflib

    ver1_res = await db.execute(select(SpecVersion).where(
        SpecVersion.specification_id == uuid.UUID(spec_id),
        SpecVersion.version_number == v1
    ))
    ver1 = ver1_res.scalars().first()

    ver2_res = await db.execute(select(SpecVersion).where(
        SpecVersion.specification_id == uuid.UUID(spec_id),
        SpecVersion.version_number == v2
    ))
    ver2 = ver2_res.scalars().first()

    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    text1 = ver1.content.splitlines(keepends=True)
    text2 = ver2.content.splitlines(keepends=True)

    diff = list(difflib.unified_diff(text1, text2, fromfile=f'v{v1}', tofile=f'v{v2}'))
    return {"diff": "".join(diff)}


@router.get("/{spec_id}/affected-testcases")
async def get_affected_testcases(
    spec_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trả về danh sách Testcase bị ảnh hưởng sau khi Spec được cập nhật."""
    result = await db.execute(
        select(Testcase)
        .join(testcase_spec_link, testcase_spec_link.c.testcase_id == Testcase.id)
        .where(
            testcase_spec_link.c.specification_id == uuid.UUID(spec_id),
            Testcase.is_affected == True
        )
    )
    tcs = result.scalars().all()
    return [
        {
            "id": str(tc.id),
            "title": tc.title,
            "status": tc.status,
            "is_affected": tc.is_affected,
        }
        for tc in tcs
    ]


class AiDiffRequest(BaseModel):
    spec_id: str
    v1: int
    v2: int
    diff_text: str

@router.post("/ai-diff-analyze")
async def ai_diff_analyze(
    req: AiDiffRequest,
    current_user: dict = Depends(get_current_user)
):
    """AI phân tích sự khác biệt giữa 2 phiên bản Spec."""
    from services.ai_service import call_llm
    import json

    prompt = f"""Bạn là chuyên gia QA tại Thundersoft.
Dưới đây là kết quả so sánh (diff) giữa Version {req.v1} và Version {req.v2} của một Specification.

```diff
{req.diff_text[:3000]}
```

Hãy phân tích ngắn gọn:
1. Tổng quan thay đổi: Liệt kê các phần chính đã thay đổi.
2. Đánh giá mức độ ảnh hưởng đến Testcase hiện tại (Low/Medium/High).
3. Các chức năng/module cần được re-test.
4. Gợi ý hành động tiếp theo cho team QA.

Trả lời bằng Tiếng Việt, format dạng bullet points rõ ràng."""

    try:
        analysis = await call_llm(prompt, system_prompt="Bạn là chuyên gia QA của Thundersoft. Hãy phân tích tài liệu spec ngắn gọn, chuyên nghiệp.")
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"[AI DIFF] Error: {e}", exc_info=True)
        return {"analysis": f"Lỗi AI: {str(e)}"}
