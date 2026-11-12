"""Backend Sanity and Integration Tests

Verifies that the entire FastAPI backend, database, authentication,
CFO analysis, Guardian AI risk scoring, and audit logging work end-to-end.
"""

import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_headers():
    resp = client.post("/api/v1/auth/demo-login")
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "connected"
    print("[PASS] Health Check Passed:", data["status"], "DB:", data["database"]["type"])


def test_authentication():
    # Test registration of new user & business
    email = f"test_owner_{int(os.getpid())}@company.com"
    reg_payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Test Owner",
        "business_name": "Test Enterprise LLC",
        "currency": "USD",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    reg_data = reg_resp.json()
    assert reg_data["user"]["email"] == email
    assert reg_data["business"]["name"] == "Test Enterprise LLC"
    print(f"[PASS] Authentication Register: {email} -> {reg_data['business']['name']}")

    # Test login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    assert "access_token" in login_resp.json()
    print("[PASS] Authentication Login verified.")


def test_company_metrics():
    headers = get_auth_headers()
    response = client.get("/api/v1/cfo/metrics", headers=headers)
    assert response.status_code == 200, response.text
    metrics = response.json()
    assert "total_balance" in metrics
    assert "monthly_budget" in metrics
    print(f"[PASS] Company Metrics: {metrics['name']} | Balance: ${metrics['total_balance']:,}")


def test_cfo_and_guardian_flow():
    headers = get_auth_headers()

    # 1. Ingest invoice
    invoice_payload = {
        "title": "AWS Cloud Infrastructure - Monthly",
        "vendor": "Amazon Web Services",
        "vendor_email": "billing@aws.amazon.com",
        "category": "Infrastructure",
        "amount": 320.00,
        "currency": "USD",
        "notes": "Production EC2 instances and Postgres RDS cluster",
    }
    cfo_resp = client.post("/api/v1/cfo/analyze", json=invoice_payload, headers=headers)
    assert cfo_resp.status_code == 200, cfo_resp.text
    cfo_data = cfo_resp.json()
    decision_id = cfo_data["decision_id"]
    print(f"[PASS] CFO Analysis for Decision #{decision_id}: {cfo_data['recommendation']}")

    # 2. Guardian AI risk evaluation
    risk_resp = client.post("/api/v1/guardian/assess-risk", json={"decision_id": decision_id}, headers=headers)
    assert risk_resp.status_code == 200, risk_resp.text
    risk_data = risk_resp.json()
    print(f"[PASS] Guardian AI Risk: Verdict={risk_data['verdict']}, Score={risk_data['risk_score']}/100")

    # 3. Verify audit log creation
    audit_resp = client.get(f"/api/v1/audit/logs?decision_id={decision_id}", headers=headers)
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    assert len(logs) >= 2
    print(f"[PASS] Audit Trail Verified: {len(logs)} audit checkpoints recorded.")

    # 4. Verify explainability report
    explain_resp = client.get(f"/api/v1/audit/explain/{decision_id}", headers=headers)
    assert explain_resp.status_code == 200, explain_resp.text
    explain_data = explain_resp.json()
    assert explain_data["decision_id"] == decision_id
    print(f"[PASS] Explainability Report: {explain_data['guardian_security_summary']}")


if __name__ == "__main__":
    test_health()
    test_authentication()
    test_company_metrics()
    test_cfo_and_guardian_flow()
    print("\nALL BACKEND SANITY & INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
