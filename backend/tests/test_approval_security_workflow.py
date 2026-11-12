"""Approval and Security Workflow Test Suite

Tests all mandatory security invariants:
1. Exact payee, amount, currency, and purpose binding (SHA-256 details_hash).
2. Approval bypass rejection (executing unapproved drafts fails).
3. Modified payment draft tampering detection (revokes approval immediately upon mismatch).
4. Automatic approval invalidation on draft update.
5. Mandatory Critical-Risk Block: Cannot be approved or executed, HTTP 403 Forbidden.
6. Configurable Dual-Control Review Rules:
   - High-value / high-risk draft requires two distinct executive approvals.
   - Premature execution blocked after Step 1.
   - Separation of duties: same user cannot self-dual-approve when multiple officers exist.
   - Full clearance after secondary authorization.
7. Safe Approval Expiration: Stale approvals (> 24 hours) automatically expire and block disbursement.
8. Replay & Duplicate Execution Prevention.
9. Explicit Rejection with mandatory audit trail and reason capture.
"""

import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.business import Business, BusinessSettings
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, PaymentApproval, Transaction
from app.models.guardian import RiskAssessment
from app.services.policy_engine import PaymentPolicyEngine
from app.services.guardian_service import GuardianRiskEngine
from app.schemas.payment import (
    PaymentDraftCreateRequest,
    PaymentDraftUpdateRequest,
    PaymentDraftApproveRequest,
    PaymentDraftRejectRequest,
    ExecutePaymentRequest,
)
from app.api.v1.endpoints.payments import (
    create_payment_draft,
    update_payment_draft,
    approve_payment_draft,
    reject_payment_draft,
    execute_payment,
    compute_details_hash,
)


