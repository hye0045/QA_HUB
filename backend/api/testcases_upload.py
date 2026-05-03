# testcases_upload.py
# Endpoint riêng để upload testcase từ file Excel (.xlsx)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import openpyxl
import io
import uuid
import logging

from core.security import get_current_user, require_tester
from db.database import get_db
from db.models import Testcase, DeviceModelProfile

router = APIRouter(prefix="/testcases", tags=["Testcases"])
logger = logging.getLogger("qa_hub.testcases.upload")


@router.post("/upload", dependencies=[Depends(require_tester)])
async def upload_testcases_excel(
    file: UploadFile = File(...),
    model_id: str = Query(..., description="UUID của DeviceModelProfile"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload file Excel chứa nhiều testcase.
    Cột bắt buộc (header dòng đầu): title
    Cột tuỳ chọn: description, steps, expected_result, test_type, precondition
    """
    # 1. Validate model_id
    try:
        profile_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="model_id không hợp lệ (phải là UUID)")

    result = await db.execute(
        select(DeviceModelProfile).where(DeviceModelProfile.id == profile_uuid)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy Device Model Profile: {model_id}")

    # 2. Đọc file Excel
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file .xlsx hoặc .xls")

    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(filename=io.BytesIO(contents), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        logger.error(f"[TC UPLOAD] Lỗi đọc file Excel: {e}")
        raise HTTPException(status_code=400, detail=f"Không thể đọc file Excel: {str(e)}")

    # 3. Quét tối đa 20 dòng đầu để tìm dòng header (hỗ trợ file Nhật)
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="File Excel trống")

    header_row_index = -1
    mapped_headers = []
    
    title_keywords = ["title", "確認項目", "テスト項目", "項目", "大項目", "小項目", "中項目", "tc_title", "test case"]
    desc_keywords = ["description", "詳細", "目的", "概要", "desc"]
    steps_keywords = ["steps", "手順", "操作手順", "テスト手順", "step"]
    expected_keywords = ["expected_result", "期待値", "期待される結果", "判定基準", "expected"]
    precondition_keywords = ["precondition", "前提条件", "事前準備"]
    type_keywords = ["test_type", "種別", "テスト種別", "type"]

    for idx, row in enumerate(rows[:20]):
        row_strs = [str(h).strip().lower() if h is not None else "" for h in row]
        temp_mapped = []
        has_title = False
        
        for h in row_strs:
            if any(k in h for k in title_keywords) and not has_title:
                temp_mapped.append("title")
                has_title = True
            elif any(k in h for k in desc_keywords):
                temp_mapped.append("description")
            elif any(k in h for k in steps_keywords):
                temp_mapped.append("steps")
            elif any(k in h for k in expected_keywords):
                temp_mapped.append("expected_result")
            elif any(k in h for k in precondition_keywords):
                temp_mapped.append("precondition")
            elif any(k in h for k in type_keywords):
                temp_mapped.append("test_type")
            else:
                temp_mapped.append(h)
                
        if "title" in temp_mapped:
            header_row_index = idx
            mapped_headers = temp_mapped
            break

    if header_row_index == -1:
        sample_row = []
        for r in rows[:10]:
            if any(r):
                sample_row = [str(x) for x in r if x is not None]
                break
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy cột 'title' hoặc '確認項目' trong 20 dòng đầu tiên. Dữ liệu mẫu tìm thấy: {sample_row}"
        )

    # 4. Tạo testcase cho từng dòng
    created = 0
    skipped = 0
    for row in rows[header_row_index + 1:]:
        row_dict = {mapped_headers[i]: row[i] for i in range(min(len(mapped_headers), len(row)))}
        title = str(row_dict.get("title", "")).strip()
        if not title:
            skipped += 1
            continue

        from fastapi.concurrency import run_in_threadpool
        from services.ai_service import get_embedding

        combined_text = (
            f"{title}. "
            f"{str(row_dict.get('description') or '')}. "
            f"Steps: {str(row_dict.get('steps') or '')}. "
            f"Expected: {str(row_dict.get('expected_result') or '')}"
        )
        embedding_vector = await run_in_threadpool(get_embedding, combined_text)

        tc = Testcase(
            title=title,
            description=str(row_dict.get("description") or ""),
            steps=str(row_dict.get("steps") or ""),
            expected_result=str(row_dict.get("expected_result") or ""),
            test_type=str(row_dict.get("test_type") or "manual"),
            precondition=str(row_dict.get("precondition") or ""),
            model_id=profile.name,
            status="draft",
            embedding=embedding_vector if embedding_vector else None,
            created_by=uuid.UUID(current_user["id"]),
        )
        db.add(tc)
        created += 1

        if created % 50 == 0:
            await db.flush()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"[TC UPLOAD] DB commit error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi lưu database: {str(e)}")

    logger.info(f"[TC UPLOAD] Uploaded {created} testcases for model={profile.name}, skipped={skipped}")
    return {
        "message": f"Upload thành công {created} testcase cho model '{profile.name}'",
        "created": created,
        "skipped": skipped,
        "model": profile.name
    }
