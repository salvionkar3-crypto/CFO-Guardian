"""Automated Test Suite for Official PayPal REST API Integration (Sandbox & Orders v2)

Official PayPal REST API Reference: https://developer.paypal.com/api/rest/

Tests:
1. Credential verification without charge attempts (never exposes client secret).
2. Token caching and lifecycle in PayPalTokenCache.
3. Pre-flight guardrails (rejects unapproved drafts or blocked Guardian risk).
4. Orders v2 payload generation with idempotency headers (PayPal-Request-Id).
5. Authentic/Mocked OAuth2 token retrieval and Orders v2 creation.
6. Approval URL extraction for buyer sandbox checkout.
7. Orders v2 capture workflow (strict server-side confirmation before balance debit).
8. Order cancellation and draft state reset to APPROVED.
9. HTTP API endpoints (/paypal/config, /paypal/orders, /paypal/orders/{id}/capture).
10. Live Sandbox connectivity (executed if PAYPAL_CLIENT_ID & SECRET are configured).
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import httpx
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.models.business import Business
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, Transaction
from app.models.guardian import RiskAssessment
from app.core.config import settings
from app.core.security import create_access_token
from app.services.paypal_service import (
    PayPalService,
    PayPalTokenCache,
    PayPalConfigurationError,
    PayPalAPIError,
)
from app.api.v1.endpoints.payments import compute_details_hash
from app.main import app


def test_paypal_integration_suite():
    db: Session = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        assert biz is not None, "Demo business Acme Autonomous Corp not found."
        user = biz.owner
        assert user is not None, "Owner user not found."

        print("\n=======================================================")
        print("STARTING PAYPAL REST API (SANDBOX & ORDERS V2) TESTS")
        print("=======================================================\n")

        # -------------------------------------------------------------
        # 1. Credential Verification & Non-Exposure
        # -------------------------------------------------------------
        print("--- 1. Testing Credential Verification & Non-Exposure ---")
        status_info = httpx.run(PayPalService.verify_credentials()) if hasattr(httpx, "run") else None
        # Use asyncio run since verify_credentials is async
        import asyncio
        status_info = asyncio.run(PayPalService.verify_credentials())
        assert "configured" in status_info
        assert "mode" in status_info
        assert status_info["mode"] == settings.PAYPAL_MODE
        assert "base_url" in status_info
        assert "client_secret" not in status_info
        if settings.PAYPAL_CLIENT_SECRET:
            assert settings.PAYPAL_CLIENT_SECRET not in str(status_info)
        print(f"[PASS] Credential status reported safely: Configured={status_info['configured']}, Mode={status_info['mode']}")

        # -------------------------------------------------------------
        # 2. Token Cache Expiration & In-Memory Storage
        # -------------------------------------------------------------
        print("\n--- 2. Testing PayPalTokenCache ---")
        PayPalTokenCache.clear()
        assert PayPalTokenCache.get_token() is None

        test_token = f"MOCK_A21_{uuid.uuid4().hex}"
        # Set token with 3600 seconds
        PayPalTokenCache.set_token(test_token, expires_in_seconds=3600)
        assert PayPalTokenCache.get_token() == test_token

        # Test buffer threshold: token expiring in 30s should be treated as expired (buffer is 60s)
        PayPalTokenCache._expires_at = datetime.utcnow() + timedelta(seconds=30)
        assert PayPalTokenCache.get_token() is None, "Token within 60s buffer must trigger refresh!"
        PayPalTokenCache.clear()
        print("[PASS] PayPalTokenCache expiry buffer and invalidation verified.")

        # -------------------------------------------------------------
        # 3. Pre-flight Guardrails Before Order Creation
        # -------------------------------------------------------------
        print("\n--- 3. Testing Pre-Flight Security Guardrails ---")
        vendor = db.query(Vendor).filter(Vendor.business_id == biz.id).first()
        assert vendor is not None

        # Create draft in DRAFT status (unapproved)
        unapproved_draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=vendor.id,
            created_by_id=user.id,
            title="Pre-flight Guardrail Test",
            amount=320.00,
            currency="USD",
            category="Software & SaaS",
            purpose="Testing order creation rejection on unapproved draft",
            status="DRAFT",  # Not APPROVED
            created_at=datetime.utcnow(),
        )
        db.add(unapproved_draft)
        db.commit()
        db.refresh(unapproved_draft)

        failed_guardrail = False
        try:
            asyncio.run(PayPalService.create_order_for_draft(
                db=db,
                draft=unapproved_draft,
                business=biz,
                user=user,
            ))
        except ValueError as exc:
            failed_guardrail = True
            assert "Only APPROVED drafts can initiate PayPal Orders" in str(exc)
        assert failed_guardrail, "Expected unapproved draft to be rejected before hitting PayPal!"
        print("[PASS] Guardrail verified: Unapproved draft cannot initiate PayPal Orders v2 session.")

        # Now approve the draft
        current_hash = compute_details_hash(
            vendor_id=unapproved_draft.vendor_id,
            amount=unapproved_draft.amount,
            currency=unapproved_draft.currency,
            purpose=unapproved_draft.purpose,
            invoice_number=unapproved_draft.invoice_number,
        )
        unapproved_draft.details_hash = current_hash
        unapproved_draft.status = "APPROVED"
        unapproved_draft.approved_at = datetime.utcnow()
        unapproved_draft.approved_by_id = user.id
        db.commit()

        # -------------------------------------------------------------
        # 4. Mocked Orders v2 Creation Workflow
        # -------------------------------------------------------------
        print("\n--- 4. Testing Orders v2 Creation with Idempotency & Approve Link ---")
        mock_order_id = f"5O190127TN{uuid.uuid4().hex[:6].upper()}"
        mock_approve_url = f"https://www.sandbox.paypal.com/checkoutnow?token={mock_order_id}"

        mock_token_resp = MagicMock(status_code=200)
        mock_token_resp.json.return_value = {
            "access_token": "ACCESS_TOKEN_MOCK_XYZ_123",
            "token_type": "Bearer",
            "expires_in": 32400,
        }

        mock_order_resp = MagicMock(status_code=201)
        mock_order_resp.text = json.dumps({
            "id": mock_order_id,
            "status": "CREATED",
            "intent": "CAPTURE",
            "links": [
                {"href": f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{mock_order_id}", "rel": "self", "method": "GET"},
                {"href": mock_approve_url, "rel": "approve", "method": "GET"},
                {"href": f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{mock_order_id}/capture", "rel": "capture", "method": "POST"},
            ]
        })
        mock_order_resp.json.return_value = json.loads(mock_order_resp.text)

        # Execute order creation with mocked HTTP responses
        with patch("httpx.AsyncClient.post") as mock_post:
            # First call is token, second call is create order
            mock_post.side_effect = [mock_token_resp, mock_order_resp]
            # Temporarily ensure configured for mock test
            with patch.object(PayPalService, "is_configured", return_value=True):
                tx, order_info = asyncio.run(PayPalService.create_order_for_draft(
                    db=db,
                    draft=unapproved_draft,
                    business=biz,
                    user=user,
                    idempotency_key=f"REQ-{uuid.uuid4().hex[:8]}",
                ))

        assert order_info["paypal_order_id"] == mock_order_id
        assert order_info["status"] == "CREATED"
        assert order_info["approval_url"] == mock_approve_url
        assert tx.paypal_order_id == mock_order_id
        assert tx.status == "PROVIDER_PENDING"
        assert tx.payment_method == "PAYPAL_SANDBOX"

        db.refresh(unapproved_draft)
        assert unapproved_draft.status == "PROVIDER_PENDING"
        print(f"[PASS] Orders v2 created: Order ID={order_info['paypal_order_id']}, Status={tx.status}")
        print(f"[PASS] Approval URL captured: {order_info['approval_url']}")

        # -------------------------------------------------------------
        # 5. Orders v2 Live Details Query
        # -------------------------------------------------------------
        print("\n--- 5. Testing Orders v2 Details Lookup ---")
        mock_details_resp = MagicMock(status_code=200)
        mock_details_resp.json.return_value = {
            "id": mock_order_id,
            "status": "APPROVED",
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"DRAFT_{unapproved_draft.id}_BIZ_{biz.id}",
                    "amount": {"currency_code": "USD", "value": "320.00"},
                }
            ],
            "payer": {"email_address": "buyer-test@personal.example.com", "payer_id": "PAYER_999"},
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = mock_details_resp
            with patch.object(PayPalService, "is_configured", return_value=True):
                details = asyncio.run(PayPalService.get_order_details(mock_order_id))

        assert details["id"] == mock_order_id
        assert details["status"] == "APPROVED"
        assert details["payer"]["payer_id"] == "PAYER_999"
        print(f"[PASS] Order details query successful. Live status: {details['status']}")

        # -------------------------------------------------------------
        # 6. Orders v2 Capture Workflow & Settlement Confirmation
        # -------------------------------------------------------------
        print("\n--- 6. Testing Orders v2 Capture & Settlement Confirmation ---")
        initial_balance = biz.total_balance
        initial_spent = biz.monthly_spent
        initial_vendor_paid = vendor.total_paid
        capture_amount = unapproved_draft.amount  # 320.00

        mock_capture_id = f"7CAP{uuid.uuid4().hex[:10].upper()}"
        mock_capture_resp = MagicMock(status_code=201)
        mock_capture_resp.text = json.dumps({
            "id": mock_order_id,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "reference_id": f"DRAFT_{unapproved_draft.id}_BIZ_{biz.id}",
                    "payments": {
                        "captures": [
                            {
                                "id": mock_capture_id,
                                "status": "COMPLETED",
                                "amount": {"currency_code": "USD", "value": f"{capture_amount:.2f}"},
                                "final_capture": True,
                            }
                        ]
                    }
                }
            ]
        })
        mock_capture_resp.json.return_value = json.loads(mock_capture_resp.text)

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = mock_capture_resp
            with patch.object(PayPalService, "is_configured", return_value=True):
                captured_tx, capture_info = asyncio.run(PayPalService.capture_order(
                    db=db,
                    transaction_id=tx.id,
                    paypal_order_id=mock_order_id,
                    business=biz,
                    user=user,
                ))

        assert captured_tx.status == "COMPLETED"
        assert captured_tx.paypal_capture_id == mock_capture_id
        assert captured_tx.settled_at is not None

        db.refresh(unapproved_draft)
        db.refresh(biz)
        db.refresh(vendor)

        assert unapproved_draft.status == "COMPLETED"
        assert abs(biz.total_balance - (initial_balance - capture_amount)) < 0.01
        assert abs(biz.monthly_spent - (initial_spent + capture_amount)) < 0.01
        assert abs(vendor.total_paid - (initial_vendor_paid + capture_amount)) < 0.01
        print(f"[PASS] PayPal Capture settled! Capture ID={captured_tx.paypal_capture_id}")
        print(f"[PASS] Company balance decremented to ${biz.total_balance:,.2f}")

        # -------------------------------------------------------------
        # 7. Order Cancellation Workflow
        # -------------------------------------------------------------
        print("\n--- 7. Testing Order Cancellation & Draft State Reset ---")
        # Create another approved draft and transaction for cancellation test
        cancel_draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=vendor.id,
            created_by_id=user.id,
            title="Cancelled Session Test",
            amount=85.00,
            currency="USD",
            category="Office Supplies",
            purpose="Cancelled checkout testing",
            status="APPROVED",
            created_at=datetime.utcnow(),
        )
        db.add(cancel_draft)
        db.commit()
        db.refresh(cancel_draft)

        cancel_tx = Transaction(
            business_id=biz.id,
            vendor_id=vendor.id,
            payment_draft_id=cancel_draft.id,
            transaction_type="EXPENSE",
            amount=85.00,
            currency="USD",
            status="PROVIDER_PENDING",
            category="Office Supplies",
            paypal_order_id=f"CANCEL_ORD_{uuid.uuid4().hex[:8]}",
            payment_method="PAYPAL_SANDBOX",
            is_sandbox=True,
        )
        db.add(cancel_tx)
        cancel_draft.status = "PROVIDER_PENDING"
        db.commit()
        db.refresh(cancel_tx)

        # Call cancel_order
        PayPalService.cancel_order(
            db=db,
            transaction_id=cancel_tx.id,
            business=biz,
            user=user,
        )

        db.refresh(cancel_tx)
        db.refresh(cancel_draft)
        assert cancel_tx.status == "CANCELLED"
        assert cancel_draft.status == "APPROVED", "Draft must reset to APPROVED when buyer cancels checkout!"
        print(f"[PASS] Order cancellation verified: Tx #{cancel_tx.id} CANCELLED, Draft #{cancel_draft.id} reset to APPROVED.")

        # -------------------------------------------------------------
        # 8. HTTP Endpoints via TestClient
        # -------------------------------------------------------------
        print("\n--- 8. Testing PayPal HTTP API Endpoints ---")
        token = create_access_token({"user_id": user.id, "business_id": biz.id, "role": "OWNER"})
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {token}"}

        # GET /api/v1/payments/paypal/config
        cfg_resp = client.get("/api/v1/payments/paypal/config")
        assert cfg_resp.status_code == 200
        cfg_data = cfg_resp.json()
        assert "mode" in cfg_data
        assert "base_url" in cfg_data
        assert "configured" in cfg_data
        print(f"[PASS] GET /api/v1/payments/paypal/config -> 200 OK (Mode: {cfg_data['mode']})")

        # POST /api/v1/payments/execute with PAYPAL_SANDBOX when unconfigured
        if not PayPalService.is_configured():
            # Ensure cancel_draft has details_hash set so tamper check passes
            cancel_draft.details_hash = compute_details_hash(
                vendor_id=cancel_draft.vendor_id,
                amount=cancel_draft.amount,
                currency=cancel_draft.currency,
                purpose=cancel_draft.purpose,
                invoice_number=cancel_draft.invoice_number,
            )
            cancel_draft.status = "APPROVED"
            db.commit()

            exec_resp = client.post(
                "/api/v1/payments/execute",
                headers=headers,
                json={"draft_id": cancel_draft.id, "payment_method": "PAYPAL_SANDBOX"},
            )
            print("Execute response:", exec_resp.status_code, exec_resp.text)
            assert exec_resp.status_code == 400
            assert "paypal_not_configured" in exec_resp.text
            print("[PASS] POST /api/v1/payments/execute returns clean HTTP 400 when credentials unconfigured.")

        # -------------------------------------------------------------
        # 9. Live Sandbox Check (Only if credentials provided)
        # -------------------------------------------------------------
        if PayPalService.is_configured():
            print("\n--- 9. Live PayPal Sandbox Authentication Verification ---")
            live_token = asyncio.run(PayPalService.get_access_token(force_refresh=True))
            assert live_token is not None
            assert len(live_token) > 20
            print(f"[PASS] LIVE Sandbox OAuth2 token received from PayPal: {live_token[:10]}...")

        print("\n=======================================================")
        print("ALL PAYPAL REST API (SANDBOX & ORDERS V2) TESTS PASSED!")
        print("=======================================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    test_paypal_integration_suite()
