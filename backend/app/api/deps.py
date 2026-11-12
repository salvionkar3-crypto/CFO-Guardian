"""FastAPI Authentication and Multi-Tenant Isolation Dependencies

Fintech Tenant Isolation Rule:
Never allow one business to read another business's data.
All protected endpoints resolve the caller's validated Business scope.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.business import Business
from app.core.logging_config import logger

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authenticates the request bearer token and retrieves active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or authentication session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: Optional[int] = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except Exception as exc:
        logger.warning(f"Failed JWT token verification: {exc}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists in system records.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact security compliance.",
        )

    return user


def get_current_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Business:
    """Strict Multi-Tenant Isolation:

    Resolves the specific business account owned by or assigned to the authenticated user.
    Guarantees cross-tenant boundary isolation.
    """
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business account registered for this user.",
        )
    return business


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Retrieves user if valid Bearer token provided; safely falls back to demo user for unauthenticated evaluation."""
    if token:
        try:
            payload = decode_access_token(token)
            user_id: Optional[int] = payload.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
                if user:
                    return user
        except Exception as exc:
            logger.debug(f"Optional token decode failed, falling back to demo user: {exc}")

    # Fallback to demo user
    demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
    if not demo_user:
        # Emergency auto-seed if demo user not yet in DB
        from app.db.seed import seed_demo_data
        seed_demo_data(db)
        demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()

    return demo_user


def get_optional_business(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Business:
    """Resolves authenticated business; safely falls back to demo business for unauthenticated evaluation."""
    business = db.query(Business).filter(Business.owner_id == current_user.id).first()
    if not business:
        # Fallback to demo business
        demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
        if demo_user:
            business = db.query(Business).filter(Business.owner_id == demo_user.id).first()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business account registered or demo account initialization error.",
        )
    return business