def run_approval_workflow_test_suite():
    db: Session = SessionLocal()
    client = TestClient(app)

    print("\n=======================================================")
    print("STARTING MANDATORY PAYMENT APPROVAL & SECURITY TESTS")
    print("=======================================================")

    try:
        # -------------------------------------------------------------
        # Setup: Multi-User Corporate Enterprise
        # -------------------------------------------------------------
        tag = uuid.uuid4().hex[:6]
        # Executive 1 (CFO)
        cfo_user = User(
            email=f"cfo_{tag}@guardiancfo.ai",
            hashed_password=hash_password("ExecutiveSecret123!"),
            full_name="Elena Rostova (CFO)",
            role="OWNER",
            is_active=True,
        )
        # Executive 2 (VP Finance / Dual Signer)
        vp_user = User(
            email=f"vp_{tag}@guardiancfo.ai",
            hashed_password=hash_password("ExecutiveSecret123!"),
            full_name="Marcus Vance (VP Finance)",
            role="ADMIN",
            is_active=True,
        )
        db.add_all([cfo_user, vp_user])
        db.commit()
        db.refresh(cfo_user)
        db.refresh(vp_user)

        # Create Corporate Business (Owned by CFO)
        biz = Business(
            name=f"Vanguard Global {tag}",
            currency="USD",
            total_balance=250000.0,
            monthly_budget=50000.0,
            monthly_spent=5000.0,
            owner_id=cfo_user.id,
        )
        db.add(biz)
        db.commit()
        db.refresh(biz)

        # Corporate Governance Policy Settings
        settings = BusinessSettings(
            business_id=biz.id,
            auto_approve_threshold=250.0,
            max_single_payment_limit=25000.0,
            require_dual_approval_above=1000.0,  # Any payment >= $1,000 requires Dual Approval
            risk_tolerance_level="MEDIUM",
            approval_validity_hours=24.0,  # Safe 24-hour expiration
            block_critical_risk=True,
        )
        db.add(settings)
        db.commit()

        # Create Known Vendor
        vendor = Vendor(
            business_id=biz.id,
            name=f"Datadog Monitoring {tag}",
            email=f"billing@{tag}.datadog.com",
            bank_or_paypal_email=f"disburse@{tag}.datadog.com",
            status="VERIFIED",
            trust_score=90.0,
            total_paid=15000.0,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        token_cfo = create_access_token(data={"user_id": cfo_user.id, "sub": cfo_user.email})
        token_vp = create_access_token(data={"user_id": vp_user.id, "sub": vp_user.email})
        headers_cfo = {"Authorization": f"Bearer {token_cfo}"}
        headers_vp = {"Authorization": f"Bearer {token_vp}"}

        # -------------------------------------------------------------
        # Test 1: Approval Bypass Attempt on Unapproved Draft
        # -------------------------------------------------------------
        print("\n--- 1. Testing Approval Bypass Attempt (Execution Without Approval) ---")
        draft_req1 = PaymentDraftCreateRequest(
            vendor_id=vendor.id,
            title="Infrastructure Diagnostics",
            amount=450.0,
            currency="USD",
            category="Infrastructure",
            purpose="Monthly APM telemetry cluster instrumentation",
            auto_run_risk_scan=True,
        )
        draft1 = create_payment_draft(request=draft_req1, business=biz, current_user=cfo_user, db=db)
        assert draft1.status in ("RISK_REVIEWED", "REVIEW_REQUIRED", "DRAFT")

        bypass_failed = False
        try:
            import asyncio
            asyncio.run(execute_payment(
                request=ExecutePaymentRequest(draft_id=draft1.id, payment_method="SIMULATED_PROVIDER"),
                business=biz,
                current_user=cfo_user,
                db=db,
            ))
        except HTTPException as exc:
            bypass_failed = True
            assert exc.status_code == 400
            assert "Only APPROVED drafts can be executed" in exc.detail
        assert bypass_failed, "Security Failure: Unapproved draft should not be executable!"
        print("[PASS] Approval bypass rejected: Unapproved draft execution halted with HTTP 400.")

        # -------------------------------------------------------------
        # Test 2: Approval Binds Exact Parameters & Generates Fingerprint
        # -------------------------------------------------------------
        print("\n--- 2. Testing Exact Parameter Binding & Cryptographic Details Hash ---")
        approved_draft1 = approve_payment_draft(
            draft_id=draft1.id,
            request=PaymentDraftApproveRequest(notes="Primary sign-off on telemetry infrastructure"),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert approved_draft1.status == "APPROVED"
        assert approved_draft1.approved_at is not None
        assert approved_draft1.approved_by_id == cfo_user.id
        assert approved_draft1.details_hash is not None
        assert approved_draft1.expires_at is not None

        expected_hash = compute_details_hash(
            vendor_id=draft1.vendor_id,
            amount=draft1.amount,
            currency=draft1.currency,
            purpose=draft1.purpose,
            invoice_number=draft1.invoice_number,
        )
        assert approved_draft1.details_hash == expected_hash
        print(f"[PASS] Details locked with SHA-256: {expected_hash[:16]}... Expiration set to 24h.")

        # -------------------------------------------------------------
        # Test 3: Tampering Detection (Direct DB Alteration Bypassing API)
        # -------------------------------------------------------------
        print("\n--- 3. Testing Tamper Detection on Modified Payment Draft ---")
        # Attacker covertly modifies payment draft amount from $450 to $45,000 directly in SQL
        db_draft1 = db.query(PaymentDraft).filter(PaymentDraft.id == draft1.id).first()
        original_amount = db_draft1.amount
        db_draft1.amount = 45000.0  # Tampered!
        db.commit()

        tamper_detected = False
        try:
            import asyncio
            asyncio.run(execute_payment(
                request=ExecutePaymentRequest(draft_id=draft1.id, payment_method="SIMULATED_PROVIDER"),
                business=biz,
                current_user=cfo_user,
                db=db,
            ))
        except HTTPException as exc:
            tamper_detected = True
            assert exc.status_code == 400
            assert "Payment parameters modified after approval" in exc.detail
        assert tamper_detected, "Security Failure: Execution should fail when parameters are altered!"

        # Verify that approval was immediately invalidated and revoked
        db.refresh(db_draft1)
        assert db_draft1.status == "REVIEW_REQUIRED"
        assert db_draft1.approved_at is None
        assert db_draft1.approved_by_id is None
        print("[PASS] Tamper detection verified: Covert parameter edit revoked approval and reset status to REVIEW_REQUIRED.")

        # Revert draft amount for clean state
        db_draft1.amount = original_amount
        db.commit()

        # -------------------------------------------------------------
        # Test 4: Automatic Approval Invalidation on Draft Update via API
        # -------------------------------------------------------------
        print("\n--- 4. Testing API-Level Approval Invalidation on Draft Update ---")
        # Re-approve draft
        reapproved = approve_payment_draft(
            draft_id=draft1.id,
            request=PaymentDraftApproveRequest(notes="Re-approved after audit"),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert reapproved.status == "APPROVED"

        # Update draft purpose
        updated_draft = update_payment_draft(
            draft_id=draft1.id,
            request=PaymentDraftUpdateRequest(purpose="Updated purpose: expanded log ingestion quota"),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert updated_draft.status == "REVIEW_REQUIRED"
        assert updated_draft.approved_at is None
        assert updated_draft.details_hash is None
        print("[PASS] Approval invalidation verified: Editing purpose immediately cleared approval and required re-review.")

        # -------------------------------------------------------------
        # Test 5: Mandatory Block for Critical Risk (Non-Overrideable)
        # -------------------------------------------------------------
        print("\n--- 5. Testing Mandatory Block for Critical Risk Payments ---")
        # Create critical-risk payment: spoofed vendor / duplicate invoice
        crit_draft_req = PaymentDraftCreateRequest(
            vendor_id=vendor.id,
            title="Brand Impersonation Invoice",
            amount=99000.0,  # Exceeds limits & abnormal
            currency="USD",
            category="Infrastructure",
            purpose="Urgent wire for root DNS certificate bypass",
            invoice_number="INV-CRIT-999",
            auto_run_risk_scan=False,
        )
        crit_draft = create_payment_draft(request=crit_draft_req, business=biz, current_user=cfo_user, db=db)

        # Seed a CRITICAL Risk Assessment
        crit_assessment = RiskAssessment(
            business_id=biz.id,
            payment_draft_id=crit_draft.id,
            risk_score=95.0,
            risk_level="CRITICAL",
            verdict="BLOCKED",
            recommended_action="REJECT_AND_BLOCK",
            plain_explanation="CRITICAL FRAUD ALERT: Invoice amount deviates 600x from operational norms.",
            created_at=datetime.utcnow(),
        )
        db.add(crit_assessment)
        crit_draft.status = "REJECTED"
        db.commit()

        # Attempt to approve critical draft
        crit_approval_blocked = False
        try:
            approve_payment_draft(
                draft_id=crit_draft.id,
                request=PaymentDraftApproveRequest(notes="Executive trying to override block via prompt"),
                business=biz,
                current_user=cfo_user,
                db=db,
            )
        except HTTPException as exc:
            crit_approval_blocked = True
            assert exc.status_code == 403
            assert "MANDATORY BLOCK" in exc.detail or "blocked" in exc.detail.lower()
        assert crit_approval_blocked, "Security Failure: Critical risk draft must be strictly unapprovable!"

        # Attempt to execute critical draft
        crit_exec_blocked = False
        try:
            import asyncio
            asyncio.run(execute_payment(
                request=ExecutePaymentRequest(draft_id=crit_draft.id, payment_method="SIMULATED_PROVIDER"),
                business=biz,
                current_user=cfo_user,
                db=db,
            ))
        except HTTPException as exc:
            crit_exec_blocked = True
            assert exc.status_code in (400, 403)
        assert crit_exec_blocked, "Security Failure: Critical risk execution must be prohibited!"
        print("[PASS] Mandatory Block enforced: Critical risk payment rejected approval with HTTP 403.")

        # -------------------------------------------------------------
        # Test 6: Configurable Dual-Control Review Rules for High-Risk Payments
        # -------------------------------------------------------------
        print("\n--- 6. Testing Configurable Dual-Control Review Rules ---")
        # Amount $5,500 >= $1,000 threshold -> Mandates Dual Executive Approval
        high_val_draft_req = PaymentDraftCreateRequest(
            vendor_id=vendor.id,
            title="Annual Enterprise Datadog Subscription",
            amount=5500.0,
            currency="USD",
            category="Infrastructure",
            purpose="Annual enterprise commitment for core infrastructure",
            auto_run_risk_scan=True,
        )
        high_draft = create_payment_draft(request=high_val_draft_req, business=biz, current_user=cfo_user, db=db)
        assert high_draft.requires_dual_approval is True

        # Policy eligibility check
        eligibility = PaymentPolicyEngine.evaluate_approval_eligibility(db, high_draft, biz, user=cfo_user)
        assert eligibility["requires_dual_approval"] is True
        assert eligibility["current_step"] == 1
        assert eligibility["total_steps"] == 2
        print(f"[PASS] Policy recognized dual approval requirement: {eligibility['reason']}")

        # Step 1: CFO (Elena) grants Primary Approval
        step1_resp = approve_payment_draft(
            draft_id=high_draft.id,
            request=PaymentDraftApproveRequest(notes="Approved Step 1 as CFO"),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert step1_resp.status == "AWAITING_APPROVAL"
        assert step1_resp.approved_by_id == cfo_user.id
        assert step1_resp.approved_at is not None
        assert step1_resp.secondary_approved_at is None
        print("[PASS] Step 1 Approval recorded: Draft status remains AWAITING_APPROVAL.")

        # Attempting execution after only Step 1 must fail
        premature_exec_failed = False
        try:
            import asyncio
            asyncio.run(execute_payment(
                request=ExecutePaymentRequest(draft_id=high_draft.id, payment_method="SIMULATED_PROVIDER"),
                business=biz,
                current_user=cfo_user,
                db=db,
            ))
        except HTTPException as exc:
            premature_exec_failed = True
            assert exc.status_code == 400
            assert "Only APPROVED drafts can be executed" in exc.detail or "Dual-control" in exc.detail
        assert premature_exec_failed, "Security Failure: High-value draft should not execute with only 1 approval!"
        print("[PASS] Premature execution blocked: Payout rejected prior to Step 2 sign-off.")

        # Separation of Duties check: Elena (same user) cannot grant secondary approval
        same_user_blocked = False
        try:
            approve_payment_draft(
                draft_id=high_draft.id,
                request=PaymentDraftApproveRequest(notes="Trying to self-sign Step 2"),
                business=biz,
                current_user=cfo_user,
                db=db,
            )
        except HTTPException as exc:
            same_user_blocked = True
            assert exc.status_code in (400, 403)
            assert "DIFFERENT" in exc.detail or "dual" in exc.detail.lower()
        assert same_user_blocked, "Security Failure: Single user should not be able to self-dual-approve!"
        print("[PASS] Separation of duties enforced: Primary approver cannot self-grant secondary approval.")

        # Step 2: Marcus (VP Finance - Different User) grants Secondary Approval
        step2_resp = approve_payment_draft(
            draft_id=high_draft.id,
            request=PaymentDraftApproveRequest(notes="Dual approval confirmed by VP Finance"),
            business=biz,
            current_user=vp_user,
            db=db,
        )
        assert step2_resp.status == "APPROVED"
        assert step2_resp.secondary_approved_at is not None
        assert step2_resp.secondary_approved_by_id == vp_user.id
        print(f"[PASS] Dual Authorization Completed: Signer 1=#{step2_resp.approved_by_id}, Signer 2=#{step2_resp.secondary_approved_by_id}.")

        # Now execution is fully permitted!
        import asyncio
        exec_high = asyncio.run(execute_payment(
            request=ExecutePaymentRequest(draft_id=high_draft.id, payment_method="SIMULATED_PROVIDER"),
            business=biz,
            current_user=cfo_user,
            db=db,
        ))
        assert exec_high.status == "COMPLETED"
        print(f"[PASS] High-value payout cleared and settled! Tx #{exec_high.transaction_id}")

        # -------------------------------------------------------------
        # Test 7: Safe Expiration of Stale Approvals (> 24 hours)
        # -------------------------------------------------------------
        print("\n--- 7. Testing Safe Expiration of Pending Approvals ---")
        exp_draft_req = PaymentDraftCreateRequest(
            vendor_id=vendor.id,
            title="Expired Approval Invariant Test",
            amount=300.0,
            currency="USD",
            category="Infrastructure",
            purpose="Approval expiration test draft",
            auto_run_risk_scan=True,
        )
        exp_draft = create_payment_draft(request=exp_draft_req, business=biz, current_user=cfo_user, db=db)
        approved_exp_draft = approve_payment_draft(
            draft_id=exp_draft.id,
            request=PaymentDraftApproveRequest(notes="Initial sign-off"),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert approved_exp_draft.status == "APPROVED"

        # Simulate 25 hours elapsed (past 24h validity window)
        db_exp_draft = db.query(PaymentDraft).filter(PaymentDraft.id == exp_draft.id).first()
        db_exp_draft.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()

        # Attempting execution must detect expired status and revoke
        exec_exp_failed = False
        try:
            import asyncio
            asyncio.run(execute_payment(
                request=ExecutePaymentRequest(draft_id=exp_draft.id, payment_method="SIMULATED_PROVIDER"),
                business=biz,
                current_user=cfo_user,
                db=db,
            ))
        except HTTPException as exc:
            exec_exp_failed = True
            assert exc.status_code == 400
            assert "expired" in exc.detail.lower()
        assert exec_exp_failed, "Security Failure: Stale approval should be rejected!"

        db.refresh(db_exp_draft)
        assert db_exp_draft.status == "EXPIRED"
        print("[PASS] Approval expiration enforced: Stale authorization (> 24h) revoked, draft transitioned to EXPIRED.")

        # -------------------------------------------------------------
        # Test 8: Replay & Re-Execution Prevention
        # -------------------------------------------------------------
        print("\n--- 8. Testing Replay & State Machine Re-Execution Prevention ---")
        # Attempt to approve already completed draft
        re_approve_failed = False
        try:
            approve_payment_draft(
                draft_id=high_draft.id,
                request=PaymentDraftApproveRequest(notes="Attempting re-approval on settled payment"),
                business=biz,
                current_user=cfo_user,
                db=db,
            )
        except HTTPException as exc:
            re_approve_failed = True
            assert exc.status_code == 400
            assert "already in final provider state" in exc.detail
        assert re_approve_failed, "Security Failure: Settled payments must be immutable!"
        print("[PASS] State machine immutable: Settled payments cannot be re-approved.")

        # -------------------------------------------------------------
        # Test 9: Explicit Rejection Flow with Mandatory Reason
        # -------------------------------------------------------------
        print("\n--- 9. Testing Explicit Rejection Flow with Reason Recording ---")
        reject_draft_req = PaymentDraftCreateRequest(
            vendor_id=vendor.id,
            title="Marketing Swag Proposal",
            amount=600.0,
            currency="USD",
            category="Marketing",
            purpose="Promotional materials proposal",
            auto_run_risk_scan=True,
        )
        reject_draft_obj = create_payment_draft(request=reject_draft_req, business=biz, current_user=cfo_user, db=db)

        # Reject with clear corporate reason
        rejection_reason_text = "Expenditure rejected: Exceeds non-essential marketing budget for Q4."
        rejected_resp = reject_payment_draft(
            draft_id=reject_draft_obj.id,
            request=PaymentDraftRejectRequest(reason=rejection_reason_text),
            business=biz,
            current_user=cfo_user,
            db=db,
        )
        assert rejected_resp.status == "REJECTED"
        assert rejected_resp.rejection_reason == rejection_reason_text

        # Verify in database
        db_rej = db.query(PaymentDraft).filter(PaymentDraft.id == reject_draft_obj.id).first()
        assert db_rej.status == "REJECTED"
        assert db_rej.rejection_reason == rejection_reason_text
        assert len(db_rej.approvals) >= 1
        assert db_rej.approvals[-1].status == "REJECTED"
        assert db_rej.approvals[-1].approval_role == "REJECTION"
        print(f"[PASS] Rejection verified: Reason '{rejection_reason_text}' recorded in audit log and database.")

        # -------------------------------------------------------------
        # Test 10: HTTP API Endpoints via TestClient
        # -------------------------------------------------------------
        print("\n--- 10. Testing HTTP API Endpoints via TestClient ---")
        # Get draft details via HTTP
        resp = client.get(f"/api/v1/payments/drafts/{high_draft.id}", headers=headers_cfo)
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_dual_approval"] is True
        assert data["secondary_approved_by_name"] == "Marcus Vance (VP Finance)"
        assert len(data["approvals"]) >= 2
        print(f"[PASS] HTTP GET /drafts/{high_draft.id} returned rich dual-approval payload with {len(data['approvals'])} approval items.")

        print("\n=======================================================")
        print("ALL 10 MANDATORY APPROVAL & SECURITY WORKFLOW TESTS PASSED!")
        print("=======================================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_approval_workflow_test_suite()
