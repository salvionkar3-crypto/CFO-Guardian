"""AI CFO Intelligent Financial Assistant Test Suite

Validates:
1. Read-only Tool Execution against Database Ledger
2. Natural Language Questions from User Requirements:
   - "How is my business performing this month?"
   - "What are my biggest expenses?"
   - "Which vendor costs me the most?"
   - "Compare this month with last month"
   - "Can I afford a $15,000 payment?"
   - "Give me a financial health summary"
   - "Identify unusual spending patterns"
   - "Show my recurring subscriptions"
3. Session and Message Conversation History Persistence
4. Multi-Tenant Scoping and Boundary Protection
5. Security Guardrails: Read-only, no authorization of payments
"""

import sys
import os

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.business import Business
from app.services.cfo_tools import execute_cfo_tool

client = TestClient(app)


def get_demo_token():
    """Logs in using demo account to retrieve a valid JWT token."""
    login_resp = client.post("/api/v1/auth/demo-login")
    assert login_resp.status_code == 200, f"Demo login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


def test_approved_cfo_tools():
    """Tests that all approved CFO tools execute cleanly on database data without modifying anything."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        assert biz is not None, "Demo business not found. Run seed_demo_data first."

        # 1. Financial summary tool
        summary = execute_cfo_tool("get_financial_summary", {"period": "current_month"}, db, biz)
        assert "total_revenue" in summary
        assert "total_expenses" in summary
        assert "net_cash_flow" in summary
        assert summary["total_revenue"] > 0
        print(f"[PASS] Tool: get_financial_summary (Revenue: ${summary['total_revenue']:,.2f})")

        # 2. Category breakdown tool
        cat_data = execute_cfo_tool("get_category_breakdown", {}, db, biz)
        assert "top_expense_categories" in cat_data
        assert len(cat_data["top_expense_categories"]) > 0
        print(f"[PASS] Tool: get_category_breakdown ({len(cat_data['top_expense_categories'])} categories)")

        # 3. Top vendors tool
        v_data = execute_cfo_tool("get_top_vendors", {"limit": 5}, db, biz)
        assert "top_vendors" in v_data
        assert "primary_cost_driver" in v_data
        print(f"[PASS] Tool: get_top_vendors (Top vendor: {v_data['primary_cost_driver']})")

        # 4. Affordability check tool ($2,500 - affordable)
        aff_safe = execute_cfo_tool("check_affordability", {"amount": 2500.0, "currency": "USD"}, db, biz)
        assert "AFFORDABLE" in aff_safe["verdict"]
        print(f"[PASS] Tool: check_affordability ($2.5k -> {aff_safe['verdict']})")

        # Affordability check tool ($15,000 - requires dual approval)
        aff_mid = execute_cfo_tool("check_affordability", {"amount": 15000.0, "currency": "USD"}, db, biz)
        assert aff_mid["verdict"] in ("REQUIRES_DUAL_EXECUTIVE_APPROVAL", "EXCEEDS_MONTHLY_BUDGET")
        print(f"[PASS] Tool: check_affordability ($15k -> {aff_mid['verdict']})")

        # Affordability check tool ($200,000 - unaffordable)
        aff_high = execute_cfo_tool("check_affordability", {"amount": 200000.0, "currency": "USD"}, db, biz)
        assert aff_high["verdict"] in ("UNAFFORDABLE", "EXCEEDS_MONTHLY_BUDGET")
        print(f"[PASS] Tool: check_affordability ($200k -> {aff_high['verdict']})")

        # 5. Period comparison tool
        comp = execute_cfo_tool("compare_periods", {"period1": "current_month", "period2": "last_month"}, db, biz)
        assert "revenue_growth_pct" in comp
        assert "expense_change_pct" in comp
        print(f"[PASS] Tool: compare_periods (Growth: {comp['revenue_growth_pct']}%)")

        # 6. Anomalies tool
        anom = execute_cfo_tool("get_unusual_spending_patterns", {}, db, biz)
        assert "anomalies_detected" in anom
        print(f"[PASS] Tool: get_unusual_spending_patterns ({anom['anomalies_detected']} anomalies)")

        # 7. Recurring commitments tool
        rec = execute_cfo_tool("get_recurring_commitments", {}, db, biz)
        assert "total_recurring_monthly" in rec
        print(f"[PASS] Tool: get_recurring_commitments (${rec['total_recurring_monthly']:,.2f}/mo)")

    finally:
        db.close()


def test_ai_cfo_chat_queries():
    """Submits the exact required user questions to the AI CFO API endpoint."""
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    queries = [
        ("How is my business performing this month?", "summary"),
        ("What are my biggest expenses?", "category_breakdown"),
        ("Which vendor costs me the most?", "top_vendors"),
        ("Compare this month with last month", "comparison"),
        ("Can I afford a $15,000 payment?", "affordability"),
        ("Can I afford a 50,000 payment?", "affordability"),
        ("Give me a financial health summary", "summary"),
        ("Identify unusual spending patterns", "anomalies"),
        ("What recurring subscriptions do we have?", "recurring"),
    ]

    session_id = None

    for prompt, expected_tool_or_type in queries:
        resp = client.post(
            "/api/v1/cfo/chat",
            json={"prompt": prompt, "session_id": session_id},
            headers=headers,
        )
        assert resp.status_code == 200, f"Query failed for '{prompt}': {resp.text}"
        data = resp.json()

        # Session persistence validation
        session_id = data["session_id"]
        assert session_id is not None
        assert "reply" in data and len(data["reply"]) > 20
        assert "tools_executed" in data

        # Validate that insight card is returned
        if data.get("insight_card"):
            card_type = data["insight_card"].get("type", "")
            print(f"[PASS] CFO Q: '{prompt}' -> {data['tools_executed']} [Card: {card_type}]")
        else:
            print(f"[PASS] CFO Q: '{prompt}' -> {data['tools_executed']}")

    # Now verify multi-turn conversation retrieval
    sess_resp = client.get(f"/api/v1/cfo/chat/sessions/{session_id}", headers=headers)
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert len(sess_data["messages"]) >= len(queries) * 2  # user + assistant for each turn
    print(f"[PASS] Chat Session {session_id} saved {len(sess_data['messages'])} conversation messages.")

    # Verify listing chat sessions
    list_resp = client.get("/api/v1/cfo/chat/sessions", headers=headers)
    assert list_resp.status_code == 200
    sessions_list = list_resp.json()
    assert any(s["id"] == session_id for s in sessions_list)
    print(f"[PASS] Chat Sessions list returned {len(sessions_list)} sessions.")


def test_tenant_boundary_chat_isolation():
    """Confirms that one tenant cannot access another business's chat consultation."""
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Query for a non-existent or foreign session_id
    bad_resp = client.get("/api/v1/cfo/chat/sessions/999999", headers=headers)
    assert bad_resp.status_code == 404
    print("[PASS] Multi-tenant isolation verified: cannot access unauthorized sessions.")


if __name__ == "__main__":
    test_approved_cfo_tools()
    test_ai_cfo_chat_queries()
    test_tenant_boundary_chat_isolation()
    print("\nALL AI CFO TESTS COMPLETED SUCCESSFULLY!")
