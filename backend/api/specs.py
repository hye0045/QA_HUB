from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import logging

from core.security import get_current_user
from db.database import get_db
from db.models import (
    Specification, SpecVersion, Testcase,
    testcase_spec_link, spec_version_model_link, DeviceModelProfile
)

logger = logging.getLogger("qa_hub.specs")
router = APIRouter(prefix="/specs", tags=["Specifications"])


class SpecSync(BaseModel):
    title: str
    language: str
    content: str
    version_number: int
    feature_name: Optional[str] = None
    model_profile_ids: List[str] = []


@router.get("/")
async def list_specs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Specification))
    specs = result.scalars().all()

    data = []
    for s in specs:
        # Lấy tất cả versions kèm thông tin models
        ver_res = await db.execute(
            select(SpecVersion)
            .where(SpecVersion.specification_id == s.id)
            .order_by(SpecVersion.version_number.desc())
        )
        versions = ver_res.scalars().all()

        versions_info = []
        for ver in versions:
            # Lấy danh sách models của version này
            model_res = await db.execute(
                select(DeviceModelProfile)
                .join(
                    spec_version_model_link,
                    spec_version_model_link.c.model_profile_id == DeviceModelProfile.id
                )
                .where(spec_version_model_link.c.spec_version_id == ver.id)
            )
            models = model_res.scalars().all()
            versions_info.append({
                "version_number": ver.version_number,
                "created_at": ver.created_at.isoformat(),
                "supported_models": [{"id": str(m.id), "name": m.name} for m in models]
            })

        latest_ver = versions[0] if versions else None
        data.append({
            "id": str(s.id),
            "title": s.title,
            "feature_name": s.feature_name or s.title,
            "language": s.language,
            "latest_version": latest_ver.version_number if latest_ver else 0,
            "content": latest_ver.content if latest_ver else "",
            "versions": versions_info
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
            if spec.feature_name:
                existing_spec.feature_name = spec.feature_name
        else:
            new_spec = Specification(
                title=spec.title,
                feature_name=spec.feature_name or spec.title,
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

        # Tạo embedding vector (chạy trong thread riêng để không block event loop)
        from fastapi.concurrency import run_in_threadpool
        from services.ai_service import get_embedding
        embedding_vector = await run_in_threadpool(get_embedding, spec.content)

        # Tạo version mới
        new_version = SpecVersion(
            specification_id=spec_id,
            version_number=spec.version_number,
            content=spec.content,
            embedding=embedding_vector if embedding_vector else None,
            created_by=uuid.UUID(current_user['id'])
        )
        db.add(new_version)
        await db.flush()

        if spec.model_profile_ids:
            for profile_id_str in spec.model_profile_ids:
                try:
                    profile_uuid = uuid.UUID(profile_id_str)
                    prof_res = await db.execute(
                        select(DeviceModelProfile).where(DeviceModelProfile.id == profile_uuid)
                    )
                    if prof_res.scalars().first():
                        await db.execute(
                            spec_version_model_link.insert().values(
                                spec_version_id=new_version.id,
                                model_profile_id=profile_uuid
                            )
                        )
                except (ValueError, Exception) as e:
                    logger.warning(f"[SPEC SYNC] Bỏ qua model_profile_id không hợp lệ: {profile_id_str}: {e}")

        await db.commit()
        logger.info(f"[SPEC SYNC] SUCCESS spec_id={spec_id} version={spec.version_number} models={spec.model_profile_ids}")
        return {
            "message": "Spec synced successfully",
            "spec_id": str(spec_id),
            "version_id": str(new_version.id),
            "linked_models": len(spec.model_profile_ids)
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"[SPEC SYNC] FAILED title='{spec.title}' error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/by-feature")
async def get_specs_by_feature(
    feature_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trả về tất cả Specification có cùng feature_name.
    Dùng để so sánh cùng 1 chức năng spec giữa các dòng máy khác nhau.
    """
    result = await db.execute(
        select(Specification).where(
            Specification.feature_name.ilike(f"%{feature_name}%")
        )
    )
    specs = result.scalars().all()

    data = []
    for s in specs:
        ver_res = await db.execute(
            select(SpecVersion)
            .where(SpecVersion.specification_id == s.id)
            .order_by(SpecVersion.version_number.desc())
        )
        versions = ver_res.scalars().all()

        for ver in versions:
            model_res = await db.execute(
                select(DeviceModelProfile)
                .join(
                    spec_version_model_link,
                    spec_version_model_link.c.model_profile_id == DeviceModelProfile.id
                )
                .where(spec_version_model_link.c.spec_version_id == ver.id)
            )
            models = model_res.scalars().all()
            data.append({
                "spec_id": str(s.id),
                "spec_title": s.title,
                "feature_name": s.feature_name,
                "version_number": ver.version_number,
                "version_id": str(ver.id),
                "supported_models": [{"id": str(m.id), "name": m.name} for m in models],
                "content_preview": ver.content[:300] + "..." if len(ver.content) > 300 else ver.content
            })

    return data


@router.get("/cross-model-diff")
async def cross_model_diff(
    spec_id_a: str,
    version_a: int,
    spec_id_b: str,
    version_b: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    So sánh spec giữa 2 dòng máy khác nhau (hoặc 2 versions khác nhau).
    """
    import difflib

    async def get_version_content(spec_id_str: str, ver_num: int):
        ver_res = await db.execute(
            select(SpecVersion).where(
                SpecVersion.specification_id == uuid.UUID(spec_id_str),
                SpecVersion.version_number == ver_num
            )
        )
        ver = ver_res.scalars().first()
        if not ver:
            return None, None
        model_res = await db.execute(
            select(DeviceModelProfile)
            .join(spec_version_model_link,
                  spec_version_model_link.c.model_profile_id == DeviceModelProfile.id)
            .where(spec_version_model_link.c.spec_version_id == ver.id)
        )
        models = [m.name for m in model_res.scalars().all()]
        return ver.content, models

    content_a, models_a = await get_version_content(spec_id_a, version_a)
    content_b, models_b = await get_version_content(spec_id_b, version_b)

    if not content_a or not content_b:
        raise HTTPException(status_code=404, detail="Không tìm thấy một trong hai version")

    text_a = content_a.splitlines(keepends=True)
    text_b = content_b.splitlines(keepends=True)

    label_a = f"spec={spec_id_a[:8]} v{version_a} [{', '.join(models_a) or 'no model'}]"
    label_b = f"spec={spec_id_b[:8]} v{version_b} [{', '.join(models_b) or 'no model'}]"

    diff = list(difflib.unified_diff(text_a, text_b, fromfile=label_a, tofile=label_b))
    return {
        "diff": "".join(diff),
        "source": {"spec_id": spec_id_a, "version": version_a, "models": models_a},
        "target": {"spec_id": spec_id_b, "version": version_b, "models": models_b}
    }


@router.get("/by-model/{model_name}")
async def get_specs_by_model(
    model_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lấy tất cả Spec versions thuộc về một dòng máy cụ thể.
    Dùng trong TestCaseGenerator để chọn Spec làm input.
    """
    prof_res = await db.execute(
        select(DeviceModelProfile).where(DeviceModelProfile.name == model_name)
    )
    profile = prof_res.scalars().first()
    if not profile:
        return []

    ver_res = await db.execute(
        select(SpecVersion)
        .join(spec_version_model_link,
              spec_version_model_link.c.spec_version_id == SpecVersion.id)
        .where(spec_version_model_link.c.model_profile_id == profile.id)
        .order_by(SpecVersion.created_at.desc())
    )
    versions = ver_res.scalars().all()

    result = []
    for ver in versions:
        spec_res = await db.execute(
            select(Specification).where(Specification.id == ver.specification_id)
        )
        spec = spec_res.scalars().first()
        if spec:
            result.append({
                "spec_id": str(spec.id),
                "spec_title": spec.title,
                "feature_name": spec.feature_name or spec.title,
                "version_number": ver.version_number,
                "version_id": str(ver.id),
                "content_preview": ver.content[:200] + "..." if len(ver.content) > 200 else ver.content
            })
    return result


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
