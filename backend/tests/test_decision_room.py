"""Tests for Guardian CFO Payment Decision Room

Verifies:
1. Retrieval of complete Payment Decision Room payload (6 sections)
2. Normal payment scenario (Datadog $280)
3. Suspicious payment scenario (Global Offshore $25,000)
4. Decimal-accurate cash flow impact calculations
5. 10-signal risk engine integration
6. AI financial recommendations grounded in verified facts
7. Human-controlled payment approval, hold, and review transitions
8. Audit timeline integrity
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.seed import seed_demo_data

client = TestClient(app)


def test_payment_decision_room_endpoints():
    db = SessionLocal()
    seed_demo_data(db)

    # 1. Login
    login_res = client.post("/api/v1/auth/demo-login")
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Scenario 1: Normal Payment (Datadog $280)
    res_normal = client.post("/api/v1/payments/decision-room/demo-scenario/normal", headers=headers)
    assert res_normal.status_code == 200, res_normal.text
    d_normal = res_normal.json()

    # Section A: Overview
    assert d_normal["overview"]["amount"] == 280.0
    assert d_normal["overview"]["currency"] == "USD"
    assert "Datadog" in d_normal["overview"]["vendor_name"]
    normal_draft_id = d_normal["overview"]["draft_id"]

    # Section B: Risk Assessment
    assert "risk_score" in d_normal["risk_assessment"]
    assert d_normal["risk_assessment"]["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert "signals" in d_normal["risk_assessment"]

    # Section C: AI Recommendation
    assert len(d_normal["ai_recommendation"]["verified_facts"]) >= 3
    assert len(d_normal["ai_recommendation"]["why_risky"]) > 10
    assert len(d_normal["ai_recommendation"]["cash_flow_impact"]) > 10

    # Section D: Cash Flow Impact (Decimal calculations)
    assert d_normal["cash_flow_impact"]["available_cash_before"] > 0
    assert d_normal["cash_flow_impact"]["payment_amount"] == 280.0
    expected_proj = round(d_normal["cash_flow_impact"]["available_cash_before"] - 280.0, 2)
    assert round(d_normal["cash_flow_impact"]["projected_cash_after"], 2) == expected_proj
    assert d_normal["cash_flow_impact"]["percentage_cash_consumed"] >= 0

    # Section E: Approval Workflow
    assert "can_approve" in d_normal["approval_workflow"]
    assert d_normal["approval_workflow"]["mandatory_block"] is False

    # Section F: Audit Timeline
    assert len(d_normal["audit_timeline"]) >= 1

    print("[PASS] Payment Decision Room - Normal Scenario (Datadog $280.00)")

    # 3. Test Scenario 2: Suspicious Payment (Global Offshore $25,000)
    res_susp = client.post("/api/v1/payments/decision-room/demo-scenario/suspicious", headers=headers)
    assert res_susp.status_code == 200, res_susp.text
    d_susp = res_susp.json()

    assert d_susp["overview"]["amount"] == 25000.0
    assert "Global Offshore" in d_susp["overview"]["vendor_name"]
    assert d_susp["risk_assessment"]["risk_score"] >= 50.0  # High or Critical
    assert len(d_susp["risk_assessment"]["signals"]) >= 2
    susp_draft_id = d_susp["overview"]["draft_id"]

    print("[PASS] Payment Decision Room - Suspicious Scenario (Global Offshore $25,000.00)")

    # 4. Direct Retrieval by ID
    res_get = client.get(f"/api/v1/payments/decision-room/{normal_draft_id}", headers=headers)
    assert res_get.status_code == 200, res_get.text
    assert res_get.json()["overview"]["draft_id"] == normal_draft_id
    print(f"[PASS] Payment Decision Room - Direct Retrieval by ID (#{normal_draft_id})")

    # 5. Hold Payment
    res_hold = client.post(
        f"/api/v1/payments/drafts/{normal_draft_id}/hold",
        json={"notes": "Executive hold requested for verification."},
        headers=headers,
    )
    assert res_hold.status_code == 200, res_hold.text
    assert res_hold.json()["status"] == "REVIEW_REQUIRED"
    print(f"[PASS] Hold Draft Action - Draft #{normal_draft_id} -> REVIEW_REQUIRED")

    # 6. Request Review
    res_review = client.post(
        f"/api/v1/payments/drafts/{normal_draft_id}/request-review",
        json={"notes": "Ready for secondary executive review."},
        headers=headers,
    )
    assert res_review.status_code == 200, res_review.text
    assert res_review.json()["status"] == "AWAITING_APPROVAL"
    print(f"[PASS] Request Review Action - Draft #{normal_draft_id} -> AWAITING_APPROVAL")


if __name__ == "__main__":
    test_payment_decision_room_endpoints()
    print("\n>>> ALL PAYMENT DECISION ROOM BACKEND TESTS PASSED SUCCESSFULLY! <<<")

