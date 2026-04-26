import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import AuditLog

logger = logging.getLogger("qa_hub.audit")

async def write_audit_log(
    db: AsyncSession,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str = None,
    reason: str = None
):
    """
    Ghi hành động vào audit_log.
    Gọi ở mọi nơi cần lưu vết: Lock, Unlock, AssignMentor, Delegate, v.v.
    """
    try:
        log_entry = AuditLog(
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            entity_type=entity_type,
            entity_id=uuid.UUID(entity_id) if entity_id else None,
            reason=reason
        )
        db.add(log_entry)
        # Không commit ở đây — để caller commit cùng transaction chính
        logger.info(f"[AUDIT] {action} on {entity_type}={entity_id} by user={user_id} reason={reason}")
    except Exception as e:
        logger.error(f"[AUDIT] Failed to write log: {e}")
        # Không raise — audit log failure không được phá vỡ nghiệp vụ chính
