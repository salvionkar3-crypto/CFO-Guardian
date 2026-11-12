"""PayPal REST API Integration Service (Orders v2 & Sandbox Lifecycle)

Official PayPal REST API Reference: https://developer.paypal.com/api/rest/
Features:
- OAuth 2.0 Client Credentials Grant with in-memory token caching and auto-refresh.
- Secure server-side credential storage (never logged, never exposed to client).
- Orders v2 checkout creation with idempotency keys (PayPal-Request-Id).
- Approval URL generation for buyer checkout in PayPal Sandbox.
- Cryptographic pre-flight verification before order creation.
- Strict capture confirmation: never claims success until PayPal REST API confirms COMPLETED.
- Dual execution separation: Sandbox (api-m.sandbox.paypal.com) vs Production (api-m.paypal.com).
"""

import hashlib
import json
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import logger
from app.models.payment import PaymentDraft, Transaction
from app.models.business import Business
from app.models.user import User
from app.models.vendor import Vendor
from app.models.guardian import RiskAssessment
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class PayPalConfigurationError(Exception):
    """Raised when PayPal client credentials are missing or unconfigured."""
    pass


class PayPalAPIError(Exception):
    """Raised when PayPal REST API returns a client or server error."""
    pass


class PayPalTokenCache:
    """Thread-safe in-memory cache for PayPal OAuth 2.0 Bearer tokens."""
    _access_token: Optional[str] = None
    _expires_at: Optional[datetime] = None

    @classmethod
    def get_token(cls) -> Optional[str]:
        if cls._access_token and cls._expires_at:
            # Leave 60-second buffer before true token expiry
            if datetime.utcnow() < (cls._expires_at - timedelta(seconds=60)):
                return cls._access_token
        return None

    @classmethod
    def set_token(cls, token: str, expires_in_seconds: int = 32400):
        cls._access_token = token
        cls._expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

    @classmethod
    def clear(cls):
        cls._access_token = None
        cls._expires_at = None


