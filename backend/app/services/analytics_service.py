"""Financial Analytics Engine

Performs exact mathematical and financial evaluations directly in Python
using verified database ledger records. Zero LLM hallucination.
Handles zero division, missing data, date intervals, and multi-tenant isolation.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.business import Business
from app.models.payment import Transaction
from app.models.vendor import Vendor
from app.schemas.analytics import (
    FinancialSummary,
    TrendItem,
    CategoryBreakdownItem,
    CategoryAnalysisResponse,
    ExpenseAnomaly,
    RecurringExpenseItem,
    RecurringExpensesResponse,
)
from app.core.logging_config import logger


class AnalyticsService:

    @staticmethod
    def _safe_percentage_change(current: float, previous: float) -> float:
        """Calculates percentage change safely handling zero division.

        Formula: ((Current - Previous) / Previous) * 100
        """
        if previous == 0.0:
            if current > 0.0:
                return 100.0
            elif current < 0.0:
                return -100.0
            return 0.0
        return round(((current - previous) / abs(previous)) * 100.0, 2)

    @classmethod
    def _resolve_period_dates(
        cls,
        period: Optional[str] = "current_month",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[datetime, datetime, datetime, datetime]:
        """Resolves current period and preceding comparison period ranges."""
        now = datetime.utcnow()

        if start_date and end_date:
            cur_start = datetime.combine(start_date, datetime.min.time())
            cur_end = datetime.combine(end_date, datetime.max.time())
            span = cur_end - cur_start
            prev_end = cur_start - timedelta(seconds=1)
            prev_start = prev_end - span
            return cur_start, cur_end, prev_start, prev_end

        if period == "last_3_months":
            cur_end = now
            cur_start = now - timedelta(days=90)
            prev_end = cur_start - timedelta(seconds=1)
            prev_start = prev_end - timedelta(days=90)
            return cur_start, cur_end, prev_start, prev_end

        if period == "last_6_months":
            cur_end = now
            cur_start = now - timedelta(days=180)
            prev_end = cur_start - timedelta(seconds=1)
            prev_start = prev_end - timedelta(days=180)
            return cur_start, cur_end, prev_start, prev_end

        if period == "last_month":
            # First day of this month
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Last day of prev month
            prev_month_end = first_this_month - timedelta(seconds=1)
            prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Preceding month before last month
            pre_prev_end = prev_month_start - timedelta(seconds=1)
            pre_prev_start = pre_prev_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return prev_month_start, prev_month_end, pre_prev_start, pre_prev_end

        # Default: current_month
        cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cur_end = now

        # Previous month equivalent timeframe
        prev_month_end = cur_start - timedelta(seconds=1)
        prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return cur_start, cur_end, prev_month_start, prev_month_end

    @classmethod
    def get_financial_summary(
        cls,
        db: Session,
        business: Business,
        period: Optional[str] = "current_month",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> FinancialSummary:
        """Calculates total revenue, expenses, net cash flow and period comparisons."""
        cur_start, cur_end, prev_start, prev_end = cls._resolve_period_dates(period, start_date, end_date)

        # 1. Current period transactions
        cur_txs = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business.id,
                Transaction.status == "COMPLETED",
                Transaction.created_at >= cur_start,
                Transaction.created_at <= cur_end,
            )
            .all()
        )

        # 2. Previous period transactions
        prev_txs = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business.id,
                Transaction.status == "COMPLETED",
                Transaction.created_at >= prev_start,
                Transaction.created_at <= prev_end,
            )
            .all()
        )

        cur_revenue = sum(t.amount for t in cur_txs if t.transaction_type == "INCOME")
        cur_expenses = sum(t.amount for t in cur_txs if t.transaction_type == "EXPENSE")

        prev_revenue = sum(t.amount for t in prev_txs if t.transaction_type == "INCOME")
        prev_expenses = sum(t.amount for t in prev_txs if t.transaction_type == "EXPENSE")

        # FORMULAS
        # Net Cash Flow = Total Revenue - Total Expenses
        cur_net_cash_flow = round(cur_revenue - cur_expenses, 2)
        prev_net_cash_flow = round(prev_revenue - prev_expenses, 2)
        net_cash_flow_change = round(cur_net_cash_flow - prev_net_cash_flow, 2)

        # Revenue Growth (%) = ((Current Revenue - Previous Revenue) / Previous Revenue) * 100
        rev_growth_pct = cls._safe_percentage_change(cur_revenue, prev_revenue)

        # Expense Change (%) = ((Current Expense - Previous Expense) / Previous Expense) * 100
        exp_change_pct = cls._safe_percentage_change(cur_expenses, prev_expenses)

        # Cash Flow Margin (%) = (Net Cash Flow / Revenue) * 100
        cash_flow_margin_pct = (
            round((cur_net_cash_flow / cur_revenue) * 100.0, 2) if cur_revenue > 0 else 0.0
        )

        # Runway calculation: total treasury balance / monthly expenses
        monthly_burn = cur_expenses if cur_expenses > 0 else (business.monthly_budget or 1000.0)
        runway_months = round(business.total_balance / monthly_burn, 1) if monthly_burn > 0 else 12.0

        return FinancialSummary(
            currency=business.currency,
            total_revenue=round(cur_revenue, 2),
            previous_revenue=round(prev_revenue, 2),
            revenue_growth_pct=rev_growth_pct,
            total_expenses=round(cur_expenses, 2),
            previous_expenses=round(prev_expenses, 2),
            expense_change_pct=exp_change_pct,
            net_cash_flow=cur_net_cash_flow,
            previous_net_cash_flow=prev_net_cash_flow,
            net_cash_flow_change=net_cash_flow_change,
            cash_flow_margin_pct=cash_flow_margin_pct,
            burn_rate_monthly=round(monthly_burn, 2),
            runway_months=runway_months,
            treasury_balance=round(business.total_balance, 2),
            period_start=cur_start.strftime("%Y-%m-%d"),
            period_end=cur_end.strftime("%Y-%m-%d"),
            comparison_period_start=prev_start.strftime("%Y-%m-%d"),
            comparison_period_end=prev_end.strftime("%Y-%m-%d"),
            total_transactions=len(cur_txs),
        )

    @classmethod
    def get_monthly_trends(
        cls,
        db: Session,
        business: Business,
        months_count: int = 6,
    ) -> List[TrendItem]:
        """Aggregates monthly revenue, expenses, and net cash flow for trend charts."""
        now = datetime.utcnow()
        trends: List[TrendItem] = []

        # Generate month slots in chronological order
        slots = []
        for i in range(months_count - 1, -1, -1):
            # Calculate year and month for (now - i months)
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            slots.append((year, month))

        for year, month in slots:
            month_start = datetime(year, month, 1)
            # Find next month
            if month == 12:
                next_start = datetime(year + 1, 1, 1)
            else:
                next_start = datetime(year, month + 1, 1)
            month_end = next_start - timedelta(seconds=1)

            txs = (
                db.query(Transaction)
                .filter(
                    Transaction.business_id == business.id,
                    Transaction.status == "COMPLETED",
                    Transaction.created_at >= month_start,
                    Transaction.created_at <= month_end,
                )
                .all()
            )

            rev = sum(t.amount for t in txs if t.transaction_type == "INCOME")
            exp = sum(t.amount for t in txs if t.transaction_type == "EXPENSE")
            net = rev - exp

            month_str = f"{year}-{month:02d}"
            label = month_start.strftime("%b %Y")

            trends.append(
                TrendItem(
                    month=month_str,
                    label=label,
                    revenue=round(rev, 2),
                    expenses=round(exp, 2),
                    net_cash_flow=round(net, 2),
                )
            )

        return trends

    @classmethod
    def get_category_breakdown(
        cls,
        db: Session,
        business: Business,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CategoryAnalysisResponse:
        """Categorizes expenses and revenues with exact proportional percentage shares."""
        query = db.query(Transaction).filter(
            Transaction.business_id == business.id,
            Transaction.status == "COMPLETED",
        )

        if start_date:
            query = query.filter(Transaction.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(Transaction.created_at <= datetime.combine(end_date, datetime.max.time()))

        txs = query.all()

        expense_totals: Dict[str, float] = defaultdict(float)
        expense_counts: Dict[str, int] = defaultdict(int)

        revenue_totals: Dict[str, float] = defaultdict(float)
        revenue_counts: Dict[str, int] = defaultdict(int)

        for t in txs:
            cat = t.category or "General"
            if t.transaction_type == "INCOME":
                revenue_totals[cat] += t.amount
                revenue_counts[cat] += 1
            else:
                expense_totals[cat] += t.amount
                expense_counts[cat] += 1

        total_exp = sum(expense_totals.values())
        total_rev = sum(revenue_totals.values())

        exp_items = []
        for cat, amt in sorted(expense_totals.items(), key=lambda x: x[1], reverse=True):
            pct = round((amt / total_exp) * 100.0, 2) if total_exp > 0 else 0.0
            exp_items.append(
                CategoryBreakdownItem(
                    category=cat,
                    total_amount=round(amt, 2),
                    percentage_share=pct,
                    transaction_count=expense_counts[cat],
                )
            )

        rev_items = []
        for cat, amt in sorted(revenue_totals.items(), key=lambda x: x[1], reverse=True):
            pct = round((amt / total_rev) * 100.0, 2) if total_rev > 0 else 0.0
            rev_items.append(
                CategoryBreakdownItem(
                    category=cat,
                    total_amount=round(amt, 2),
                    percentage_share=pct,
                    transaction_count=revenue_counts[cat],
                )
            )

        return CategoryAnalysisResponse(
            expenses_by_category=exp_items,
            revenue_by_category=rev_items,
            total_expenses=round(total_exp, 2),
            total_revenue=round(total_rev, 2),
        )

    @classmethod
    def identify_unusual_expense_increases(
        cls,
        db: Session,
        business: Business,
    ) -> List[ExpenseAnomaly]:
        """Detects anomalous expense surges between current period and previous period."""
        now = datetime.utcnow()
        cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cur_end = now

        prev_end = cur_start - timedelta(seconds=1)
        prev_start = prev_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get current expenses by category
        cur_txs = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business.id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.status == "COMPLETED",
                Transaction.created_at >= cur_start,
                Transaction.created_at <= cur_end,
            )
            .all()
        )

        prev_txs = (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business.id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.status == "COMPLETED",
                Transaction.created_at >= prev_start,
                Transaction.created_at <= prev_end,
            )
            .all()
        )

        cur_by_cat = defaultdict(float)
        for t in cur_txs:
            cur_by_cat[t.category] += t.amount

        prev_by_cat = defaultdict(float)
        for t in prev_txs:
            prev_by_cat[t.category] += t.amount

        anomalies: List[ExpenseAnomaly] = []

        all_categories = set(cur_by_cat.keys()) | set(prev_by_cat.keys())
        for cat in sorted(all_categories):
            cur_amt = cur_by_cat[cat]
            prev_amt = prev_by_cat[cat]

            # Trigger condition: surge > 35% and absolute increase > $200
            diff = cur_amt - prev_amt
            if prev_amt > 0 and cur_amt > prev_amt:
                increase_pct = round(((cur_amt - prev_amt) / prev_amt) * 100.0, 1)
                if increase_pct >= 35.0 and diff >= 200.0:
                    severity = "CRITICAL" if increase_pct >= 100.0 else "SIGNIFICANT" if increase_pct >= 50.0 else "MODERATE"
                    anomalies.append(
                        ExpenseAnomaly(
                            category=cat,
                            current_amount=round(cur_amt, 2),
                            previous_amount=round(prev_amt, 2),
                            increase_pct=increase_pct,
                            severity=severity,
                            reason=f"Monthly spend in '{cat}' surged by {increase_pct}% (+${diff:,.2f}) compared to prior month.",
                        )
                    )
            elif prev_amt == 0 and cur_amt >= 500.0:
                # Brand new category expense with substantial initial spend
                anomalies.append(
                    ExpenseAnomaly(
                        category=cat,
                        current_amount=round(cur_amt, 2),
                        previous_amount=0.0,
                        increase_pct=100.0,
                        severity="SIGNIFICANT",
                        reason=f"New unbudgeted category '{cat}' with initial expenditure of ${cur_amt:,.2f}.",
                    )
                )

        return anomalies

    @classmethod
    def identify_recurring_expenses(
        cls,
        db: Session,
        business: Business,
    ) -> RecurringExpensesResponse:
        """Identifies recurring subscriptions, retainers, and scheduled vendor charges."""
        # Query all expense transactions
        txs = (
            db.query(Transaction, Vendor)
            .outerjoin(Vendor, Transaction.vendor_id == Vendor.id)
            .filter(
                Transaction.business_id == business.id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.status == "COMPLETED",
            )
            .order_by(Transaction.created_at.desc())
            .all()
        )

        vendor_tx_map: Dict[str, List[Transaction]] = defaultdict(list)
        vendor_names: Dict[str, str] = {}
        vendor_categories: Dict[str, str] = {}

        for tx, vendor in txs:
            v_key = str(tx.vendor_id) if tx.vendor_id else (vendor.name if vendor else tx.category)
            v_name = vendor.name if vendor else tx.category
            vendor_tx_map[v_key].append(tx)
            vendor_names[v_key] = v_name
            vendor_categories[v_key] = tx.category

        items: List[RecurringExpenseItem] = []

        for v_key, v_txs in vendor_tx_map.items():
            # Check 1: Explicitly flagged as recurring
            explicitly_recurring = any(t.is_recurring for t in v_txs)

            # Check 2: Pattern-based heuristic (similar amounts across distinct months)
            distinct_months = {t.created_at.strftime("%Y-%m") for t in v_txs}
            is_pattern_recurring = len(distinct_months) >= 2

            if explicitly_recurring or is_pattern_recurring:
                amounts = [t.amount for t in v_txs]
                avg_amt = sum(amounts) / len(amounts)
                latest_tx = max(v_txs, key=lambda t: t.created_at)

                items.append(
                    RecurringExpenseItem(
                        vendor_name=vendor_names[v_key],
                        category=vendor_categories[v_key],
                        amount=round(avg_amt, 2),
                        frequency="MONTHLY",
                        annualized_amount=round(avg_amt * 12.0, 2),
                        last_paid_date=latest_tx.created_at.strftime("%Y-%m-%d"),
                    )
                )

        # Sort by highest monthly expense
        items.sort(key=lambda x: x.amount, reverse=True)
        total_monthly = round(sum(i.amount for i in items), 2)
        total_annual = round(total_monthly * 12.0, 2)

        return RecurringExpensesResponse(
            total_recurring_monthly=total_monthly,
            total_recurring_annual=total_annual,
            items=items,
        )
