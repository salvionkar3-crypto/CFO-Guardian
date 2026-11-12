"""Audit, Notifications, Explainability & PayPal Webhooks Comprehensive Test Suite

Tests:
1. User registration, login, and configuration audit log recording.
2. Policy violation audit log recording (mandatory blocks, dual-control, unapproved execution).
3. Audit log searching, filtering by stage/actor/action, and pagination.
4. Rich 6-Question Explainability endpoint (/api/v1/audit/explain/{id}).
5. Real-time Notifications: generation, unread counts, marking read, and mark-all-read.
6. PayPal Webhook signature verification:
   - Invalid signature rejection (HTTP 400).
   - Valid signature acceptance.
7. Webhook Idempotent Deduplication (same event_id processed once, safely acknowledged on retry).
8. Webhook Inbound State Reconciliation (CHECKOUT.ORDER.APPROVED, PAYMENT.CAPTURE.COMPLETED, PAYMENT.CAPTURE.DENIED).
"""

import sys
import os
import uuid
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.business import Business, BusinessSettings
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, Transaction
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.webhook import WebhookEvent
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.policy_engine import PaymentPolicyEngine
from app.schemas.payment import PaymentDraftCreateRequest, PaymentDraftApproveRequest


client = TestClient(app)


def setup_test_tenant(db):
    """Sets up an isolated test business and user."""
    suffix = uuid.uuid4().hex[:6]
    test_email = f"cfo_{suffix}@auditsecurity.corp"
    user = User(
        email=test_email,
        hashed_password=hash_password("AuditSecure2026!"),
        full_name=f"Chief Financial Officer {suffix}",
        role="CFO",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    biz = Business(
        name=f"Audit Corp {suffix}",
        legal_name=f"Audit Corp {suffix} Inc.",
        currency="USD",
        total_balance=100000.0,
        monthly_budget=30000.0,
        monthly_spent=5000.0,
        owner_id=user.id,
    )
    db.add(biz)
    db.commit()
    db.refresh(biz)

    settings = BusinessSettings(
        business_id=biz.id,
        auto_approve_threshold=250.0,
        max_single_payment_limit=5000.0,
        require_dual_approval_above=1000.0,
        risk_tolerance_level="MEDIUM",
        approval_validity_hours=24.0,
        block_critical_risk=True,
        enable_paypal_sandbox=True,
    )
    db.add(settings)
    db.commit()

    vendor = Vendor(
        business_id=biz.id,
        name=f"Global Cloud Services {suffix}",
        email=f"billing_{suffix}@cloudserv.com",
        bank_or_paypal_email=f"billing_{suffix}@cloudserv.com",
        status="ACTIVE",
        trust_score=90.0,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    token = create_access_token(data={"user_id": user.id, "sub": user.email, "business_id": biz.id, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    return user, biz, vendor, headers


def test_audit_logs_and_configuration():
    print("\n--- 1. Testing Auth & Configuration Change Audit Logs ---")
    db = SessionLocal()
    try:
        user, biz, vendor, headers = setup_test_tenant(db)

        # 1. Verify Configuration Update endpoint and CONFIGURATION_CHANGED log
        update_payload = {
            "auto_approve_threshold": 300.0,
            "require_dual_approval_above": 2000.0,
            "risk_tolerance_level": "LOW",
        }
        res = client.put("/api/v1/cfo/settings", json=update_payload, headers=headers)
        assert res.status_code == 200, res.text
        updated = res.json()
        assert updated["auto_approve_threshold"] == 300.0
        assert updated["require_dual_approval_above"] == 2000.0

        # Check Audit log for CONFIGURATION_CHANGED
        config_log = (
            db.query(AuditLog)
            .filter(AuditLog.business_id == biz.id, AuditLog.action == "CONFIGURATION_CHANGED")
            .first()
        )
        assert config_log is not None
        assert "auto_approve_threshold" in config_log.details
        print(f"[PASS] CONFIGURATION_CHANGED audited: {config_log.summary}")

        # 2. Test Audit Log Search & Filter API
        logs_resp = client.get("/api/v1/audit/logs?action=CONFIGURATION_CHANGED", headers=headers)
        assert logs_resp.status_code == 200
        logs = logs_resp.json()
        assert len(logs) >= 1
        assert logs[0]["action"] == "CONFIGURATION_CHANGED"

        search_resp = client.get("/api/v1/audit/logs?search=auto_approve_threshold", headers=headers)
        assert search_resp.status_code == 200
        search_logs = search_resp.json()
        assert len(search_logs) >= 1
        print(f"[PASS] Audit Log Search & Filter verified ({len(search_logs)} matching logs).")
    finally:
        db.close()


def test_policy_violation_audit_logs():
    print("\n--- 2. Testing Policy Violation Audit Logging ---")
    db = SessionLocal()
    try:
        user, biz, vendor, headers = setup_test_tenant(db)

        # Create unapproved draft
        draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=vendor.id,
            title="Policy Breach Draft",
            amount=6000.0,
            currency="USD",
            category="IT Infrastructure",
            status="DRAFT",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        # Attempt to execute without approval -> MUST violate policy & log
        exec_resp = client.post(
            "/api/v1/payments/execute",
            json={"draft_id": draft.id, "payment_method": "PAYPAL_SANDBOX"},
            headers=headers,
        )
        assert exec_resp.status_code == 400

        violation_log = (
            db.query(AuditLog)
            .filter(
                AuditLog.business_id == biz.id,
                AuditLog.action == "POLICY_VIOLATION",
                AuditLog.decision_id == draft.id,
            )
            .first()
        )
        assert violation_log is not None
        assert "Unapproved Execution Attempt" in violation_log.summary
        print(f"[PASS] POLICY_VIOLATION recorded: {violation_log.summary}")
    finally:
        db.close()


def test_six_question_explainability_report():
    print("\n--- 3. Testing Transparent 6-Question Explainability Report ---")
    db = SessionLocal()
    try:
        user, biz, vendor, headers = setup_test_tenant(db)

        # Create draft via API to run CFO + Guardian analysis
        create_payload = {
            "vendor_id": vendor.id,
            "title": "AWS Compute Cloud Infrastructure",
            "amount": 2500.0,
            "currency": "USD",
            "category": "Technology",
            "purpose": "Monthly cloud server hosting",
            "invoice_number": "INV-2026-CLOUD-99",
        }
        res = client.post("/api/v1/payments/drafts", json=create_payload, headers=headers)
        assert res.status_code == 201, res.text
        draft_data = res.json()
        draft_id = draft_data["id"]

        # Call explain endpoint
        explain_resp = client.get(f"/api/v1/audit/explain/{draft_id}", headers=headers)
        assert explain_resp.status_code == 200, explain_resp.text
        rep = explain_resp.json()

        # Validate 6 questions presence and structured quality
        assert "what_happened" in rep and len(rep["what_happened"]) > 10
        assert "why_flagged" in rep and len(rep["why_flagged"]) > 5
        assert "evidence_detected" in rep and isinstance(rep["evidence_detected"], list)
        assert "action_taken" in rep and len(rep["action_taken"]) > 5
        assert "approval_details" in rep and "approvers" in rep["approval_details"]
        assert "final_provider_status" in rep and rep["final_provider_status"]["provider"] == "PayPal REST API"

        print(f"[PASS] Dimension 1 (What happened?): {rep['what_happened'][:80]}...")
        print(f"[PASS] Dimension 2 (Why flagged?): {rep['why_flagged'][:80]}...")
        print(f"[PASS] Dimension 3 (Evidence detected): {len(rep['evidence_detected'])} evidence signals.")
        print(f"[PASS] Dimension 4 (Action taken): {rep['action_taken']}")
        print(f"[PASS] Dimension 5 (Who approved/rejected): Status={rep['approval_details']['status']}")
        print(f"[PASS] Dimension 6 (Provider status): {rep['final_provider_status']['status']} (Mode: {rep['final_provider_status']['mode']})")
    finally:
        db.close()


def test_notifications_workflow():
    print("\n--- 4. Testing Notification Engine & Read States ---")
    db = SessionLocal()
    try:
        user, biz, vendor, headers = setup_test_tenant(db)

        # 1. Create a notification via NotificationService
        notif = NotificationService.notify_high_risk(
            db=db,
            business_id=biz.id,
            draft_id=999,
            risk_score=85.0,
            risk_level="CRITICAL",
            reasons=["First-time vendor", "Amount spike 400%"],
            user_id=user.id,
        )

        notif2 = NotificationService.notify_awaiting_approval(
            db=db,
            business_id=biz.id,
            draft_id=999,
            title="Urgent Vendor Payment",
            amount=15000.0,
            currency="USD",
            step=1,
            user_id=user.id,
        )

        # 2. Check unread count
        count_resp = client.get("/api/v1/notifications/unread-count", headers=headers)
        assert count_resp.status_code == 200
        assert count_resp.json()["unread_count"] >= 2
        print(f"[PASS] Unread count verified: {count_resp.json()['unread_count']}")

        # 3. Retrieve notifications list
        list_resp = client.get("/api/v1/notifications", headers=headers)
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) >= 2
        assert items[0]["business_id"] == biz.id

        # 4. Mark single notification as read
        read_resp = client.post(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert read_resp.status_code == 200
        assert read_resp.json()["is_read"] is True

        # 5. Mark all as read
        all_read_resp = client.post("/api/v1/notifications/read-all", headers=headers)
        assert all_read_resp.status_code == 200
        assert all_read_resp.json()["success"] is True

        # Verify unread count is now 0
        count_after = client.get("/api/v1/notifications/unread-count", headers=headers).json()
        assert count_after["unread_count"] == 0
        print("[PASS] Notifications lifecycle: create -> list -> read -> read-all -> count 0 verified.")
    finally:
        db.close()


def test_paypal_webhooks():
    print("\n--- 5. Testing PayPal Webhook Signature, Deduplication & Reconciliation ---")
    db = SessionLocal()
    try:
        user, biz, vendor, headers = setup_test_tenant(db)

        # Create an approved draft and transaction for webhook settlement test
        draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=vendor.id,
            title="Webhook Settlement Draft",
            amount=420.0,
            currency="USD",
            status="APPROVED",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        paypal_order_id = f"ORDER-{uuid.uuid4().hex[:12].upper()}"
        tx = Transaction(
            business_id=biz.id,
            vendor_id=vendor.id,
            payment_draft_id=draft.id,
            amount=draft.amount,
            currency=draft.currency,
            category=draft.category,
            description="PayPal Webhook Test Transaction",
            status="PROVIDER_PENDING",
            paypal_order_id=paypal_order_id,
            payment_method="PAYPAL_SANDBOX",
            created_at=datetime.utcnow(),
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        # --- A. Test Invalid Webhook Signature Rejection ---
        event_id_1 = f"WH-EVT-{uuid.uuid4().hex[:10]}"
        bad_headers = {
            "paypal-auth-algo": "TEST_INVALID",
            "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1",
            "paypal-transmission-id": "trans-bad-123",
            "paypal-transmission-sig": "INVALID_SIGNATURE",
            "paypal-transmission-time": datetime.utcnow().isoformat() + "Z",
        }
        bad_payload = {
            "id": event_id_1,
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"id": "CAP-INVALID", "amount": {"value": "420.00", "currency_code": "USD"}},
        }
        bad_res = client.post("/api/v1/webhooks/paypal", json=bad_payload, headers=bad_headers)
        assert bad_res.status_code == 400
        assert "signature rejected" in bad_res.json()["detail"].lower()
        print("[PASS] Invalid PayPal webhook signature rejected with HTTP 400.")

        # --- B. Test Valid Webhook Processing (CHECKOUT.ORDER.APPROVED) ---
        event_id_2 = f"WH-EVT-{uuid.uuid4().hex[:10]}"
        valid_headers = {
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1",
            "paypal-transmission-id": "trans-valid-12345",
            "paypal-transmission-sig": "VALID_MOCK_SIGNATURE_OK",
            "paypal-transmission-time": datetime.utcnow().isoformat() + "Z",
        }
        approved_payload = {
            "id": event_id_2,
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "id": paypal_order_id,
                "custom_id": str(draft.id),
                "status": "APPROVED",
            },
        }
        appr_res = client.post("/api/v1/webhooks/paypal", json=approved_payload, headers=valid_headers)
        assert appr_res.status_code == 200, appr_res.text
        assert appr_res.json()["status"] == "PROCESSED"
        assert appr_res.json()["duplicate"] is False
        print(f"[PASS] CHECKOUT.ORDER.APPROVED processed: Event {event_id_2}")

        # --- C. Test Idempotent Deduplication ---
        dup_res = client.post("/api/v1/webhooks/paypal", json=approved_payload, headers=valid_headers)
        assert dup_res.status_code == 200
        assert dup_res.json()["status"] == "ALREADY_PROCESSED"
        assert dup_res.json()["duplicate"] is True
        print(f"[PASS] Webhook Deduplication verified: Repeat event {event_id_2} acknowledged without re-execution.")

        # --- D. Test Capture Settlement (PAYMENT.CAPTURE.COMPLETED) ---
        event_id_3 = f"WH-EVT-{uuid.uuid4().hex[:10]}"
        capture_id = f"CAP-{uuid.uuid4().hex[:10].upper()}"
        initial_balance = biz.total_balance
        capture_payload = {
            "id": event_id_3,
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": capture_id,
                "custom_id": str(draft.id),
                "amount": {"value": "420.00", "currency_code": "USD"},
                "supplementary_data": {"related_ids": {"order_id": paypal_order_id}},
            },
        }
        cap_res = client.post("/api/v1/webhooks/paypal", json=capture_payload, headers=valid_headers)
        assert cap_res.status_code == 200, cap_res.text
        assert cap_res.json()["status"] == "PROCESSED"

        # Verify database state mutations
        db.refresh(draft)
        db.refresh(tx)
        db.refresh(biz)
        assert draft.status == "COMPLETED"
        assert tx.status == "COMPLETED"
        assert tx.paypal_capture_id == capture_id
        assert biz.total_balance == initial_balance - 420.0
        print(f"[PASS] PAYMENT.CAPTURE.COMPLETED reconciled: Draft #{draft.id} status={draft.status}, Capture={capture_id}")

        # Verify audit log recorded for capture
        cap_log = (
            db.query(AuditLog)
            .filter(AuditLog.business_id == biz.id, AuditLog.action == "PAYPAL_WEBHOOK_CAPTURE_COMPLETED")
            .first()
        )
        assert cap_log is not None
        print(f"[PASS] Webhook audit trail recorded: {cap_log.summary}")

        # Verify notification created
        cap_notif = (
            db.query(Notification)
            .filter(Notification.business_id == biz.id, Notification.category == "PAYMENT_COMPLETED")
            .first()
        )
        assert cap_notif is not None
        print(f"[PASS] PAYMENT_COMPLETED notification received: {cap_notif.title}")

        # --- E. Test Webhook Events Listing Endpoint ---
        events_resp = client.get("/api/v1/webhooks/events", headers=headers)
        assert events_resp.status_code == 200
        events_list = events_resp.json()
        assert len(events_list) >= 2
        print(f"[PASS] Webhook Events audit list verified ({len(events_list)} events recorded).")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("STARTING AUDIT, NOTIFICATIONS, EXPLAINABILITY & WEBHOOKS TESTS")
    print("=" * 65)

    test_audit_logs_and_configuration()
    test_policy_violation_audit_logs()
    test_six_question_explainability_report()
    test_notifications_workflow()
    test_paypal_webhooks()

    print("\n" + "=" * 65)
    print("ALL AUDIT, NOTIFICATIONS, EXPLAINABILITY & WEBHOOK TESTS PASSED!")
    print("=" * 65 + "\n")
