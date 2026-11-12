"""Payment Policy and Approval Security Engine

Enforces strict backend governance rules:
1. Exact parameter binding (payee, amount, currency, purpose, invoice) via SHA-256 fingerprint.
2. Invalidation of prior approval upon any parameter alteration.
3. Configurable dual-control review rules for high-risk / high-value disbursements.
4. Mandatory non-overrideable blocks for critical-risk invoices.
5. Approver identity, role, and timestamp auditing.
6. Safe 24-hour expiration of pending approvals.
7. Replay prevention and state machine integrity.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.payment import PaymentDraft, PaymentApproval
from app.models.business import Business
from app.models.user import User
from app.models.guardian import RiskAssessment
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class PaymentPolicyEngine:
    DEFAULT_EXPIRATION_HOURS = 24.0

    @staticmethod
    def compute_details_hash(
        vendor_id: int,
        amount: float,
        currency: str,
        purpose: Optional[str] = None,
        invoice_number: Optional[str] = None,
    ) -> str:
        """Computes a deterministic SHA-256 fingerprint locking exact draft details."""
        raw = f"{vendor_id}|{amount:.2f}|{currency.upper()}|{(purpose or '').strip().lower()}|{(invoice_number or '').strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def verify_draft_fingerprint(cls, draft: PaymentDraft) -> Tuple[bool, str, str]:
        """Compares current draft parameters with the locked details_hash."""
        current_hash = cls.compute_details_hash(
            vendor_id=draft.vendor_id,
            amount=draft.amount,
            currency=draft.currency,
            purpose=draft.purpose,
            invoice_number=draft.invoice_number,
        )
        if not draft.details_hash:
            return False, current_hash, "Draft has no locked details_hash (unapproved)."
        if draft.details_hash != current_hash:
            return False, current_hash, "Payment parameters modified after approval; fingerprint mismatch."
        return True, current_hash, "Fingerprint matches locked approval details."

    @classmethod
    def check_and_apply_expiration(cls, db: Session, draft: PaymentDraft, business: Business) -> bool:
        """Inspects if approval validity window has expired. Transitions status to EXPIRED if stale."""
        if draft.status == "APPROVED" and draft.expires_at:
            if datetime.utcnow() > draft.expires_at:
                prior_approved_at = draft.approved_at
                draft.status = "EXPIRED"
                draft.approved_at = None
                draft.approved_by_id = None
                draft.secondary_approved_at = None
                draft.secondary_approved_by_id = None
                draft.details_hash = None
                draft.updated_at = datetime.utcnow()

                AuditService.log_event(
                    db=db,
                    business_id=business.id,
                    user_id=None,
                    stage="DECIDE",
                    actor="POLICY_ENGINE",
                    action="APPROVAL_EXPIRED",
                    summary=f"Approval for Payment Draft #{draft.id} expired after validity window",
                    details=f"Draft #{draft.id} ({draft.currency} {draft.amount:,.2f}) approved at {prior_approved_at}. Stale authorization revoked.",
                    rationale="Security policy automatically invalidates approvals older than configured validity hours to prevent execution against stale financial conditions.",
                )
                db.commit()
                db.refresh(draft)
                return True
        return False

    @classmethod
    def evaluate_approval_eligibility(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user: Optional[User] = None,
        dual_approval_override: bool = False,
    ) -> Dict[str, Any]:
        """Evaluates whether a payment draft is eligible for approval under corporate policy."""
        # Check expiration first
        is_expired = cls.check_and_apply_expiration(db, draft, business)

        # Retrieve latest risk assessment
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.payment_draft_id == draft.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )

        settings = business.settings
        dual_approval_threshold = settings.require_dual_approval_above if settings else 1000.0
        validity_hours = settings.approval_validity_hours if settings else cls.DEFAULT_EXPIRATION_HOURS

        requires_dual = False
        if assessment:
            if assessment.risk_score >= 50.0 or assessment.verdict == "REQUIRES_DUAL_EXECUTIVE_APPROVAL":
                requires_dual = True
        if draft.amount >= dual_approval_threshold:
            requires_dual = True

        # Check terminal states
        if draft.status in ("COMPLETED", "PROVIDER_PENDING"):
            return {
                "can_approve": False,
                "mandatory_block": False,
                "requires_dual_approval": requires_dual,
                "status": draft.status,
                "current_step": 2 if requires_dual else 1,
                "total_steps": 2 if requires_dual else 1,
                "reason": f"Payment is already in final provider state '{draft.status}'.",
                "recommended_action": "MONITOR",
            }

        # Check Guardian risk investigation
        if not assessment:
            return {
                "can_approve": False,
                "mandatory_block": False,
                "requires_dual_approval": requires_dual,
                "status": draft.status,
                "current_step": 0,
                "total_steps": 2 if requires_dual else 1,
                "reason": "Payment draft must be investigated by Guardian AI risk engine before approval.",
                "recommended_action": "RUN_RISK_SCAN",
            }

        # Mandatory Block Check (Non-overrideable)
        if assessment.verdict == "BLOCKED" or assessment.risk_score >= 75.0:
            return {
                "can_approve": False,
                "mandatory_block": True,
                "requires_dual_approval": requires_dual,
                "status": "BLOCKED",
                "current_step": 0,
                "total_steps": 2 if requires_dual else 1,
                "reason": "MANDATORY BLOCK: Guardian AI detected CRITICAL fraud or policy violation. This block cannot be overridden by user instructions.",
                "recommended_action": "REJECT_AND_BLOCK",
                "verdict": assessment.verdict,
                "risk_score": assessment.risk_score,
            }

        # Expired check
        if draft.status == "EXPIRED":
            return {
                "can_approve": False,
                "mandatory_block": False,
                "requires_dual_approval": requires_dual,
                "status": "EXPIRED",
                "current_step": 0,
                "total_steps": 2 if requires_dual else 1,
                "reason": f"Approval expired (valid for {validity_hours:g} hours). Please run a fresh risk scan to re-authorize.",
                "recommended_action": "RE_SCAN_RISK",
            }

        # Check Dual Approval Progress
        if requires_dual:
            if not draft.approved_at:
                return {
                    "can_approve": True,
                    "mandatory_block": False,
                    "requires_dual_approval": True,
                    "status": draft.status,
                    "current_step": 1,
                    "total_steps": 2,
                    "step_name": "INITIAL_EXECUTIVE_APPROVAL",
                    "reason": f"High risk/value payment ({draft.currency} {draft.amount:,.2f}) mandates dual executive authorization. Ready for primary approval.",
                    "recommended_action": "APPROVE_STEP_1",
                }
            elif not draft.secondary_approved_at:
                # Check separation of duties (Four-Eyes Principle)
                is_same_user = bool(user and draft.approved_by_id and user.id == draft.approved_by_id)
                can_user_sign = (not is_same_user) or dual_approval_override

                return {
                    "can_approve": can_user_sign,
                    "mandatory_block": False,
                    "requires_dual_approval": True,
                    "status": "AWAITING_APPROVAL",
                    "current_step": 2,
                    "total_steps": 2,
                    "step_name": "SECONDARY_EXECUTIVE_APPROVAL",
                    "primary_approver_id": draft.approved_by_id,
                    "primary_approver_name": draft.approved_by.full_name if draft.approved_by else "Executive",
                    "primary_approved_at": draft.approved_at.isoformat() if draft.approved_at else None,
                    "reason": (
                        "Primary approval recorded. Ready for secondary executive authorization."
                        if can_user_sign
                        else "Dual-control policy requires secondary approval from a DIFFERENT executive user (Four-Eyes Principle)."
                    ),
                    "recommended_action": "APPROVE_STEP_2",
                }
            else:
                return {
                    "can_approve": False,
                    "mandatory_block": False,
                    "requires_dual_approval": True,
                    "status": "APPROVED",
                    "current_step": 2,
                    "total_steps": 2,
                    "reason": "Dual authorization fully granted. Eligible for PayPal Sandbox execution.",
                    "recommended_action": "EXECUTE_PAYMENT",
                }

        # Single Approval Flow
        if draft.status == "APPROVED":
            return {
                "can_approve": False,
                "mandatory_block": False,
                "requires_dual_approval": False,
                "status": "APPROVED",
                "current_step": 1,
                "total_steps": 1,
                "reason": "Payment draft is fully approved. Eligible for payment execution.",
                "recommended_action": "EXECUTE_PAYMENT",
            }

        return {
            "can_approve": True,
            "mandatory_block": False,
            "requires_dual_approval": False,
            "status": draft.status,
            "current_step": 1,
            "total_steps": 1,
            "step_name": "SINGLE_EXECUTIVE_APPROVAL",
            "reason": f"Payment is verified and eligible for executive approval ({draft.currency} {draft.amount:,.2f}).",
            "recommended_action": "APPROVE_PAYMENT",
        }

    @classmethod
    def approve_draft(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user: User,
        notes: Optional[str] = None,
        expected_details_hash: Optional[str] = None,
        dual_approval_override: bool = False,
    ) -> PaymentDraft:
        """Executes strict approval governance."""
        # Auto-evaluate with Guardian AI if draft has not yet been investigated
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.payment_draft_id == draft.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        if not assessment:
            from app.services.guardian_service import GuardianRiskEngine
            GuardianRiskEngine.evaluate(
                db=db,
                draft=draft,
                business=business,
                user_id=user.id,
            )

        eligibility = cls.evaluate_approval_eligibility(
            db, draft, business, user=user, dual_approval_override=dual_approval_override
        )

        if eligibility.get("mandatory_block"):
            AuditService.log_event(
                db=db,
                business_id=business.id,
                user_id=user.id if user else None,
                stage="DECIDE",
                actor="GUARDIAN_AI",
                action="POLICY_VIOLATION",
                summary=f"Mandatory Block Violation: Attempted approval on blocked Draft #{draft.id}",
                details=eligibility.get("reason"),
                rationale="Critical risk payments cannot be approved or bypassed.",
                decision_id=draft.id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=eligibility.get("reason"),
            )

        if not eligibility.get("can_approve"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=eligibility.get("reason"),
            )

        # Compute current deterministic fingerprint
        current_hash = cls.compute_details_hash(
            vendor_id=draft.vendor_id,
            amount=draft.amount,
            currency=draft.currency,
            purpose=draft.purpose,
            invoice_number=draft.invoice_number,
        )

        if expected_details_hash and expected_details_hash != current_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment draft parameters changed since you reviewed the page. Please reload and review the updated details.",
            )

        validity_hours = business.settings.approval_validity_hours if business.settings else cls.DEFAULT_EXPIRATION_HOURS
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=validity_hours)

        requires_dual = eligibility.get("requires_dual_approval", False)
        current_step = eligibility.get("current_step", 1)

        if requires_dual:
            draft.requires_dual_approval = True
            if current_step == 1:
                # Step 1: Initial Executive Approval
                draft.details_hash = current_hash
                draft.approved_at = now
                draft.approved_by_id = user.id
                draft.expires_at = expires_at
                draft.status = "AWAITING_APPROVAL"

                approval_record = PaymentApproval(
                    payment_draft_id=draft.id,
                    approved_by_id=user.id,
                    status="APPROVED",
                    approval_role="PRIMARY_APPROVER",
                    details_hash=current_hash,
                    expires_at=expires_at,
                    notes=notes or "Primary executive authorization granted (Step 1 of 2).",
                    approved_at=now,
                )
                db.add(approval_record)

                AuditService.log_event(
                    db=db,
                    business_id=business.id,
                    user_id=user.id,
                    stage="APPROVE",
                    actor="USER",
                    action="PRIMARY_APPROVAL_GRANTED",
                    summary=f"Primary executive approval granted for Draft #{draft.id} by {user.full_name}",
                    details=f"Amount: {draft.currency} {draft.amount:,.2f}. Fingerprint: {current_hash[:12]}... Awaiting secondary sign-off.",
                    rationale="Step 1 of dual-control security policy completed.",
                    decision_id=draft.id,
                )
                NotificationService.notify_awaiting_approval(
                    db=db,
                    business_id=business.id,
                    draft_id=draft.id,
                    title=draft.title,
                    amount=draft.amount,
                    currency=draft.currency,
                    step=2,
                    user_id=user.id,
                )
            else:
                # Step 2: Secondary Executive Approval
                if user and draft.approved_by_id and user.id == draft.approved_by_id and not dual_approval_override:
                    AuditService.log_event(
                        db=db,
                        business_id=business.id,
                        user_id=user.id,
                        stage="APPROVE",
                        actor="USER",
                        action="POLICY_VIOLATION",
                        summary=f"Separation of Duties Violation on Draft #{draft.id}",
                        details="Primary approver attempted to self-authorize secondary approval.",
                        rationale="Dual-control policy requires two distinct executive officers.",
                        decision_id=draft.id,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Dual-control policy violation: Secondary approval must be granted by a DIFFERENT executive user (Four-Eyes Principle).",
                    )

                draft.details_hash = current_hash
                draft.secondary_approved_at = now
                draft.secondary_approved_by_id = user.id
                draft.expires_at = expires_at
                draft.status = "APPROVED"

                approval_record = PaymentApproval(
                    payment_draft_id=draft.id,
                    approved_by_id=user.id,
                    status="APPROVED",
                    approval_role="SECONDARY_APPROVER",
                    details_hash=current_hash,
                    expires_at=expires_at,
                    notes=notes or "Secondary executive authorization granted (Step 2 of 2).",
                    approved_at=now,
                )
                db.add(approval_record)

                AuditService.log_event(
                    db=db,
                    business_id=business.id,
                    user_id=user.id,
                    stage="APPROVE",
                    actor="USER",
                    action="DUAL_APPROVAL_COMPLETED",
                    summary=f"Dual-control authorization fully satisfied for Draft #{draft.id}",
                    details=f"Signer 1: #{draft.approved_by_id}, Signer 2: #{user.id}. Fingerprint: {current_hash[:12]}...",
                    rationale="Secondary authorization verified; payment unlocked for settlement execution.",
                    decision_id=draft.id,
                )
                NotificationService.notify_payment_approved(
                    db=db,
                    business_id=business.id,
                    draft_id=draft.id,
                    title=draft.title,
                    amount=draft.amount,
                    currency=draft.currency,
                    approved_by_name=user.full_name,
                    user_id=user.id,
                )
        else:
            # Single Approval Flow
            draft.details_hash = current_hash
            draft.approved_at = now
            draft.approved_by_id = user.id
            draft.expires_at = expires_at
            draft.requires_dual_approval = False
            draft.status = "APPROVED"

            approval_record = PaymentApproval(
                payment_draft_id=draft.id,
                approved_by_id=user.id,
                status="APPROVED",
                approval_role="PRIMARY_APPROVER",
                details_hash=current_hash,
                expires_at=expires_at,
                notes=notes or "Explicit user authorization granted after risk review.",
                approved_at=now,
            )
            db.add(approval_record)

            AuditService.log_event(
                db=db,
                business_id=business.id,
                user_id=user.id,
                stage="APPROVE",
                actor="USER",
                action="PAYMENT_APPROVED",
                summary=f"Approved payment of {draft.currency} {draft.amount:,.2f} for {draft.vendor.name if draft.vendor else 'Vendor'}",
                details=f"Draft #{draft.id}. Hash: {current_hash[:12]}... Valid until: {expires_at.isoformat()}",
                rationale="Authorized by business executive following pre-payment risk assessment.",
                decision_id=draft.id,
            )
            NotificationService.notify_payment_approved(
                db=db,
                business_id=business.id,
                draft_id=draft.id,
                title=draft.title,
                amount=draft.amount,
                currency=draft.currency,
                approved_by_name=user.full_name,
                user_id=user.id,
            )

        db.commit()
        db.refresh(draft)
        return draft

    @classmethod
    def reject_draft(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user: User,
        reason: Optional[str] = None,
    ) -> PaymentDraft:
        """Rejects a payment draft, records the explicit rejection reason, and revokes prior authorizations."""
        if draft.status in ("COMPLETED", "PROVIDER_PENDING"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject payment in terminal provider state '{draft.status}'.",
            )

        rejection_notes = (reason or "").strip() or "Declined by executive authority."
        now = datetime.utcnow()

        draft.status = "REJECTED"
        draft.rejection_reason = rejection_notes
        draft.approved_at = None
        draft.approved_by_id = None
        draft.secondary_approved_at = None
        draft.secondary_approved_by_id = None
        draft.details_hash = None
        draft.expires_at = None
        draft.updated_at = now

        rejection_record = PaymentApproval(
            payment_draft_id=draft.id,
            approved_by_id=user.id,
            status="REJECTED",
            approval_role="REJECTION",
            notes=rejection_notes,
            approved_at=now,
        )
        db.add(rejection_record)

        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=user.id,
            stage="DECIDE",
            actor="USER",
            action="PAYMENT_REJECTED",
            summary=f"Rejected payment draft #{draft.id} for {draft.currency} {draft.amount:,.2f}",
            details=f"Vendor: {draft.vendor.name if draft.vendor else ''}. Reason: {rejection_notes}",
            rationale="Executive declined payment draft.",
            decision_id=draft.id,
        )
        NotificationService.notify_payment_rejected(
            db=db,
            business_id=business.id,
            draft_id=draft.id,
            title=draft.title,
            amount=draft.amount,
            currency=draft.currency,
            rejected_by_name=user.full_name,
            reason=rejection_notes,
            user_id=user.id,
        )

        db.commit()
        db.refresh(draft)
        return draft

    @classmethod
    def verify_execution_clearance(cls, db: Session, draft: PaymentDraft, business: Business) -> None:
        """Enforces all mandatory pre-execution clearance invariants before allowing provider disbursement."""
        # 1. Safe Expiration Check
        if cls.check_and_apply_expiration(db, draft, business):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval for Draft #{draft.id} has expired (valid for 24 hours). A fresh risk scan and re-authorization are required.",
            )

        # 2. Status Invariant
        if draft.status != "APPROVED":
            AuditService.log_event(
                db=db,
                business_id=business.id,
                stage="PAY",
                actor="GUARDIAN_AI",
                action="POLICY_VIOLATION",
                summary=f"Unapproved Execution Attempt on Draft #{draft.id}",
                details=f"Current status is '{draft.status}'. Only APPROVED drafts can be executed.",
                rationale="Pre-execution security gate rejected unapproved execution.",
                decision_id=draft.id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Draft #{draft.id} is in status '{draft.status}'. Only APPROVED drafts can be executed. Only APPROVED drafts can initiate PayPal Orders.",
            )

        # 3. Fingerprint Invariant
        matches, current_hash, reason = cls.verify_draft_fingerprint(draft)
        if not matches:
            draft.status = "REVIEW_REQUIRED"
            draft.approved_at = None
            draft.approved_by_id = None
            draft.secondary_approved_at = None
            draft.secondary_approved_by_id = None
            draft.details_hash = None
            db.commit()
            AuditService.log_event(
                db=db,
                business_id=business.id,
                stage="PAY",
                actor="GUARDIAN_AI",
                action="POLICY_VIOLATION",
                summary=f"Tampering Detected on Draft #{draft.id}",
                details=f"Parameters modified after approval: {reason}. Approvals revoked.",
                rationale="Cryptographic fingerprint mismatch detected.",
                decision_id=draft.id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment parameters modified after approval ({reason}). Approval revoked; re-review required.",
            )

        # 4. Guardian Risk Invariant
        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.payment_draft_id == draft.id, RiskAssessment.business_id == business.id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )
        if assessment and (assessment.verdict == "BLOCKED" or assessment.risk_score >= 75.0):
            AuditService.log_event(
                db=db,
                business_id=business.id,
                stage="PAY",
                actor="GUARDIAN_AI",
                action="POLICY_VIOLATION",
                summary=f"Execution Attempt on Critical-Risk Draft #{draft.id}",
                details=f"Verdict: {assessment.verdict}, Risk Score: {assessment.risk_score}/100",
                rationale="Critical risk execution blocked.",
                decision_id=draft.id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Execution BLOCKED: Guardian AI flagged this transaction as CRITICAL fraud/policy risk.",
            )

        # 5. Dual Approval Invariant
        if draft.requires_dual_approval and not draft.secondary_approved_at:
            AuditService.log_event(
                db=db,
                business_id=business.id,
                stage="PAY",
                actor="GUARDIAN_AI",
                action="POLICY_VIOLATION",
                summary=f"Premature Execution Attempt on Draft #{draft.id}",
                details="Dual-control required but secondary authorization missing.",
                rationale="Premature release blocked.",
                decision_id=draft.id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Execution BLOCKED: Dual-control policy mandates secondary executive authorization before funds can be released.",
            )
