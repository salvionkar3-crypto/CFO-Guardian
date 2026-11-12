"""Financial Analytics Engine Test Suite

Validates deterministic financial calculations against known sample transactions:
1. Total revenue
2. Total expenses
3. Net cash flow (Revenue - Expenses)
4. Revenue growth % (((Current - Previous) / Previous) * 100)
5. Expense change % (((Current - Previous) / Previous) * 100)
6. Division by zero and missing data safety
7. Monthly timeline trends
8. Category breakdown & percentage share
9. Unusual expense increase detection
10. Recurring expense detection
11. Authenticated API endpoints
"""

import sys
import os
from datetime import datetime, timedelta

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.payment import Transaction
from app.services.analytics_service import AnalyticsService

client = TestClient(app)


def test_pure_math_formulas():
    """Validates math formulas with precision and edge case handling."""
    # 1. Standard positive change
    # ((18750 - 17000) / 17000) * 100 = 10.2941... -> 10.29%
    growth = AnalyticsService._safe_percentage_change(18750.0, 17000.0)
    assert growth == 10.29, f"Expected 10.29, got {growth}"

    # 2. Expense increase
    # ((5975 - 4290) / 4290) * 100 = 39.277... -> 39.28%
    exp_change = AnalyticsService._safe_percentage_change(5975.0, 4290.0)
    assert exp_change == 39.28, f"Expected 39.28, got {exp_change}"

    # 3. Expense decrease
    # ((3000 - 4000) / 4000) * 100 = -25.0%
    exp_decrease = AnalyticsService._safe_percentage_change(3000.0, 4000.0)
    assert exp_decrease == -25.0, f"Expected -25.0, got {exp_decrease}"

    # 4. Zero division handling
    assert AnalyticsService._safe_percentage_change(500.0, 0.0) == 100.0
    assert AnalyticsService._safe_percentage_change(0.0, 0.0) == 0.0
    assert AnalyticsService._safe_percentage_change(-200.0, 0.0) == -100.0

    print("[PASS] Pure math and zero-division handling verified.")


def test_service_calculations():
    """Tests database calculations on the demo business ledger."""
    db = SessionLocal()
    try:
        biz = db.query(Business).filter(Business.name == "Acme Autonomous Corp").first()
        assert biz is not None, "Demo business not found. Ensure seed_demo_data has run."

        # 1. Summary calculations
        summary = AnalyticsService.get_financial_summary(db=db, business=biz, period="current_month")
        assert summary.total_revenue > 0, "Current revenue must be > 0"
        assert summary.total_expenses > 0, "Current expenses must be > 0"

        # Verify: Net Cash Flow = Total Revenue - Total Expenses
        expected_ncf = round(summary.total_revenue - summary.total_expenses, 2)
        assert summary.net_cash_flow == expected_ncf, (
            f"Net cash flow formula mismatch: {summary.net_cash_flow} != {expected_ncf}"
        )
        print(f"[PASS] Financial Summary: Rev=${summary.total_revenue:,.2f}, Exp=${summary.total_expenses:,.2f}, Net=${summary.net_cash_flow:,.2f}")

        # 2. Monthly Trends
        trends = AnalyticsService.get_monthly_trends(db=db, business=biz, months_count=6)
        assert len(trends) == 6, f"Expected 6 trend periods, got {len(trends)}"
        for t in trends:
            expected_trend_net = round(t.revenue - t.expenses, 2)
            assert t.net_cash_flow == expected_trend_net, f"Trend net mismatch for {t.month}"
        print(f"[PASS] 6-Month Trends verified across {len(trends)} monthly periods.")

        # 3. Category Breakdown
        categories = AnalyticsService.get_category_breakdown(db=db, business=biz)
        assert len(categories.expenses_by_category) > 0, "Expense categories should be populated"
        assert len(categories.revenue_by_category) > 0, "Revenue categories should be populated"

        # Percentage sum check (~100% accounting for rounding)
        exp_pct_sum = sum(c.percentage_share for c in categories.expenses_by_category)
        assert 99.0 <= exp_pct_sum <= 101.0, f"Expense percentage shares must sum to ~100%, got {exp_pct_sum}"
        print(f"[PASS] Category Breakdown: {len(categories.expenses_by_category)} expense categories, sum={exp_pct_sum:.1f}%")

        # 4. Unusual Expense Anomaly Detection
        anomalies = AnalyticsService.identify_unusual_expense_increases(db=db, business=biz)
        assert len(anomalies) > 0, "Anomalies should be detected for spiked categories (AWS, Marketing)"
        anomaly_cats = [a.category for a in anomalies]
        print(f"[PASS] Unusual Expense Increases detected: {anomaly_cats}")

        # 5. Recurring Expenses Identification
        recurring = AnalyticsService.identify_recurring_expenses(db=db, business=biz)
        assert len(recurring.items) >= 3, f"Expected at least 3 recurring expenses, got {len(recurring.items)}"
        assert recurring.total_recurring_monthly > 0
        assert recurring.total_recurring_annual == round(recurring.total_recurring_monthly * 12.0, 2)
        recurring_names = [i.vendor_name for i in recurring.items]
        print(f"[PASS] Recurring Expenses: ${recurring.total_recurring_monthly:,.2f}/mo across {recurring_names}")

    finally:
        db.close()


