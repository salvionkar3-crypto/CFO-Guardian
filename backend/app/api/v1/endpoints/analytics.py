"""Financial Analytics API Endpoints

Provides deterministic, calculated financial metrics:
- Revenue, Expenses, Net Cash Flow
- Period-over-period comparisons (Growth %, Expense Change %)
- Monthly historical trends
- Categorization breakdown
- Unusual expense increase detection
- Recurring subscription and vendor obligations
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_business
from app.models.business import Business
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    FinancialSummary,
    TrendItem,
    CategoryAnalysisResponse,
    ExpenseAnomaly,
    RecurringExpensesResponse,
)

router = APIRouter()


@router.get("/summary", response_model=FinancialSummary)
def get_financial_summary(
    period: Optional[str] = Query("current_month", description="Period: current_month, last_month, last_3_months, last_6_months"),
    start_date: Optional[date] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Custom end date (YYYY-MM-DD)"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Calculates total revenue, total expenses, net cash flow, and growth comparison metrics."""
    return AnalyticsService.get_financial_summary(
        db=db,
        business=business,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trends", response_model=list[TrendItem])
def get_financial_trends(
    months: int = Query(6, ge=2, le=24, description="Number of historical months to analyze"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves monthly timeline breakdown of revenue, expenses, and net cash flow."""
    return AnalyticsService.get_monthly_trends(
        db=db,
        business=business,
        months_count=months,
    )


@router.get("/categories", response_model=CategoryAnalysisResponse)
def get_category_breakdown(
    start_date: Optional[date] = Query(None, description="Optional start date"),
    end_date: Optional[date] = Query(None, description="Optional end date"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Analyzes expenses and revenues categorized with exact percentage allocations."""
    return AnalyticsService.get_category_breakdown(
        db=db,
        business=business,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/anomalies", response_model=list[ExpenseAnomaly])
def get_expense_anomalies(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Identifies unusual expense increases and sudden budget surge anomalies."""
    return AnalyticsService.identify_unusual_expense_increases(
        db=db,
        business=business,
    )


@router.get("/recurring", response_model=RecurringExpensesResponse)
def get_recurring_expenses(
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Identifies and aggregates recurring subscriptions, retainers, and regular obligations."""
    return AnalyticsService.identify_recurring_expenses(
        db=db,
        business=business,
    )

