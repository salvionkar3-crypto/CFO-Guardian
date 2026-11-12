"""Authentication and Tenant Management Endpoints

Implements:
- Registration with automatic business account provisioning
- Secure bcrypt password verification and JWT token issuance
- Safe demo login endpoint
- Current user & business profile retrieval
- Logout audit recording
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.db.session import get_db
from app.db.seed import seed_demo_data
from app.models.user import User
from app.models.business import Business, BusinessSettings
from app.models.audit import AuditLog
from app.services.audit_service import AuditService
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserSummary,
    BusinessSummary,
    BusinessSettingsSummary,
)
from app.api.deps import get_current_user, get_current_business
from app.core.logging_config import logger

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """Registers a new user and provisions their isolated business treasury account."""
    existing_user = db.query(User).filter(User.email == data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # 1. Create User with bcrypt hashed password (never plain text)
    new_user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="OWNER",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 2. Provision isolated Business
    new_business = Business(
        name=data.business_name,
        legal_name=f"{data.business_name} Inc.",
        currency=data.currency or "USD",
        total_balance=100000.0,
        monthly_budget=30000.0,
        monthly_spent=0.0,
        owner_id=new_user.id,
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)

    # 3. Provision Default Business Settings
    b_settings = BusinessSettings(
        business_id=new_business.id,
        auto_approve_threshold=settings.AUTO_APPROVE_THRESHOLD_USD,
        max_single_payment_limit=5000.0,
        require_dual_approval_above=1000.0,
        risk_tolerance_level="MEDIUM",
        notification_email=data.email.lower(),
        enable_paypal_sandbox=True,
    )
    db.add(b_settings)

    # 4. Audit Log
    audit = AuditLog(
        business_id=new_business.id,
        user_id=new_user.id,
        stage="UNDERSTAND",
        actor="SYSTEM",
        action="USER_REGISTRATION",
        summary=f"New organization registered: {new_business.name}",
        details=f"Owner: {new_user.email} (ID #{new_user.id})",
        rationale="Initialized tenant space and security guardrails.",
    )
    db.add(audit)
    db.commit()

    # 5. Issue JWT Token
    token_claims = {
        "sub": new_user.email,
        "user_id": new_user.id,
        "business_id": new_business.id,
        "role": new_user.role,
    }
    access_token = create_access_token(token_claims)

    AuditService.log_event(
        db=db,
        business_id=new_business.id,
        user_id=new_user.id,
        stage="UNDERSTAND",
        actor="USER",
        action="USER_REGISTER",
        summary=f"New business '{new_business.name}' registered by {new_user.email}",
        details=f"Tenant ID: {new_business.id}, Role: {new_user.role}",
        rationale="Self-service organization and user registration.",
    )

    logger.info(f"Registered new tenant: {new_business.name} (Owner: {new_user.email})")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
        ),
        business=BusinessSummary(
            id=new_business.id,
            name=new_business.name,
            legal_name=new_business.legal_name,
            currency=new_business.currency,
            total_balance=new_business.total_balance,
            monthly_budget=new_business.monthly_budget,
            monthly_spent=new_business.monthly_spent,
            owner_id=new_business.owner_id,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    data: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticates user via email and password, returning JWT token and business context."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact administrator.",
        )

    business = db.query(Business).filter(Business.owner_id == user.id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business account associated with this login.",
        )

    # Issue JWT token
    token_claims = {
        "sub": user.email,
        "user_id": user.id,
        "business_id": business.id,
        "role": user.role,
    }
    access_token = create_access_token(token_claims)

    # Audit login
    audit = AuditLog(
        business_id=business.id,
        user_id=user.id,
        stage="MONITOR",
        actor="SYSTEM",
        action="USER_LOGIN",
        summary=f"User logged in: {user.email}",
        details=f"Role: {user.role}",
        rationale="Session established via JWT authentication.",
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        business=BusinessSummary(
            id=business.id,
            name=business.name,
            legal_name=business.legal_name,
            currency=business.currency,
            total_balance=business.total_balance,
            monthly_budget=business.monthly_budget,
            monthly_spent=business.monthly_spent,
            owner_id=business.owner_id,
        ),
    )


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)):
    """Safe, one-click evaluation login with rich pre-seeded fintech data."""
    # Ensure demo ecosystem is seeded
    seed_demo_data(db)

    demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
    if not demo_user:
        raise HTTPException(status_code=500, detail="Demo account initialization error.")

    demo_business = db.query(Business).filter(Business.owner_id == demo_user.id).first()
    if not demo_business:
        raise HTTPException(status_code=500, detail="Demo business initialization error.")

    token_claims = {
        "sub": demo_user.email,
        "user_id": demo_user.id,
        "business_id": demo_business.id,
        "role": demo_user.role,
    }
    access_token = create_access_token(token_claims)

    AuditService.log_event(
        db=db,
        business_id=demo_business.id,
        user_id=demo_user.id,
        stage="MONITOR",
        actor="SYSTEM",
        action="USER_LOGIN",
        summary=f"Demo user logged in: {demo_user.email}",
        details="Demo evaluation session initialized.",
        rationale="Safe demo evaluation login.",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=demo_user.id,
            email=demo_user.email,
            full_name=demo_user.full_name,
            role=demo_user.role,
            is_active=demo_user.is_active,
            created_at=demo_user.created_at,
        ),
        business=BusinessSummary(
            id=demo_business.id,
            name=demo_business.name,
            legal_name=demo_business.legal_name,
            currency=demo_business.currency,
            total_balance=demo_business.total_balance,
            monthly_budget=demo_business.monthly_budget,
            monthly_spent=demo_business.monthly_spent,
            owner_id=demo_business.owner_id,
        ),
    )


@router.get("/me")
def get_current_profile(
    current_user: User = Depends(get_current_user),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Retrieves authenticated user profile, business settings, and account scope."""
    settings_record = (
        db.query(BusinessSettings)
        .filter(BusinessSettings.business_id == business.id)
        .first()
    )

    return {
        "user": UserSummary(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
        ),
        "business": BusinessSummary(
            id=business.id,
            name=business.name,
            legal_name=business.legal_name,
            currency=business.currency,
            total_balance=business.total_balance,
            monthly_budget=business.monthly_budget,
            monthly_spent=business.monthly_spent,
            owner_id=business.owner_id,
        ),
        "settings": (
            BusinessSettingsSummary(
                id=settings_record.id,
                auto_approve_threshold=settings_record.auto_approve_threshold,
                max_single_payment_limit=settings_record.max_single_payment_limit,
                require_dual_approval_above=settings_record.require_dual_approval_above,
                risk_tolerance_level=settings_record.risk_tolerance_level,
                notification_email=settings_record.notification_email,
                enable_paypal_sandbox=settings_record.enable_paypal_sandbox,
            )
            if settings_record
            else None
        ),
    }


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Records logout event and informs client to clear auth token."""
    audit = AuditLog(
        business_id=business.id,
        user_id=current_user.id,
        stage="MONITOR",
        actor="SYSTEM",
        action="USER_LOGOUT",
        summary=f"User logged out: {current_user.email}",
        details=None,
        rationale="Session invalidated by user request.",
    )
    db.add(audit)
    db.commit()

    return {"message": "Logged out successfully. Invalidate your client bearer token."}
