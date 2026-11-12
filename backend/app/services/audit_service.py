"""Audit and Explainability Service

Fintech requirement: Every automated or human touchpoint across the
Understand -> Analyze -> Investigate -> Decide -> Approve -> Pay -> Monitor -> Explain
lifecycle must be logged with actor, rationale, and timestamp.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.core.logging_config import logger


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        stage: str,
        actor: str,
        action: str,
        summary: str,
        business_id: Optional[int] = None,
        user_id: Optional[int] = None,
        decision_id: Optional[int] = None,
        details: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> AuditLog:
        """Appends an immutable audit log entry."""
        if not business_id:
            from app.models.business import Business
            first_biz = db.query(Business).first()
            business_id = first_biz.id if first_biz else 1

        log_entry = AuditLog(
            business_id=business_id,
            user_id=user_id,
            decision_id=decision_id,
            stage=stage.upper(),
            actor=actor.upper(),
            action=action,
            summary=summary,
            details=details,
            rationale=rationale,
            created_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"[AUDIT] [{stage}] [{actor}] {action} - Decision #{decision_id}: {summary}")
        return log_entry

    @staticmethod
    def get_logs_for_decision(db: Session, decision_id: int) -> List[AuditLog]:
        return (
            db.query(AuditLog)
            .filter(AuditLog.decision_id == decision_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

    @staticmethod
    def get_recent_logs(db: Session, limit: int = 50) -> List[AuditLog]:
        return (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