def test_analytics_api_endpoints():
    """Tests the authenticated API endpoints with a live demo token."""
    # 1. Login to obtain JWT
    login_resp = client.post("/api/v1/auth/demo-login")
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET /api/v1/analytics/summary
    summary_resp = client.get("/api/v1/analytics/summary?period=current_month", headers=headers)
    assert summary_resp.status_code == 200, summary_resp.text
    summary_data = summary_resp.json()
    assert "total_revenue" in summary_data
    assert "total_expenses" in summary_data
    assert "net_cash_flow" in summary_data
    assert "revenue_growth_pct" in summary_data
    assert "expense_change_pct" in summary_data
    print("[PASS] API Endpoint: /api/v1/analytics/summary")

    # 3. GET /api/v1/analytics/trends
    trends_resp = client.get("/api/v1/analytics/trends?months=6", headers=headers)
    assert trends_resp.status_code == 200, trends_resp.text
    trends_data = trends_resp.json()
    assert len(trends_data) == 6
    print("[PASS] API Endpoint: /api/v1/analytics/trends")

    # 4. GET /api/v1/analytics/categories
    cat_resp = client.get("/api/v1/analytics/categories", headers=headers)
    assert cat_resp.status_code == 200, cat_resp.text
    cat_data = cat_resp.json()
    assert "expenses_by_category" in cat_data
    assert "revenue_by_category" in cat_data
    print("[PASS] API Endpoint: /api/v1/analytics/categories")

    # 5. GET /api/v1/analytics/anomalies
    anom_resp = client.get("/api/v1/analytics/anomalies", headers=headers)
    assert anom_resp.status_code == 200, anom_resp.text
    anom_data = anom_resp.json()
    assert isinstance(anom_data, list)
    print(f"[PASS] API Endpoint: /api/v1/analytics/anomalies ({len(anom_data)} anomalies reported)")

    # 6. GET /api/v1/analytics/recurring
    rec_resp = client.get("/api/v1/analytics/recurring", headers=headers)
    assert rec_resp.status_code == 200, rec_resp.text
    rec_data = rec_resp.json()
    assert "total_recurring_monthly" in rec_data
    assert "items" in rec_data
    print(f"[PASS] API Endpoint: /api/v1/analytics/recurring (${rec_data['total_recurring_monthly']:,.2f}/mo)")


if __name__ == "__main__":
    test_pure_math_formulas()
    test_service_calculations()
    test_analytics_api_endpoints()
    print("\nALL FINANCIAL ANALYTICS TESTS PASSED SUCCESSFULLY!")