class PayPalService:
    @classmethod
    def is_configured(cls) -> bool:
        """Verifies if PayPal credentials exist in environment configuration."""
        client_id = (settings.PAYPAL_CLIENT_ID or "").strip()
        client_secret = (settings.PAYPAL_CLIENT_SECRET or "").strip()
        return bool(client_id and client_secret)

    @classmethod
    def get_masked_client_id(cls) -> Optional[str]:
        """Returns a non-sensitive preview of the client ID for dashboard telemetry."""
        cid = (settings.PAYPAL_CLIENT_ID or "").strip()
        if not cid:
            return None
        if len(cid) <= 8:
            return "****"
        return f"{cid[:4]}...{cid[-4:]}"

    @classmethod
    async def get_access_token(cls, force_refresh: bool = False) -> str:
        """Obtains an OAuth 2.0 Bearer Token from PayPal REST API using Client Credentials grant."""
        if not cls.is_configured():
            raise PayPalConfigurationError(
                "PayPal Sandbox credentials are not configured. Please supply PAYPAL_CLIENT_ID "
                "and PAYPAL_CLIENT_SECRET in backend/.env to interact with PayPal Sandbox."
            )

        if not force_refresh:
            cached = PayPalTokenCache.get_token()
            if cached:
                return cached

        url = f"{settings.paypal_base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    url,
                    auth=(settings.PAYPAL_CLIENT_ID.strip(), settings.PAYPAL_CLIENT_SECRET.strip()),
                    headers=headers,
                    data=data,
                )
                if response.status_code != 200:
                    PayPalTokenCache.clear()
                    err_msg = response.text
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error_description", response.text)
                    except Exception:
                        pass
                    logger.error(f"PayPal OAuth failed ({response.status_code}): {err_msg}")
                    raise PayPalAPIError(f"PayPal OAuth authentication failed ({response.status_code}): {err_msg}")

                payload = response.json()
                token = payload.get("access_token")
                expires_in = payload.get("expires_in", 32400)
                if not token:
                    raise PayPalAPIError("PayPal OAuth response did not contain an access_token.")

                PayPalTokenCache.set_token(token, expires_in)
                logger.info(f"[PAYPAL] Retrieved fresh OAuth2 access token (expires in {expires_in}s)")
                return token
            except httpx.RequestError as exc:
                logger.error(f"Network error communicating with PayPal OAuth: {exc}")
                raise PayPalAPIError(f"Network error reaching PayPal OAuth endpoint: {str(exc)}")

    @classmethod
    async def verify_credentials(cls) -> Dict[str, Any]:
        """Health check verifying credentials against PayPal Sandbox without making any charges."""
        if not cls.is_configured():
            return {
                "configured": False,
                "mode": settings.PAYPAL_MODE,
                "base_url": settings.paypal_base_url,
                "client_id_preview": None,
                "status": "missing_credentials",
                "details": "PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET is missing in backend/.env",
            }

        try:
            await cls.get_access_token(force_refresh=True)
            return {
                "configured": True,
                "mode": settings.PAYPAL_MODE,
                "base_url": settings.paypal_base_url,
                "client_id_preview": cls.get_masked_client_id(),
                "status": "ready",
                "details": f"Authenticated successfully with PayPal {settings.PAYPAL_MODE.upper()} REST API.",
            }
        except Exception as exc:
            return {
                "configured": True,
                "mode": settings.PAYPAL_MODE,
                "base_url": settings.paypal_base_url,
                "client_id_preview": cls.get_masked_client_id(),
                "status": "error",
                "details": str(exc),
            }

    @classmethod
    async def create_order_for_draft(
        cls,
        db: Session,
        draft: PaymentDraft,
        business: Business,
        user: User,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Transaction, Dict[str, Any]]:
        """Creates an authentic PayPal v2 Checkout Order for an APPROVED payment draft."""
        # 1. Strict Pre-flight Security Validations
        if draft.business_id != business.id:
            raise ValueError(f"Draft #{draft.id} does not belong to this business.")

        # Mandatory policy engine invariants (Approved, Not Expired, Tamper Intact, Guardian Risk, Dual Control)
        from app.services.policy_engine import PaymentPolicyEngine
        try:
            PaymentPolicyEngine.verify_execution_clearance(db=db, draft=draft, business=business)
        except Exception as exc:
            raise ValueError(getattr(exc, "detail", str(exc)))

        # 2. Payee resolution
        vendor = db.query(Vendor).filter(Vendor.id == draft.vendor_id).first()
        recipient_email = (
            vendor.bank_or_paypal_email or (vendor.email if vendor else "payee@example.com")
        )

        # 4. OAuth2 Token
        access_token = await cls.get_access_token()

        url = f"{settings.paypal_base_url}/v2/checkout/orders"
        request_id = idempotency_key or f"REQ-DRAFT-{draft.id}-{uuid.uuid4().hex[:8]}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": request_id,
        }

        ret_url = return_url or "http://localhost:3000/dashboard/payments/success"
        canc_url = cancel_url or "http://localhost:3000/dashboard/payments/cancel"

        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"DRAFT_{draft.id}_BIZ_{business.id}",
                    "description": f"Guardian CFO: {draft.title}"[:127],
                    "custom_id": str(draft.id),
                    "invoice_id": (draft.invoice_number or f"INV-DRAFT-{draft.id}")[:127],
                    "amount": {
                        "currency_code": draft.currency.upper(),
                        "value": f"{draft.amount:.2f}",
                    },
                    "payee": {
                        "email_address": recipient_email,
                    },
                }
            ],
            "application_context": {
                "brand_name": f"Guardian CFO ({business.name})"[:127],
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": ret_url,
                "cancel_url": canc_url,
            },
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=order_payload)
            if resp.status_code not in (200, 201):
                logger.error(f"PayPal Order creation rejected ({resp.status_code}): {resp.text}")
                draft.status = "FAILED"
                db.commit()
                raise PayPalAPIError(f"PayPal create order rejected ({resp.status_code}): {resp.text}")
            result = resp.json()

        paypal_order_id = result.get("id")
        links = result.get("links", [])
        approve_url = next(
            (l["href"] for l in links if l.get("rel") in ("approve", "payer-action")),
            None,
        )

        # 5. Record Transaction in Database
        transaction = (
            db.query(Transaction)
            .filter(Transaction.payment_draft_id == draft.id, Transaction.business_id == business.id)
            .first()
        )
        if not transaction:
            transaction = Transaction(
                business_id=business.id,
                vendor_id=draft.vendor_id,
                payment_draft_id=draft.id,
                transaction_type="EXPENSE",
                amount=draft.amount,
                currency=draft.currency,
                status="PROVIDER_PENDING",
                category=draft.category,
                description=f"PayPal Order for {draft.title}",
                paypal_order_id=paypal_order_id,
                payment_method="PAYPAL_SANDBOX",
                idempotency_key=request_id,
                is_sandbox=(settings.PAYPAL_MODE.lower() == "sandbox"),
                raw_paypal_response=resp.text,
            )
            db.add(transaction)
        else:
            transaction.paypal_order_id = paypal_order_id
            transaction.status = "PROVIDER_PENDING"
            transaction.payment_method = "PAYPAL_SANDBOX"
            transaction.idempotency_key = request_id
            transaction.raw_paypal_response = resp.text

        draft.status = "PROVIDER_PENDING"
        db.commit()
        db.refresh(transaction)

        # 6. Immutable Audit Trail Logging
        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=user.id,
            stage="PAY",
            actor="PAYMENT_AGENT",
            action="CREATE_PAYPAL_ORDER",
            summary=f"Created PayPal Order {paypal_order_id} in {settings.PAYPAL_MODE.upper()} mode",
            details=f"Draft #{draft.id} -> Transaction #{transaction.id}. Payee: {recipient_email}. Approve URL: {approve_url or 'None'}",
            rationale="Dispatched official PayPal v2 checkout order. Awaiting buyer sandbox authorization.",
        )

        return transaction, {
            "paypal_order_id": paypal_order_id,
            "status": result.get("status", "CREATED"),
            "approval_url": approve_url,
            "amount": draft.amount,
            "currency": draft.currency,
            "recipient_email": recipient_email,
            "links": links,
        }

    @classmethod
    async def get_order_details(cls, paypal_order_id: str) -> Dict[str, Any]:
        """Queries live order state from PayPal REST API."""
        access_token = await cls.get_access_token()
        url = f"{settings.paypal_base_url}/v2/checkout/orders/{paypal_order_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise PayPalAPIError(f"Failed to fetch PayPal order details ({resp.status_code}): {resp.text}")
            return resp.json()

    @classmethod
    async def capture_order(
        cls,
        db: Session,
        transaction_id: int,
        paypal_order_id: str,
        business: Business,
        user: User,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Transaction, Dict[str, Any]]:
        """Captures an approved PayPal Order on the backend.
        
        Fintech Guardrail: Never trusts frontend payment status.
        Does not mark transaction as COMPLETED until PayPal REST API confirms settlement.
        """
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.business_id == business.id)
            .first()
        )
        if not transaction:
            raise ValueError(f"Transaction #{transaction_id} not found in this business.")

        # Idempotent return if already completed
        if transaction.status == "COMPLETED":
            return transaction, {"status": "COMPLETED", "capture_id": transaction.paypal_capture_id}

        access_token = await cls.get_access_token()
        url = f"{settings.paypal_base_url}/v2/checkout/orders/{paypal_order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": idempotency_key or f"CAP-{transaction.id}-{uuid.uuid4().hex[:8]}",
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers)
            if resp.status_code not in (200, 201):
                logger.error(f"PayPal capture rejected ({resp.status_code}): {resp.text}")
                transaction.status = "FAILED"
                if transaction.payment_draft_id:
                    draft = db.query(PaymentDraft).filter(PaymentDraft.id == transaction.payment_draft_id).first()
                    if draft:
                        draft.status = "FAILED"
                db.commit()
                raise PayPalAPIError(f"PayPal capture rejected ({resp.status_code}): {resp.text}")

            result = resp.json()

        # Extract capture details and status
        capture_id = None
        capture_status = "UNKNOWN"
        purchase_units = result.get("purchase_units", [])
        if purchase_units:
            captures = purchase_units[0].get("payments", {}).get("captures", [])
            if captures:
                capture_id = captures[0].get("id")
                capture_status = captures[0].get("status", "UNKNOWN")

        transaction.paypal_capture_id = capture_id
        transaction.raw_paypal_response = resp.text

        # Strict Verification: Only mark COMPLETED if capture status is confirmed COMPLETED by PayPal
        if capture_status == "COMPLETED" or result.get("status") == "COMPLETED":
            transaction.status = "COMPLETED"
            transaction.settled_at = datetime.utcnow()

            # Decrement business balance and update monthly spent
            business.total_balance -= transaction.amount
            business.monthly_spent += transaction.amount

            # Update draft status
            if transaction.payment_draft_id:
                draft = db.query(PaymentDraft).filter(PaymentDraft.id == transaction.payment_draft_id).first()
                if draft:
                    draft.status = "COMPLETED"

            # Update vendor total paid
            vendor = db.query(Vendor).filter(Vendor.id == transaction.vendor_id).first()
            if vendor:
                vendor.total_paid += transaction.amount

            # Audit logs for PAY and MONITOR stages
            AuditService.log_event(
                db=db,
                business_id=business.id,
                user_id=user.id,
                stage="PAY",
                actor="PAYMENT_AGENT",
                action="CAPTURE_PAYPAL_ORDER",
                summary=f"Captured PayPal Order {paypal_order_id} (Capture ID: {capture_id})",
                details=f"Transaction #{transaction.id} settled for ${transaction.amount:,.2f}",
                rationale="Successfully captured funds from buyer via PayPal REST API v2.",
            )

            AuditService.log_event(
                db=db,
                business_id=business.id,
                user_id=user.id,
                stage="MONITOR",
                actor="SYSTEM",
                action="PAYMENT_CONFIRMATION",
                summary=f"Confirmed PayPal settlement for ${transaction.amount:,.2f}",
                details=f"Capture ID: {capture_id}. Decremented company balance.",
                rationale="Provider confirmed settlement. Treasury ledger balances updated.",
            )

            NotificationService.notify_payment_completed(
                db=db,
                business_id=business.id,
                draft_id=transaction.payment_draft_id,
                transaction_id=transaction.id,
                title=f"Disbursement to {vendor.name if vendor else 'Vendor'}",
                amount=transaction.amount,
                currency=transaction.currency,
                provider_tx_id=capture_id,
                user_id=user.id,
            )
        elif capture_status == "PENDING":
            transaction.status = "PROVIDER_PENDING"
            logger.warn(f"PayPal capture is PENDING for transaction #{transaction.id}")
        else:
            transaction.status = "FAILED"
            if transaction.payment_draft_id:
                draft = db.query(PaymentDraft).filter(PaymentDraft.id == transaction.payment_draft_id).first()
                if draft:
                    draft.status = "FAILED"
            NotificationService.notify_payment_failed(
                db=db,
                business_id=business.id,
                draft_id=transaction.payment_draft_id,
                title="PayPal Capture Declined",
                amount=transaction.amount,
                currency=transaction.currency,
                error_reason=f"Status: {capture_status}",
                user_id=user.id,
            )

        db.commit()
        db.refresh(transaction)

        return transaction, {
            "status": transaction.status,
            "paypal_order_id": paypal_order_id,
            "paypal_capture_id": capture_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "details": result,
        }

    @classmethod
    def cancel_order(
        cls,
        db: Session,
        transaction_id: int,
        business: Business,
        user: User,
    ) -> Transaction:
        """Handles order cancellation when buyer abandons checkout."""
        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.business_id == business.id)
            .first()
        )
        if not transaction:
            raise ValueError(f"Transaction #{transaction_id} not found.")

        transaction.status = "CANCELLED"
        if transaction.payment_draft_id:
            draft = db.query(PaymentDraft).filter(PaymentDraft.id == transaction.payment_draft_id).first()
            if draft:
                draft.status = "APPROVED"  # Re-enable draft for approval/retry

        AuditService.log_event(
            db=db,
            business_id=business.id,
            user_id=user.id,
            stage="PAY",
            actor="USER",
            action="CANCEL_PAYPAL_ORDER",
            summary=f"Cancelled PayPal order session for Transaction #{transaction.id}",
            details=f"PayPal Order ID: {transaction.paypal_order_id}. Reset draft to APPROVED.",
            rationale="User canceled PayPal checkout.",
        )
        db.commit()
        db.refresh(transaction)
        return transaction
