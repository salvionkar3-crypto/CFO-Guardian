"""AI CFO Schemas
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CompanyMetrics(BaseModel):
    name: str
    operating_currency: str
    total_balance: float
    monthly_budget: float
    monthly_spent: float
    budget_remaining: float
    runway_months: float
    burn_rate_daily: float


class InvoiceAnalysisRequest(BaseModel):
    title: str = Field(..., example="AWS Production Cloud Infrastructure")
    vendor: str = Field(..., example="Amazon Web Services")
    vendor_email: str = Field(..., example="billing@aws.amazon.com")
    category: str = Field(default="Infrastructure", example="Infrastructure")
    amount: float = Field(..., gt=0, example=450.00)
    currency: str = Field(default="USD", example="USD")
    invoice_number: Optional[str] = Field(default=None, example="INV-2026-9041")
    notes: Optional[str] = Field(default=None, example="Monthly EC2 and RDS hosting")


class CFOAnalysisResult(BaseModel):
    decision_id: int
    recommendation: str  # "APPROVE", "FLAG_FOR_REVIEW", "REJECT"
    rationale: str
    budget_impact_pct: float
    runway_impact_days: int
    current_stage: str

