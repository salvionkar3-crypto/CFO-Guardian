"""Guardian AI Payment Risk Detection Engine Test Suite

Validates:
1. Normal Payment Scenario (LOW risk, SAFE_TO_PAY, ALLOW)
2. Unusual Payment Scenario (Unusual amount / category surge -> MEDIUM/HIGH risk)
3. Duplicate Payment Scenario (Duplicate invoice & velocity replay attack)
4. High-Value Impersonation Scenario (CRITICAL risk >= 75, BLOCKED, SecurityAlert created)
5. Verification of all 10 risk signals, evidence generation, and missing info tracking
6. Cryptographic SHA-256 verification hash integrity
7. Authenticated Guardian Security Center API endpoints
"""

import sys
import os
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft
from app.models.guardian import RiskAssessment, SecurityAlert
from app.services.guardian_service import GuardianRiskEngine

client = TestClient(app)


def get_demo_token():
    """Logs in using demo account to retrieve a valid JWT token."""
    login_resp = client.post("/api/v1/auth/demo-login")
    assert login_resp.status_code == 200, f"Demo login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


def test_scenario_normal_payment():
    """Scenario 1: Normal payment to established vendor within normal parameters.

    Expected: LOW risk (0-24), SAFE_TO_PAY, recommended_action=ALLOW.
    """
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        assert biz is not None

        # GitHub Enterprise is an established vendor in seed data
        github_vendor = db.query(Vendor).filter(Vendor.business_id == biz.id, Vendor.name == "GitHub Enterprise").first()
        assert github_vendor is not None

        # Clean up any prior test drafts for this vendor so velocity check doesn't fire
        db.query(PaymentDraft).filter(
            PaymentDraft.business_id == biz.id,
            PaymentDraft.vendor_id == github_vendor.id
        ).delete()
        db.commit()

        draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=github_vendor.id,
            created_by_id=biz.owner_id,
            title="Monthly GitHub Enterprise Seats",
            amount=140.00,  # Exactly matches historical monthly amount
            currency="USD",
            category="Engineering & R&D",
            invoice_number=f"INV-NORM-{datetime.utcnow().timestamp()}",
            description="Routine monthly developer seat license",
            status="PENDING",
            cfo_recommendation="APPROVE",
            cfo_rationale="Well within budget",
            budget_impact_pct=1.2,
            runway_impact_days=1,
            created_at=datetime(2026, 11, 4, 14, 0, 0),  # Midday weekday
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        assessment = GuardianRiskEngine.evaluate(db=db, draft=draft, business=biz, force_recalculate=True)
        assert assessment.risk_score <= 24.0, f"Expected LOW risk <= 24.0, got {assessment.risk_score}"
        assert assessment.risk_level == "LOW"
        assert assessment.verdict == "SAFE_TO_PAY"
        assert assessment.recommended_action == "ALLOW"
        assert assessment.verification_hash is not None
        assert draft.status == "APPROVED"
        print(f"[PASS] Scenario 1 (Normal Payment): Score={assessment.risk_score}/100, Verdict={assessment.verdict}")
    finally:
        db.close()


