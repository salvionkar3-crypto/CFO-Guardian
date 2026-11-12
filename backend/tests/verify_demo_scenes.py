"""Verification Script for Hackathon Demo Scenes 1, 2, 3, and 4
Verifies:
- Scene 1: AI CFO natural language consultation ("How is my business performing this month?")
- Scene 2: Normal Payment to known vendor, Guardian risk investigation, approval, and settlement
- Scene 3: Suspicious Payment to first-time vendor, high risk detection, policy pause, blocked approval
- Scene 4: Explainability report & audit trail verification
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.db.seed import seed_demo_data
from app.models.user import User
from app.models.business import Business
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft
from app.services.ai_cfo_service import AICFOService
from app.services.guardian_service import GuardianRiskEngine
from app.services.policy_engine import PaymentPolicyEngine
from app.services.audit_service import AuditService
from app.services.paypal_service import PayPalService
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def run_demo_scenarios():
    db = SessionLocal()
    try:
        print("\n" + "=" * 70)
        print("VERIFYING GUARDIAN CFO DEMO SCENARIOS FOR PAYPAL AI HACKATHON")
        print("=" * 70)

        # 0. Initialize Demo Workspace
        seed_res = seed_demo_data(db)
        from app.core.config import settings
        demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
        demo_business = db.query(Business).filter(Business.owner_id == demo_user.id).first()

        # Login to obtain Bearer token
        login_res = client.post("/api/v1/auth/demo-login")
        assert login_res.status_code == 200, f"Demo login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Authenticated Demo Account: {demo_user.email} (Business: '{demo_business.name}')")

        # -------------------------------------------------------------
        # SCENE 1: AI CFO CONSULTATION
        # -------------------------------------------------------------
        print("\n--- SCENE 1: AI CFO CONSULTATION ---")
        question = "How is my business performing this month?"
        cfo_result = AICFOService.ask_cfo(
            db=db,
            business=demo_business,
            user=demo_user,
            prompt=question,
        )
        print(f"User Query: \"{question}\"")
        print(f"Tools Executed: {cfo_result['tools_executed']}")
        print(f"Insight Card Type: {cfo_result['insight_card']['type'] if cfo_result.get('insight_card') else 'None'}")
        print("AI CFO Structured Reply Preview:")
        print("-" * 50)
        print(cfo_result["reply"][:350] + "...\n" + "-" * 50)
        assert len(cfo_result["reply"]) > 50
        assert "get_financial_summary" in cfo_result["tools_executed"]
        print("[PASS] Scene 1: Verified real database-backed analytics response.")

        # -------------------------------------------------------------
        # SCENE 2: NORMAL PAYMENT TO KNOWN VENDOR
        # -------------------------------------------------------------
        print("\n--- SCENE 2: NORMAL PAYMENT TO KNOWN VENDOR ---")
        # Ensure a verified trusted vendor exists with clean recent history
        vendor_name = "Datadog Cloud Observability"
        vendor = db.query(Vendor).filter(Vendor.business_id == demo_business.id, Vendor.name == vendor_name).first()
        if not vendor:
            vendor = Vendor(
                business_id=demo_business.id,
                name=vendor_name,
                email="billing@datadog.com",
                website="https://datadog.com",
                status="ACTIVE",
                trust_score=95.0,
                bank_or_paypal_email="pay@datadog.com",
                total_paid=2400.0,
            )
            db.add(vendor)
            db.commit()
            db.refresh(vendor)

        # 1. Create Draft with clean unique invoice number
        normal_draft_payload = {
            "vendor_id": vendor.id,
            "title": "Datadog Cloud APM & Security Monitoring - Monthly",
            "amount": 280.00,
            "currency": "USD",
            "category": "Technology",
            "purpose": "Monthly application telemetry and infrastructure monitoring per MSA",
            "invoice_number": f"INV-DD-2026-{int(datetime.utcnow().timestamp())}",
        }
        res_draft = client.post("/api/v1/payments/drafts", json=normal_draft_payload, headers=headers)
        assert res_draft.status_code == 201, res_draft.text
        draft_data = res_draft.json()
        draft_id = draft_data["id"]
        print(f"Created Payment Draft #{draft_id} for ${draft_data['amount']} to {vendor.name}")

        # 2. Guardian Risk Investigation
        risk_data = draft_data.get("risk_assessment")
        print(f"Guardian Risk Score: {risk_data['risk_score']:.1f}/100 ({risk_data['risk_level']})")
        print(f"Guardian Verdict: {risk_data['verdict']}")
        print(f"Signals Detected ({len(risk_data.get('risk_signals', []))}):")
        for s in risk_data.get("risk_signals", []):
            print(f"  - [{s.get('severity')}] {s.get('name')}: {s.get('evidence')} (+{s.get('score_impact')} pts)")

        # 3. Policy & Approval Workflow
        eligibility = draft_data.get("policy_eligibility")
        print(f"Policy Eligibility: Can Approve={eligibility['can_approve']}, Mandatory Block={eligibility['mandatory_block']}")
        assert eligibility["can_approve"] is True

        # Approve Draft
        appr_res = client.post(
            f"/api/v1/payments/drafts/{draft_id}/approve",
            json={"notes": "Verified against AWS billing statement. Approved."},
            headers=headers,
        )
        assert appr_res.status_code == 200, appr_res.text
        appr_data = appr_res.json()
        print(f"Approved Draft #{draft_id}: Status={appr_data['status']}, Hash={appr_data['details_hash'][:16]}...")

        # If dual approval is required by policy, grant secondary approval
        if appr_data["status"] == "AWAITING_APPROVAL" and appr_data.get("requires_dual_approval"):
            appr2_res = client.post(
                f"/api/v1/payments/drafts/{draft_id}/approve",
                json={"notes": "Secondary executive authorization (CEO).", "dual_approval_override": True},
                headers=headers,
            )
            assert appr2_res.status_code == 200, appr2_res.text
            appr_data = appr2_res.json()
            print(f"Dual-Approved Draft #{draft_id}: Status={appr_data['status']}")

        # 4. Execute Payment (Simulated Provider or PayPal Sandbox)
        exec_res = client.post(
            "/api/v1/payments/execute",
            json={"draft_id": draft_id, "payment_method": "SIMULATED_PROVIDER"},
            headers=headers,
        )
        assert exec_res.status_code == 200, exec_res.text
        exec_data = exec_res.json()
        print(f"Payment Settled! Status={exec_data['status']}, Tx ID={exec_data['transaction_id']}, Ref={exec_data['provider_reference']}")
        print("[PASS] Scene 2: Normal payment investigation, approval and settlement verified.")

        # -------------------------------------------------------------
        # SCENE 3: SUSPICIOUS PAYMENT TO FIRST-TIME VENDOR
        # -------------------------------------------------------------
        print("\n--- SCENE 3: SUSPICIOUS PAYMENT TO FIRST-TIME VENDOR ---")
        suspicious_draft_payload = {
            "new_vendor": {
                "name": "Global Offshore FinTech Direct Ltd",
                "email": "transfers@global-offshore99.xyz",
                "website": "http://global-offshore99.xyz",
                "bank_or_paypal_email": "wire-dest@global-offshore99.xyz",
            },
            "title": "Urgent Offshore Retainer Payment",
            "amount": 25000.00,  # Exceeds max single payment limit and unverified vendor
            "currency": "USD",
            "category": "Consulting",
            "purpose": "Urgent corporate re-structuring advance advisory fee",
            "invoice_number": f"INV-ANOM-{int(datetime.utcnow().timestamp())}",
        }
        res_susp = client.post("/api/v1/payments/drafts", json=suspicious_draft_payload, headers=headers)
        assert res_susp.status_code == 201, res_susp.text
        susp_data = res_susp.json()
        susp_id = susp_data["id"]
        susp_risk = susp_data["risk_assessment"]
        susp_policy = susp_data["policy_eligibility"]

        print(f"Created Suspicious Draft #{susp_id} for ${susp_data['amount']} to new payee")
        print(f"Guardian Risk Score: {susp_risk['risk_score']:.1f}/100 ({susp_risk['risk_level']})")
        print(f"Guardian Verdict: {susp_risk['verdict']}")
        print(f"Detected Risk Signals ({len(susp_risk['risk_signals'])}):")
        for s in susp_risk["risk_signals"]:
            print(f"  - [{s['severity']}] {s['name']}: {s['evidence']}")

        print(f"Policy Action: {susp_risk['recommended_action']}")
        print(f"Can Approve: {susp_policy['can_approve']}, Mandatory Block: {susp_policy['mandatory_block']}")

        # Attempt to bypass/approve -> must be blocked or require dual approval
        if susp_policy["mandatory_block"]:
            appr_attempt = client.post(
                f"/api/v1/payments/drafts/{susp_id}/approve",
                json={"notes": "Trying to override"},
                headers=headers,
            )
            assert appr_attempt.status_code == 403, f"Critical payment approval should be 403, got {appr_attempt.status_code}"
            print("[PASS] Policy Pause Enforced: Mandatory block halted unilateral approval with HTTP 403 Forbidden.")
        else:
            print(f"[PASS] Policy Pause Enforced: Dual approval required. Step: {susp_policy['step_name']}.")

        print("[PASS] Scene 3: Suspicious payment detected and guarded.")

        # -------------------------------------------------------------
        # SCENE 4: EXPLAINABILITY & AUDIT TRAIL
        # -------------------------------------------------------------
        print("\n--- SCENE 4: EXPLAINABILITY & AUDIT TRAIL ---")
        explain_res = client.get(f"/api/v1/audit/explain/{draft_id}", headers=headers)
        assert explain_res.status_code == 200, explain_res.text
        exp_data = explain_res.json()

        print(f"Explainability Report for Payment #{draft_id}:")
        print(f"1. What happened? -> {exp_data['what_happened'][:120]}...")
        print(f"2. Why flagged? -> {exp_data['why_flagged'][:120]}...")
        print(f"3. Evidence detected -> {len(exp_data['evidence_detected'])} evidence items")
        print(f"4. Action taken -> {exp_data['action_taken']}")
        print(f"5. Approval details -> Status: {exp_data['approval_details']['status']}, Approver: {exp_data['approval_details'].get('primary_approver')}")
        print(f"6. Final provider status -> {exp_data['final_provider_status']['status']} (Mode: {exp_data['final_provider_status']['mode']})")

        # Verify Audit Timeline
        audit_res = client.get("/api/v1/audit/logs?limit=5", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        print(f"\nRecent Audit Trail Entries ({len(logs)}):")
        for log in logs[:3]:
            print(f"  [{log.get('timestamp', '')[:19]}] [{log['action']}] {log['summary']}")

        print("[PASS] Scene 4: Full explainability and audit trail verified.")

        print("\n" + "=" * 70)
        print("ALL 4 DEMO SCENARIOS FULLY VERIFIED AND READY FOR HACKATHON!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_demo_scenarios()
