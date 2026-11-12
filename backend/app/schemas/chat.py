"""Pydantic Schemas for AI CFO Chat and Consultation

Covers:
- Prompt ingestion
- Structured tool execution responses
- Session management
- Chronological message history
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ChatQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Natural language question for the AI CFO")
    session_id: Optional[int] = Field(None, description="Existing session ID to continue conversation, or null to auto-create")


class ChatQueryResponse(BaseModel):
    session_id: int
    session_title: str
    message_id: int
    role: str = "assistant"
    reply: str
    tools_executed: List[str] = Field(default_factory=list)
    insight_card: Optional[Dict[str, Any]] = None
    timestamp: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    reasoning_meta: Optional[str] = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)

