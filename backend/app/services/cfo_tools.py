"""Approved AI CFO Read-Only Financial Analytics Tools

Security Guardrail:
- strictly READ-ONLY. The AI CANNOT alter balances, execute transactions, or authorize payments.
- All figures are computed deterministically from the database ledger for the caller's business.
- Never reveals raw credentials, sensitive PII, or internal cryptographic secrets.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.business import Business
from app.models.payment import Transaction
from app.models.vendor import Vendor
from app.services.analytics_service import AnalyticsService
from app.core.logging_config import logger


# ==============================================================================
# 1. APPROVED TOOL IMPLEMENTATIONS
# ==============================================================================

def tool_get_financial_summary(db: Session, business: Business, period: str = "current_month") -> Dict[str, Any]:
    """Retrieves verified total revenue, total expenses, net cash flow, and growth metrics."""
    summary = AnalyticsService.get_financial_summary(db=db, business=business, period=period)
    return {
        "period": period,
        "currency": summary.currency,
        "total_revenue": summary.total_revenue,
        "previous_revenue": summary.previous_revenue,
        "revenue_growth_pct": summary.revenue_growth_pct,
        "total_expenses": summary.total_expenses,
        "previous_expenses": summary.previous_expenses,
        "expense_change_pct": summary.expense_change_pct,
        "net_cash_flow": summary.net_cash_flow,
        "previous_net_cash_flow": summary.previous_net_cash_flow,
        "net_cash_flow_change": summary.net_cash_flow_change,
        "cash_flow_margin_pct": summary.cash_flow_margin_pct,
        "runway_months": summary.runway_months,
        "treasury_balance": summary.treasury_balance,
        "period_start": summary.period_start,
        "period_end": summary.period_end,
    }


def tool_get_category_breakdown(db: Session, business: Business) -> Dict[str, Any]:
    """Returns exact breakdown of expenses and revenue by category with percentage shares."""
    breakdown = AnalyticsService.get_category_breakdown(db=db, business=business)
    return {
        "total_expenses": breakdown.total_expenses,
        "total_revenue": breakdown.total_revenue,
        "top_expense_categories": [
            {
                "category": c.category,
                "amount": c.total_amount,
                "percentage_share": c.percentage_share,
                "transactions": c.transaction_count,
            }
            for c in breakdown.expenses_by_category[:6]
        ],
        "top_revenue_categories": [
            {
                "category": c.category,
                "amount": c.total_amount,
                "percentage_share": c.percentage_share,
            }
            for c in breakdown.revenue_by_category[:4]
        ],
    }


def tool_get_top_vendors(db: Session, business: Business, limit: int = 5) -> Dict[str, Any]:
    """Identifies vendors with the highest cumulative paid amounts."""
    vendors = (
        db.query(Vendor)
        .filter(Vendor.business_id == business.id)
        .order_by(Vendor.total_paid.desc())
        .limit(limit)
        .all()
    )

    vendor_list = []
    for v in vendors:
        vendor_list.append({
            "vendor_name": v.name,
            "status": v.status,
            "trust_score": v.trust_score,
            "total_paid": round(v.total_paid, 2),
        })

    return {
        "top_vendors": vendor_list,
        "count": len(vendor_list),
        "primary_cost_driver": vendor_list[0]["vendor_name"] if vendor_list else "None",
    }


def tool_check_affordability(
    db: Session,
    business: Business,
    amount: float,
    currency: str = "USD",
    category: str = "General",
) -> Dict[str, Any]:
    """Determines whether the business can afford a proposed purchase without jeopardizing runway."""
    # Convert approximate if needed, or default to USD
    amount_usd = amount

    current_balance = business.total_balance
    monthly_budget = business.monthly_budget
    monthly_spent = business.monthly_spent
    remaining_budget = max(0.0, monthly_budget - monthly_spent)

    daily_burn = (monthly_budget / 30.0) if monthly_budget > 0 else 1000.0
    runway_impact_days = max(1, int(amount_usd / daily_burn))
    post_purchase_balance = current_balance - amount_usd
    new_runway_months = round(post_purchase_balance / monthly_budget, 1) if monthly_budget > 0 else 0.0

    # Verdict Evaluation
    if amount_usd > current_balance:
        verdict = "UNAFFORDABLE"
        recommendation = "REJECT"
        rationale = f"Expense of ${amount_usd:,.2f} exceeds total treasury liquidity (${current_balance:,.2f}). Immediate insolvency risk."
    elif amount_usd > remaining_budget:
        verdict = "EXCEEDS_MONTHLY_BUDGET"
        recommendation = "FLAG_FOR_REVIEW"
        rationale = f"Expense of ${amount_usd:,.2f} exceeds remaining monthly budget (${remaining_budget:,.2f}). Reduces treasury runway by {runway_impact_days} days."
    elif amount_usd > 5000.0:
        verdict = "REQUIRES_DUAL_EXECUTIVE_APPROVAL"
        recommendation = "FLAG_FOR_REVIEW"
        rationale = f"Expense of ${amount_usd:,.2f} is affordable from cash reserves, but triggers executive dual-approval threshold ($5,000)."
    else:
        verdict = "AFFORDABLE"
        recommendation = "APPROVE"
        rationale = f"Expense of ${amount_usd:,.2f} is well within safe operating limits. Remaining treasury runway after purchase: {new_runway_months} months."

    return {
        "requested_amount": amount,
        "currency": currency,
        "category": category,
        "current_treasury_balance": current_balance,
        "remaining_monthly_budget": remaining_budget,
        "post_purchase_balance": post_purchase_balance,
        "runway_impact_days": runway_impact_days,
        "projected_runway_months": new_runway_months,
        "verdict": verdict,
        "recommendation": recommendation,
        "rationale": rationale,
        "disclaimer": "AI CFO recommendations are advisory. Official payments require dual authorization through the payment gateway.",
    }


def tool_get_unusual_spending_patterns(db: Session, business: Business) -> Dict[str, Any]:
    """Identifies sudden cost spikes, budget surges, and unusual category outflows."""
    anomalies = AnalyticsService.identify_unusual_expense_increases(db=db, business=business)
    return {
        "anomalies_detected": len(anomalies),
        "items": [
            {
                "category": a.category,
                "current_amount": a.current_amount,
                "previous_amount": a.previous_amount,
                "surge_percentage": a.increase_pct,
                "severity": a.severity,
                "description": a.reason,
            }
            for a in anomalies
        ],
    }


def tool_get_recurring_commitments(db: Session, business: Business) -> Dict[str, Any]:
    """Retrieves verified recurring vendor subscriptions and monthly/annual cost totals."""
    rec = AnalyticsService.identify_recurring_expenses(db=db, business=business)
    return {
        "total_recurring_monthly": rec.total_recurring_monthly,
        "total_recurring_annual": rec.total_recurring_annual,
        "recurring_subscriptions": [
            {
                "vendor": i.vendor_name,
                "category": i.category,
                "amount": i.amount,
                "frequency": i.frequency,
                "annual_cost": i.annualized_amount,
                "last_paid": i.last_paid_date,
            }
            for i in rec.items
        ],
    }


def tool_compare_periods(db: Session, business: Business, period1: str = "current_month", period2: str = "last_month") -> Dict[str, Any]:
    """Compares financial metrics between two operational periods."""
    summary = AnalyticsService.get_financial_summary(db=db, business=business, period=period1)
    return {
        "current_period": period1,
        "previous_period": period2,
        "revenue_current": summary.total_revenue,
        "revenue_previous": summary.previous_revenue,
        "revenue_growth_pct": summary.revenue_growth_pct,
        "expenses_current": summary.total_expenses,
        "expenses_previous": summary.previous_expenses,
        "expense_change_pct": summary.expense_change_pct,
        "net_cash_flow_current": summary.net_cash_flow,
        "net_cash_flow_previous": summary.previous_net_cash_flow,
        "cash_flow_delta": summary.net_cash_flow_change,
    }


# ==============================================================================
# 2. OPENAI TOOL SCHEMAS FOR STRUCTURED FUNCTION CALLING
# ==============================================================================

CFO_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_summary",
            "description": "Get verified total revenue, total expenses, net cash flow, growth %, burn rate, and runway for a period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["current_month", "last_month", "last_3_months", "last_6_months"],
                        "description": "The time period to summarize.",
                    }
                },
                "required": ["period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_breakdown",
            "description": "Get exact breakdown of expenses and revenue categorized with dollar amounts and proportional percentage shares.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_vendors",
            "description": "Identifies which vendors or service providers cost the business the most money.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of top vendors to return (default 5).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_affordability",
            "description": "Evaluates whether the business can afford a specific payment or purchase amount without jeopardizing cash runway.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The proposed monetary expenditure amount.",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (e.g. USD, INR, EUR).",
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category (e.g. Software, Infrastructure, Marketing).",
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_unusual_spending_patterns",
            "description": "Detects unusual expense spikes, unexpected category surges, and cost anomalies.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recurring_commitments",
            "description": "Lists all active recurring subscriptions, retainers, and regular scheduled vendor obligations with monthly and annual totals.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_periods",
            "description": "Compares financial performance between two periods (e.g. this month vs last month).",
            "parameters": {
                "type": "object",
                "properties": {
                    "period1": {
                        "type": "string",
                        "enum": ["current_month", "last_month", "last_3_months"],
                    },
                    "period2": {
                        "type": "string",
                        "enum": ["last_month", "last_3_months"],
                    },
                },
                "required": ["period1", "period2"],
            },
        },
    },
]


def execute_cfo_tool(tool_name: str, arguments: Dict[str, Any], db: Session, business: Business) -> Dict[str, Any]:
    """Executes an approved read-only financial tool and returns actual database figures."""
    logger.info(f"[CFO TOOL] Executing '{tool_name}' with args {arguments} for business #{business.id}")

    if tool_name == "get_financial_summary":
        return tool_get_financial_summary(db, business, arguments.get("period", "current_month"))
    elif tool_name == "get_category_breakdown":
        return tool_get_category_breakdown(db, business)
    elif tool_name == "get_top_vendors":
        return tool_get_top_vendors(db, business, arguments.get("limit", 5))
    elif tool_name == "check_affordability":
        return tool_check_affordability(
            db,
            business,
            arguments.get("amount", 0.0),
            arguments.get("currency", "USD"),
            arguments.get("category", "General"),
        )
    elif tool_name == "get_unusual_spending_patterns":
        return tool_get_unusual_spending_patterns(db, business)
    elif tool_name == "get_recurring_commitments":
        return tool_get_recurring_commitments(db, business)
    elif tool_name == "compare_periods":
        return tool_compare_periods(
            db,
            business,
            arguments.get("period1", "current_month"),
            arguments.get("period2", "last_month"),
        )
    else:
        raise ValueError(f"Unauthorized or unknown CFO tool: '{tool_name}'")

