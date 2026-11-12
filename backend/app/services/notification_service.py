"""Notification Service

Dispatches and manages real-time system and security alerts:
- HIGH_RISK_DETECTED: Critical/High risk payment detected
- PAYMENT_AWAITING_APPROVAL: Payment draft awaiting executive sign-off
- PAYMENT_APPROVED: Payment approved (step 1 or step 2)
- PAYMENT_REJECTED: Payment rejected with explicit rationale
- PAYMENT_COMPLETED: Payment captured and settled via PayPal Sandbox / provider
- PAYMENT_FAILED: Payment declined, voided, or capture failed
- UNUSUAL_FINANCIAL_ACTIVITY: Anomaly in spending patterns or webhook alerts
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.core.logging_config import logger


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        business_id: int,
        category: str,
        severity: str,
        title: str,
        message: str,
        user_id: Optional[int] = None,
        payment_draft_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
    ) -> Notification:
        """Persists a new notification into the database."""
        notification = Notification(
            business_id=business_id,
            user_id=user_id,
            category=category.upper(),
            severity=severity.upper(),
            title=title,
            message=message,
            payment_draft_id=payment_draft_id,
            transaction_id=transaction_id,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info(
            f"[NOTIFICATION] [{severity}] [{category}] Biz #{business_id}: {title} (Draft: {payment_draft_id})"
        )
        return notification

    @staticmethod
    def notify_high_risk(
        db: Session,
        business_id: int,
        draft_id: int,
        risk_score: float,
        risk_level: str,
        reasons: List[str],
        user_id: Optional[int] = None,
    ) -> Notification:
        severity = "CRITICAL" if risk_score >= 75.0 else "HIGH"
        summary_reasons = "; ".join(reasons[:2]) if reasons else "Elevated risk signals detected"
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="HIGH_RISK_DETECTED",
            severity=severity,
            title=f"Security Alert: {risk_level} Risk Payment Flagged",
            message=f"Draft #{draft_id} scored {risk_score:.0f}/100 ({risk_level}). Flags: {summary_reasons}.",
            user_id=user_id,
            payment_draft_id=draft_id,
        )

    @staticmethod
    def notify_awaiting_approval(
        db: Session,
        business_id: int,
        draft_id: int,
        title: str,
        amount: float,
        currency: str,
        step: int = 1,
        user_id: Optional[int] = None,
    ) -> Notification:
        step_label = "Secondary" if step == 2 else "Executive"
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="PAYMENT_AWAITING_APPROVAL",
            severity="MEDIUM" if step == 2 else "INFO",
            title=f"Approval Required: {title}",
            message=f"Payment #{draft_id} for {currency} {amount:,.2f} requires {step_label} sign-off.",
            user_id=user_id,
            payment_draft_id=draft_id,
        )

    @staticmethod
    def notify_payment_approved(
        db: Session,
        business_id: int,
        draft_id: int,
        title: str,
        amount: float,
        currency: str,
        approved_by_name: str,
        user_id: Optional[int] = None,
    ) -> Notification:
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="PAYMENT_APPROVED",
            severity="LOW",
            title=f"Payment Approved: {title}",
            message=f"Payment #{draft_id} ({currency} {amount:,.2f}) was approved by {approved_by_name}. Ready for execution.",
            user_id=user_id,
            payment_draft_id=draft_id,
        )

    @staticmethod
    def notify_payment_rejected(
        db: Session,
        business_id: int,
        draft_id: int,
        title: str,
        amount: float,
        currency: str,
        rejected_by_name: str,
        reason: str,
        user_id: Optional[int] = None,
    ) -> Notification:
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="PAYMENT_REJECTED",
            severity="HIGH",
            title=f"Payment Rejected: {title}",
            message=f"Payment #{draft_id} ({currency} {amount:,.2f}) was rejected by {rejected_by_name}. Reason: {reason}",
            user_id=user_id,
            payment_draft_id=draft_id,
        )

    @staticmethod
    def notify_payment_completed(
        db: Session,
        business_id: int,
        draft_id: Optional[int],
        transaction_id: Optional[int],
        title: str,
        amount: float,
        currency: str,
        provider_tx_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Notification:
        ref_text = f" (PayPal Capture: {provider_tx_id})" if provider_tx_id else ""
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="PAYMENT_COMPLETED",
            severity="LOW",
            title=f"Payment Settled: {title}",
            message=f"Disbursement of {currency} {amount:,.2f} completed successfully{ref_text}.",
            user_id=user_id,
            payment_draft_id=draft_id,
            transaction_id=transaction_id,
        )

    @staticmethod
    def notify_payment_failed(
        db: Session,
        business_id: int,
        draft_id: Optional[int],
        title: str,
        amount: float,
        currency: str,
        error_reason: str,
        user_id: Optional[int] = None,
    ) -> Notification:
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="PAYMENT_FAILED",
            severity="HIGH",
            title=f"Payment Failed: {title}",
            message=f"Payment #{draft_id or 'N/A'} ({currency} {amount:,.2f}) could not be completed. Reason: {error_reason}",
            user_id=user_id,
            payment_draft_id=draft_id,
        )

    @staticmethod
    def notify_unusual_activity(
        db: Session,
        business_id: int,
        title: str,
        message: str,
        severity: str = "HIGH",
        user_id: Optional[int] = None,
    ) -> Notification:
        return NotificationService.create_notification(
            db=db,
            business_id=business_id,
            category="UNUSUAL_FINANCIAL_ACTIVITY",
            severity=severity,
            title=title,
            message=message,
            user_id=user_id,
        )

    @staticmethod
    def get_notifications(
        db: Session,
        business_id: int,
        is_read: Optional[bool] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Notification]:
        query = db.query(Notification).filter(Notification.business_id == business_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        if category:
            query = query.filter(Notification.category == category.upper())
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_unread_count(db: Session, business_id: int) -> int:
        return (
            db.query(Notification)
            .filter(Notification.business_id == business_id, Notification.is_read.is_(False))
            .count()
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, business_id: int) -> Optional[Notification]:
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.business_id == business_id)
            .first()
        )
        if notif and not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, business_id: int) -> int:
        unread = (
            db.query(Notification)
            .filter(Notification.business_id == business_id, Notification.is_read.is_(False))
            .all()
        )
        now = datetime.utcnow()
        for n in unread:
            n.is_read = True
            n.read_at = now
        db.commit()
        return len(unread)

