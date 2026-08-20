"""Shared audit-logging helper — single source of truth for writing
AuditLog rows, used by every router/engine that needs to record an action
(previously duplicated as a private `_log()` inside app/routers/admin.py).
"""

import json
from typing import Any, Optional

from sqlmodel import Session

from app.models import AuditLog, User


def log_action(
    session: Session,
    actor: User,
    action: str,
    target_type: str,
    target_id: Optional[int],
    detail: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail, default=str),
        )
    )
    session.commit()
