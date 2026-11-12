"""Authentication and User Pydantic Schemas

Strict input validation for user registration, login, and tenant contexts.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100)
    business_name: str = Field(..., min_length=2, max_length=150)
    currency: Optional[str] = Field(default="USD", max_length=10)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class BusinessSummary(BaseModel):
    id: int
    name: str
    legal_name: Optional[str] = None
    currency: str
    total_balance: float
    monthly_budget: float
    monthly_spent: float
    owner_id: int


class BusinessSettingsSummary(BaseModel):
    id: int
    auto_approve_threshold: float
    max_single_payment_limit: float
    require_dual_approval_above: float
    risk_tolerance_level: str
    approval_validity_hours: Optional[float] = 24.0
    block_critical_risk: Optional[bool] = True
    notification_email: Optional[str] = None
    enable_paypal_sandbox: bool


class BusinessSettingsUpdateRequest(BaseModel):
    auto_approve_threshold: Optional[float] = None
    max_single_payment_limit: Optional[float] = None
    require_dual_approval_above: Optional[float] = None
    risk_tolerance_level: Optional[str] = None
    approval_validity_hours: Optional[float] = None
    block_critical_risk: Optional[bool] = None
    notification_email: Optional[str] = None
    enable_paypal_sandbox: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
    business: BusinessSummary