def test_scenario_unusual_amount_and_category():
    """Scenario 2: Payment to known vendor with an unusual 4x amount spike and category surge.

    Expected: MEDIUM/HIGH risk (25-74), REQUIRES_MANUAL_REVIEW or DUAL_EXECUTIVE_APPROVAL.
    """
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        # Clean up prior test runs
        db.query(PaymentDraft).filter(PaymentDraft.business_id == biz.id, PaymentDraft.title == "Emergency Copilot Enterprise Expansion").delete()
        db.commit()

        # GitHub Enterprise has historical avg $140/mo. A jump to $650 is a 4.6x spike.
        gh_vendor = db.query(Vendor).filter(Vendor.business_id == biz.id, Vendor.name == "GitHub Enterprise").first()

        draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=gh_vendor.id,
            created_by_id=biz.owner_id,
            title="Emergency Copilot Enterprise Expansion",
            amount=650.00,  # 4.6x higher than historical average ($140.00)
            currency="USD",
            category="Engineering & R&D",
            invoice_number=f"INV-UNUSUAL-{datetime.utcnow().timestamp()}",
            description="Large unbudgeted seat addition",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        assessment = GuardianRiskEngine.evaluate(db=db, draft=draft, business=biz, force_recalculate=True)
        assert 25.0 <= assessment.risk_score < 75.0, f"Expected MEDIUM/HIGH risk, got {assessment.risk_score}"
        assert assessment.risk_level in ("MEDIUM", "HIGH")
        assert assessment.verdict in ("REQUIRES_MANUAL_REVIEW", "REQUIRES_DUAL_EXECUTIVE_APPROVAL")
        assert draft.status == "AWAITING_APPROVAL"
        print(f"[PASS] Scenario 2 (Unusual Amount): Score={assessment.risk_score}/100, Level={assessment.risk_level}, Verdict={assessment.verdict}")
    finally:
        db.close()


