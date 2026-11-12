"""Guardian AI Risk Assessment & Security Center Schemas

Defines contracts for:
- 10 Discrete Risk Signal detections
- Supporting evidence and missing information
- Deterministic scoring breakdown (0-100)
- Configurable risk policy thresholds
- Security alerts and resolution
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RiskSignalItem(BaseModel):
    id: str = Field(..., description="Unique signal code, e.g. SIGNAL_FIRST_TIME_VENDOR")
    name: str = Field(..., description="Human-readable title of the signal")
    severity: str = Field("MEDIUM", description="LOW, MEDIUM, HIGH, or CRITICAL")
    score_impact: float = Field(..., ge=0.0, le=100.0, description="Score contribution to overall risk")
    description: str = Field(..., description="What the signal checks for")
    evidence: str = Field(..., description="Specific evidence detected for this transaction")


class RiskPolicyThresholds(BaseModel):
    low_min: float = 0.0
    low_max: float = 24.0
    medium_min: float = 25.0
    medium_max: float = 49.0
    high_min: float = 50.0
    high_max: float = 74.0
    critical_min: float = 75.0
    critical_max: float = 100.0
    notice: str = "Demonstration policy thresholds, not validated fraud probabilities."


class RiskAssessmentRequest(BaseModel):
    decision_id: int
    force_deep_scan: bool = False


class RiskAssessmentResponse(BaseModel):
    id: int
    decision_id: int
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    verdict: str  # "SAFE_TO_PAY", "REQUIRES_MANUAL_REVIEW", "BLOCKED"
    recommended_action: str  # "ALLOW", "MANUAL_REVIEW_REQUIRED", "DUAL_EXECUTIVE_APPROVAL_REQUIRED", "REJECT_AND_BLOCK"
    plain_explanation: str
    detected_signals: List[RiskSignalItem] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    vendor_verified: bool = False
    is_duplicate_invoice: bool = False
    anomaly_detected: bool = False
    verification_hash: Optional[str] = None
    created_at: Optional[str] = None


class SecurityAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    severity: str
    title: str
    description: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
