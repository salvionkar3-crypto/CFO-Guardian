"""Financial Analytics Pydantic Schemas

Strictly typed contracts for revenue, expense, cash flow, trends,
category allocations, recurring obligations, and anomaly detection.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FinancialSummary(BaseModel):
    currency: str = "USD"
    total_revenue: float
    previous_revenue: float
    revenue_growth_pct: float
    total_expenses: float
    previous_expenses: float
    expense_change_pct: float
    net_cash_flow: float
    previous_net_cash_flow: float
    net_cash_flow_change: float
    cash_flow_margin_pct: float
    burn_rate_monthly: float
    runway_months: float
    treasury_balance: float
    period_start: str
    period_end: str
    comparison_period_start: str
    comparison_period_end: str
    total_transactions: int


class TrendItem(BaseModel):
    month: str  # YYYY-MM
    label: str  # e.g., "Jun 2026"
    revenue: float
    expenses: float
    net_cash_flow: float


class CategoryBreakdownItem(BaseModel):
    category: str
    total_amount: float
    percentage_share: float
    transaction_count: int


class CategoryAnalysisResponse(BaseModel):
    expenses_by_category: List[CategoryBreakdownItem]
    revenue_by_category: List[CategoryBreakdownItem]
    total_expenses: float
    total_revenue: float


class ExpenseAnomaly(BaseModel):
    category: str
    vendor: Optional[str] = None
    current_amount: float
    previous_amount: float
    increase_pct: float
    severity: str  # "MODERATE", "SIGNIFICANT", "CRITICAL"
    reason: str


class RecurringExpenseItem(BaseModel):
    vendor_name: str
    category: str
    amount: float
    frequency: str = "MONTHLY"
    annualized_amount: float
    last_paid_date: Optional[str] = None


class RecurringExpensesResponse(BaseModel):
    total_recurring_monthly: float
    total_recurring_annual: float
    items: List[RecurringExpenseItem]