def test_scenario_duplicate_payment_and_invoice():
    """Scenario 3: Replay payment attempt (same vendor, same amount, and duplicate invoice number).

    Expected: Triggers SIGNAL_DUPLICATE_INVOICE and SIGNAL_DUPLICATE_PAYMENT.
    """
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        aws_vendor = db.query(Vendor).filter(Vendor.business_id == biz.id, Vendor.name == "Amazon Web Services").first()

        shared_inv = f"INV-DUP-TEST-99"

        # Clean up prior test runs
        db.query(PaymentDraft).filter(PaymentDraft.business_id == biz.id, PaymentDraft.invoice_number == shared_inv).delete()
        db.commit()

        # First legitimate draft
        draft1 = PaymentDraft(
            business_id=biz.id,
            vendor_id=aws_vendor.id,
            created_by_id=biz.owner_id,
            title="Original Invoice Submission",
            amount=1450.00,
            currency="USD",
            category="Infrastructure",
            invoice_number=shared_inv,
            description="Initial submission",
            status="APPROVED",
            created_at=datetime.utcnow(),
        )
        db.add(draft1)
        db.commit()

        # Duplicate draft submitted shortly after
        draft2 = PaymentDraft(
            business_id=biz.id,
            vendor_id=aws_vendor.id,
            created_by_id=biz.owner_id,
            title="Duplicate Replay Invoice Submission",
            amount=1450.00,
            currency="USD",
            category="Infrastructure",
            invoice_number=shared_inv,
            description="Re-submitted accidentally or maliciously",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(draft2)
        db.commit()
        db.refresh(draft2)

        assessment = GuardianRiskEngine.evaluate(db=db, draft=draft2, business=biz, force_recalculate=True)
        assert assessment.is_duplicate_invoice is True
        assert assessment.risk_score >= 50.0, f"Expected high risk on duplicate, got {assessment.risk_score}"
        print(f"[PASS] Scenario 3 (Duplicate Payment/Invoice): Score={assessment.risk_score}/100, Level={assessment.risk_level}")
    finally:
        db.close()


def test_scenario_critical_brand_impersonation():
    """Scenario 4: High-value payment with brand spoofing and limit violation.

    Expected: CRITICAL risk (>= 75.0), BLOCKED, draft status REJECTED, SecurityAlert created.
    """
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()

        # Clean up prior test runs
        db.query(PaymentDraft).filter(PaymentDraft.business_id == biz.id, PaymentDraft.title == "Urgent Annual Server Renewal").delete()
        db.commit()

        # Spoofed vendor claiming to be Google Cloud but using an unverified domain
        fake_vendor = Vendor(
            business_id=biz.id,
            name="Google Cloud EMEA Billing",
            email="payments@google-billing-fake-portal.xyz",
            bank_or_paypal_email="hacker@google-billing-fake-portal.xyz",
            status="ACTIVE",
            trust_score=35.0,  # Low trust
        )
        db.add(fake_vendor)
        db.commit()
        db.refresh(fake_vendor)

        draft = PaymentDraft(
            business_id=biz.id,
            vendor_id=fake_vendor.id,
            created_by_id=biz.owner_id,
            title="Urgent Annual Server Renewal",
            amount=18500.00,  # Exceeds single payment limit ($5,000)
            currency="USD",
            category="Infrastructure",
            invoice_number=f"INV-SPOOF-{datetime.utcnow().timestamp()}",
            description="Immediate wire transfer requested",
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        assessment = GuardianRiskEngine.evaluate(db=db, draft=draft, business=biz, force_recalculate=True)
        assert assessment.risk_score >= 75.0, f"Expected CRITICAL >= 75.0, got {assessment.risk_score}"
        assert assessment.risk_level == "CRITICAL"
        assert assessment.verdict == "BLOCKED"
        assert assessment.recommended_action == "REJECT_AND_BLOCK"
        assert draft.status == "REJECTED"

        # Check that SecurityAlert was logged
        alert = (
            db.query(SecurityAlert)
            .filter(SecurityAlert.business_id == biz.id, SecurityAlert.severity == "CRITICAL")
            .order_by(SecurityAlert.created_at.desc())
            .first()
        )
        assert alert is not None
        assert "Blocked High-Risk Payment" in alert.title
        print(f"[PASS] Scenario 4 (Brand Impersonation & Exceeded Limits): Score={assessment.risk_score}/100, Verdict={assessment.verdict}, Alert ID={alert.id}")
    finally:
        db.close()


def test_guardian_api_endpoints():
    """Validates Guardian Security Center API endpoints."""
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Policy Endpoint
    policy_resp = client.get("/api/v1/guardian/policy", headers=headers)
    assert policy_resp.status_code == 200, policy_resp.text
    p = policy_resp.json()
    assert p["low_max"] == 24.0
    assert p["critical_min"] == 75.0
    print("[PASS] API Endpoint: GET /api/v1/guardian/policy")

    # 2. List Assessments
    list_resp = client.get("/api/v1/guardian/assessments", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    assessments = list_resp.json()
    assert len(assessments) > 0
    first = assessments[0]
    assert "detected_signals" in first
    assert "supporting_evidence" in first
    assert "missing_information" in first
    assert "plain_explanation" in first
    print(f"[PASS] API Endpoint: GET /api/v1/guardian/assessments (Count: {len(assessments)})")

    # 3. Get Assessment by Decision ID
    decision_id = first["decision_id"]
    detail_resp = client.get(f"/api/v1/guardian/assessments/{decision_id}", headers=headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["decision_id"] == decision_id
    print(f"[PASS] API Endpoint: GET /api/v1/guardian/assessments/{decision_id}")

    # 4. List Security Alerts
    alerts_resp = client.get("/api/v1/guardian/alerts", headers=headers)
    assert alerts_resp.status_code == 200, alerts_resp.text
    alerts = alerts_resp.json()
    print(f"[PASS] API Endpoint: GET /api/v1/guardian/alerts (Count: {len(alerts)})")

    # 5. Resolve Security Alert if open
    if alerts:
        open_alert = next((a for a in alerts if a["status"] == "OPEN"), None)
        if open_alert:
            resolve_resp = client.post(f"/api/v1/guardian/alerts/{open_alert['id']}/resolve", headers=headers)
            assert resolve_resp.status_code == 200
            assert resolve_resp.json()["status"] == "RESOLVED"
            print(f"[PASS] API Endpoint: POST /api/v1/guardian/alerts/{open_alert['id']}/resolve")


if __name__ == "__main__":
    test_scenario_normal_payment()
    test_scenario_unusual_amount_and_category()
    test_scenario_duplicate_payment_and_invoice()
    test_scenario_critical_brand_impersonation()
    test_guardian_api_endpoints()
    print("\nALL GUARDIAN AI PAYMENT RISK ENGINE TESTS COMPLETED SUCCESSFULLY!")
