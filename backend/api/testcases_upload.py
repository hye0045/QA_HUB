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

    # 3. Đọc headers từ dòng đầu tiên
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="File Excel trống")

    raw_headers = rows[0]
    headers = [str(h).strip().lower() if h is not None else "" for h in raw_headers]

    if "title" not in headers:
        raise HTTPException(
            status_code=400,
            detail=f"File Excel phải có cột 'title'. Các cột tìm thấy: {headers}"
        )

    # 4. Tạo testcase cho từng dòng
    created = 0
    skipped = 0
    for row in rows[1:]:
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        title = str(row_dict.get("title", "")).strip()
        if not title:
            skipped += 1
            continue

        tc = Testcase(
            title=title,
            description=str(row_dict.get("description") or ""),
            steps=str(row_dict.get("steps") or ""),
            expected_result=str(row_dict.get("expected_result") or ""),
            test_type=str(row_dict.get("test_type") or "manual"),
            precondition=str(row_dict.get("precondition") or ""),
            model_id=profile.name,
            status="draft",
            created_by=uuid.UUID(current_user["id"]),
        )
        db.add(tc)
        created += 1

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
