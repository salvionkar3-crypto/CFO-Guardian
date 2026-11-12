"""AI CFO Conversational Chat Endpoints

Enables small businesses to consult Guardian CFO in natural language.
Strictly scoped to the authenticated tenant business.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.api.deps import get_optional_business, get_optional_user
from app.models.user import User
from app.models.business import Business
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageResponse,
)
from app.services.ai_cfo_service import AICFOService
from app.core.logging_config import logger

router = APIRouter()


@router.post("", response_model=ChatQueryResponse)
@router.post("/", response_model=ChatQueryResponse)
def ask_ai_cfo(
    request: ChatQueryRequest,
    business: Business = Depends(get_optional_business),
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Submits a natural language financial question to the AI CFO.

    Executes approved database analytics tools to retrieve actual financial numbers
    and returns a structured explanation with optional insight cards.
    Gracefully falls back to demo business context if unauthenticated.
    """
    logger.info(f"AI CFO consultation query received for Business #{business.id} ('{business.name}') by User #{current_user.id}: {request.prompt[:60]}...")
    try:
        response_dict = AICFOService.ask_cfo(
            db=db,
            business=business,
            user=current_user,
            prompt=request.prompt.strip(),
            session_id=request.session_id,
        )
        logger.info(f"AI CFO query successful: Session #{response_dict.get('session_id')}, Tools: {response_dict.get('tools_executed')}")
        return ChatQueryResponse(**response_dict)
    except Exception as exc:
        logger.error(f"Error processing AI CFO consultation: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI CFO processing failed: {str(exc)}",
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
@router.get("/sessions/", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    business: Business = Depends(get_optional_business),
    db: Session = Depends(get_db),
):
    """Retrieves all chat consultation sessions for the tenant business."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.business_id == business.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

    results = []
    for s in sessions:
        msg_count = db.query(func.count(ChatMessage.id)).filter(ChatMessage.session_id == s.id).scalar() or 0
        results.append(
            ChatSessionResponse(
                id=s.id,
                business_id=s.business_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count,
            )
        )
    return results


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
@router.get("/sessions/{session_id}/", response_model=ChatSessionDetailResponse)
def get_chat_session_detail(
    session_id: int,
    business: Business = Depends(get_optional_business),
    db: Session = Depends(get_db),
):
    """Retrieves chronological message history for a specific consultation session."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.business_id == business.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found for your business.",
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return ChatSessionDetailResponse(
        id=session.id,
        business_id=session.business_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/sessions/{session_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: int,
    business: Business = Depends(get_optional_business),
    db: Session = Depends(get_db),
):
    """Deletes a chat consultation session and all associated messages."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.business_id == business.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    db.delete(session)
    db.commit()
    return None

