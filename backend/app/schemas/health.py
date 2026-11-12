"""Health Check Schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    configured: bool
    status: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: Dict[str, Any]
    paypal: ServiceStatus
    openai: ServiceStatus
    timestamp: str

