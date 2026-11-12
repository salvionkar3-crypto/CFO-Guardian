"""Database Seeder Module

Populates demo business, vendors, multi-month transactions, risk assessments,
security alerts, and audit logs for instant, safe sandbox evaluation.
"""

from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.business import Business, BusinessSettings
from app.models.vendor import Vendor
from app.models.payment import PaymentDraft, PaymentApproval, Transaction
from app.models.guardian import RiskAssessment, SecurityAlert
from app.models.audit import AuditLog
from app.models.chat import ChatSession, ChatMessage
from app.core.logging_config import logger


def seed_demo_data(db: Session) -> dict:
    """Seeds a rich demo dataset for testing authentication, analytics, and tenant isolation."""
    # 1. Create or retrieve Demo User
    demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
    if not demo_user:
        demo_user = User(
            email=settings.DEMO_USER_EMAIL,
            hashed_password=hash_password(settings.DEMO_USER_PASSWORD),
            full_name="Alex Vance (CFO & Treasury Lead)",
            role="OWNER",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        logger.info(f"Seeded demo user: {demo_user.email}")

    # 2. Create or retrieve Demo Business
    demo_business = db.query(Business).filter(Business.owner_id == demo_user.id).first()
    if not demo_business:
        demo_business = Business(
            name="Acme Autonomous Corp",
            legal_name="Acme Autonomous Corporation LLC",
            currency="USD",
            tax_id="US-84920412",
            total_balance=148500.00,
            monthly_budget=35000.00,
            monthly_spent=12400.00,
            owner_id=demo_user.id,
            created_at=datetime.utcnow(),
        )
        db.add(demo_business)
        db.commit()
        db.refresh(demo_business)

        settings_record = BusinessSettings(
            business_id=demo_business.id,
            auto_approve_threshold=settings.AUTO_APPROVE_THRESHOLD_USD,
            max_single_payment_limit=5000.00,
            require_dual_approval_above=1000.00,
            risk_tolerance_level="MEDIUM",
            notification_email="cfo-alerts@acmeautonomous.com",
            enable_paypal_sandbox=True,
        )
        db.add(settings_record)
        db.commit()

    # 3. Ensure Vendors exist
    v_aws = db.query(Vendor).filter(Vendor.business_id == demo_business.id, Vendor.name == "Amazon Web Services").first()
    if not v_aws:
        v_aws = Vendor(
            business_id=demo_business.id,
            name="Amazon Web Services",
            email="billing@aws.amazon.com",
            website="https://aws.amazon.com",
            status="ACTIVE",
            trust_score=98.5,
            bank_or_paypal_email="billing@aws.amazon.com",
            total_paid=8400.00,
        )
        db.add(v_aws)

    v_stripe = db.query(Vendor).filter(Vendor.business_id == demo_business.id, Vendor.name == "Stripe Platform Services").first()
    if not v_stripe:
        v_stripe = Vendor(
            business_id=demo_business.id,
            name="Stripe Platform Services",
            email="invoicing@stripe.com",
            website="https://stripe.com",
            status="ACTIVE",
            trust_score=99.0,
            bank_or_paypal_email="invoicing@stripe.com",
            total_paid=3200.00,
        )
        db.add(v_stripe)

    v_github = db.query(Vendor).filter(Vendor.business_id == demo_business.id, Vendor.name == "GitHub Enterprise").first()
    if not v_github:
        v_github = Vendor(
            business_id=demo_business.id,
            name="GitHub Enterprise",
            email="billing@github.com",
            website="https://github.com",
            status="ACTIVE",
            trust_score=96.0,
            bank_or_paypal_email="billing@github.com",
            total_paid=1440.00,
        )
        db.add(v_github)

    v_suspicious = db.query(Vendor).filter(Vendor.business_id == demo_business.id, Vendor.name == "FastPay Offshore Ltd").first()
    if not v_suspicious:
        v_suspicious = Vendor(
            business_id=demo_business.id,
            name="FastPay Offshore Ltd",
            email="wire-transfer@fastpay-offshore99.xyz",
            website="http://fastpay-offshore99.xyz",
            status="UNDER_REVIEW",
            trust_score=34.0,
            bank_or_paypal_email="payouts@fastpay-offshore99.xyz",
            total_paid=0.0,
        )
        db.add(v_suspicious)

    db.commit()
    db.refresh(v_aws)
    db.refresh(v_stripe)
    db.refresh(v_github)
    db.refresh(v_suspicious)

    # 4. Multi-Month Transactions for Analytics Engine
    tx_count = db.query(Transaction).filter(Transaction.business_id == demo_business.id).count()
    if tx_count < 10:
        now = datetime.utcnow()
        # Month offsets: 0 (current), 1 (last month), 2, 3, 4, 5
        monthly_data = [
            # Current Month (Nov 2026)
            {
                "offset_days": 2,
                "items": [
                    ("Client Retainers", "INCOME", 14500.00, None, "Enterprise AI CFO Advisory - Retainer", False),
                    ("Software Subscriptions", "INCOME", 4250.00, None, "PayPal Checkout SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 890.00, v_aws.id, "AWS EC2 and RDS Scaling (Surge)", True),
                    ("Processing Fees", "EXPENSE", 195.00, v_stripe.id, "Stripe Monthly Merchant Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Cloud Seats", True),
                    ("Marketing", "EXPENSE", 2400.00, None, "Q4 Paid Acquisition Campaign (Surge)", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Team Space", True),
                    ("Legal & Professional", "EXPENSE", 1500.00, None, "Corporate Compliance & Tax Retainer", True),
                ]
            },
            # Previous Month (Oct 2026)
            {
                "offset_days": 32,
                "items": [
                    ("Client Retainers", "INCOME", 13200.00, None, "Enterprise AI CFO Advisory - Retainer", False),
                    ("Software Subscriptions", "INCOME", 3800.00, None, "PayPal Checkout SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 420.00, v_aws.id, "AWS Monthly Hosting", True),
                    ("Processing Fees", "EXPENSE", 180.00, v_stripe.id, "Stripe Monthly Merchant Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Cloud Seats", True),
                    ("Marketing", "EXPENSE", 1200.00, None, "Monthly Search Ads", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Team Space", True),
                    ("Legal & Professional", "EXPENSE", 1500.00, None, "Corporate Compliance & Tax Retainer", True),
                ]
            },
            # Sep 2026 (-60 days)
            {
                "offset_days": 62,
                "items": [
                    ("Client Retainers", "INCOME", 12500.00, None, "Enterprise AI CFO Advisory - Retainer", False),
                    ("Software Subscriptions", "INCOME", 3400.00, None, "PayPal Checkout SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 410.00, v_aws.id, "AWS Monthly Hosting", True),
                    ("Processing Fees", "EXPENSE", 160.00, v_stripe.id, "Stripe Monthly Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Seats", True),
                    ("Marketing", "EXPENSE", 1100.00, None, "Monthly Ads", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Space", True),
                ]
            },
            # Aug 2026 (-90 days)
            {
                "offset_days": 92,
                "items": [
                    ("Client Retainers", "INCOME", 11800.00, None, "Enterprise Retainer", False),
                    ("Software Subscriptions", "INCOME", 3100.00, None, "PayPal SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 415.00, v_aws.id, "AWS Monthly Hosting", True),
                    ("Processing Fees", "EXPENSE", 150.00, v_stripe.id, "Stripe Monthly Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Seats", True),
                    ("Marketing", "EXPENSE", 950.00, None, "Adwords", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Space", True),
                ]
            },
            # Jul 2026 (-120 days)
            {
                "offset_days": 122,
                "items": [
                    ("Client Retainers", "INCOME", 10500.00, None, "Enterprise Retainer", False),
                    ("Software Subscriptions", "INCOME", 2800.00, None, "PayPal SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 390.00, v_aws.id, "AWS Monthly Hosting", True),
                    ("Processing Fees", "EXPENSE", 140.00, v_stripe.id, "Stripe Monthly Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Seats", True),
                    ("Marketing", "EXPENSE", 900.00, None, "Adwords", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Space", True),
                ]
            },
            # Jun 2026 (-150 days)
            {
                "offset_days": 152,
                "items": [
                    ("Client Retainers", "INCOME", 9800.00, None, "Enterprise Retainer", False),
                    ("Software Subscriptions", "INCOME", 2400.00, None, "PayPal SaaS Subscriptions", False),
                    ("Infrastructure", "EXPENSE", 380.00, v_aws.id, "AWS Monthly Hosting", True),
                    ("Processing Fees", "EXPENSE", 120.00, v_stripe.id, "Stripe Monthly Settlement", True),
                    ("Developer Tools", "EXPENSE", 140.00, v_github.id, "GitHub Enterprise Seats", True),
                    ("Marketing", "EXPENSE", 800.00, None, "Adwords", False),
                    ("Office & Facilities", "EXPENSE", 850.00, None, "WeWork Dedicated Space", True),
                ]
            },
        ]

        seeded_txs = []
        for m in monthly_data:
            tx_date = now - timedelta(days=m["offset_days"])
            for cat, t_type, amt, v_id, desc, is_rec in m["items"]:
                seeded_txs.append(
                    Transaction(
                        business_id=demo_business.id,
                        vendor_id=v_id,
                        transaction_type=t_type,
                        amount=amt,
                        currency="USD",
                        status="COMPLETED",
                        category=cat,
                        description=desc,
                        is_recurring=is_rec,
                        recurring_frequency="MONTHLY" if is_rec else None,
                        paypal_order_id=f"PP-{t_type[:3]}-{int(tx_date.timestamp())}",
                        paypal_capture_id=f"CAP-{int(tx_date.timestamp())}",
                        is_sandbox=True,
                        settled_at=tx_date,
                        created_at=tx_date,
                    )
                )
        db.add_all(seeded_txs)
        db.commit()
        logger.info(f"Seeded {len(seeded_txs)} multi-month transactions for business #{demo_business.id}")

    # 5. Payment Drafts
    draft_count = db.query(PaymentDraft).filter(PaymentDraft.business_id == demo_business.id).count()
    if draft_count == 0:
        draft_safe = PaymentDraft(
            business_id=demo_business.id,
            vendor_id=v_aws.id,
            created_by_id=demo_user.id,
            title="AWS Production Cloud Infrastructure - Monthly",
            amount=420.00,
            currency="USD",
            category="Infrastructure",
            invoice_number="INV-AWS-2026-904",
            description="Monthly compute & database cluster hosting",
            status="APPROVED",
            cfo_recommendation="APPROVE",
            cfo_rationale="Expense of $420.00 represents 1.2% of monthly budget. Pre-approved under safe runway guardrails.",
            budget_impact_pct=1.2,
            runway_impact_days=1,
            created_at=datetime.utcnow() - timedelta(hours=4),
        )

        draft_threat = PaymentDraft(
            business_id=demo_business.id,
            vendor_id=v_suspicious.id,
            created_by_id=demo_user.id,
            title="Urgent Offshore Strategy Advisory",
            amount=6400.00,
            currency="USD",
            category="Consulting",
            invoice_number="INV-SUSP-771",
            description="Urgent retainer requested prior to MSA execution",
            status="REJECTED",
            cfo_recommendation="REJECT",
            cfo_rationale="Expense of $6,400.00 exceeds single transaction ceiling ($5,000) and triggers fraud anomaly rules.",
            budget_impact_pct=18.28,
            runway_impact_days=6,
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add_all([draft_safe, draft_threat])
        db.commit()
        db.refresh(draft_safe)
        db.refresh(draft_threat)

        # Risk Assessments
        risk_safe = RiskAssessment(
            business_id=demo_business.id,
            payment_draft_id=draft_safe.id,
            risk_score=5.0,
            risk_level="LOW",
            verdict="SAFE_TO_PAY",
            flags=json.dumps(["Verified reputable vendor domain (aws.amazon.com).", "Transaction is within typical baseline velocity."]),
            anomaly_detected=False,
            vendor_verified=True,
            is_duplicate_invoice=False,
            verification_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            created_at=datetime.utcnow() - timedelta(hours=4),
        )

        risk_threat = RiskAssessment(
            business_id=demo_business.id,
            payment_draft_id=draft_threat.id,
            risk_score=82.0,
            risk_level="CRITICAL",
            verdict="BLOCKED",
            flags=json.dumps([
                "Unverified vendor domain 'fastpay-offshore99.xyz' - first-time payee.",
                "High-value transaction ceiling exceeded ($5,000 threshold).",
                "Anomaly: Urgent keyword combined with non-standard overseas domain."
            ]),
            anomaly_detected=True,
            vendor_verified=False,
            is_duplicate_invoice=False,
            verification_hash="fa25b78e901a182937cd9a842f1b0a827419e99274291849182371928419281a",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add_all([risk_safe, risk_threat])

        # Security Alert
        alert1 = SecurityAlert(
            business_id=demo_business.id,
            severity="HIGH",
            title="High-Risk Offshore Invoicing Attempt Blocked",
            description="Guardian AI prevented automated payout to unverified payee 'FastPay Offshore Ltd' ($6,400.00).",
            status="OPEN",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(alert1)

        # Audit Logs
        audit_records = [
            AuditLog(
                business_id=demo_business.id,
                user_id=demo_user.id,
                stage="UNDERSTAND",
                actor="AI_CFO",
                action="INGEST_INVOICE",
                summary="Ingested invoice from Amazon Web Services for $420.00 USD",
                details="Invoice #INV-AWS-2026-904 for compute hosting.",
                rationale="Parsed line items, currency, and matched against vendor master profile.",
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
            AuditLog(
                business_id=demo_business.id,
                user_id=demo_user.id,
                stage="ANALYZE",
                actor="AI_CFO",
                action="EVALUATE_BUDGET_RUNWAY",
                summary="CFO Recommendation: APPROVE (Budget impact: 1.2%)",
                details="Current cash runway: 4.2 months. Operating balance: $148,500.00",
                rationale="Expense falls comfortably within operational discretionary threshold.",
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
            AuditLog(
                business_id=demo_business.id,
                user_id=demo_user.id,
                stage="INVESTIGATE",
                actor="GUARDIAN_AI",
                action="FRAUD_SECURITY_SCAN",
                summary="Security scan completed: Risk Level LOW (Score: 5.0/100)",
                details="Domain verified, no duplicate invoices detected.",
                rationale="Target payee matched verified corporate domain whitelist.",
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
            AuditLog(
                business_id=demo_business.id,
                user_id=demo_user.id,
                stage="DECIDE",
                actor="GUARDIAN_AI",
                action="SECURITY_VERDICT",
                summary="Guardian Verdict: SAFE_TO_PAY",
                details="Tamper integrity hash generated and locked.",
                rationale="Safe composite threat rating allows payment gateway authorization.",
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
            AuditLog(
                business_id=demo_business.id,
                user_id=demo_user.id,
                stage="EXPLAIN",
                actor="EXPLAINABILITY_AGENT",
                action="SYNTHESIZE_EXPLANATION",
                summary="Decision #1 explained: Safe operational cloud expense",
                details="Transparent justification generated for executive compliance.",
                rationale="Maintained immutable audit trace according to fintech audit requirements.",
                created_at=datetime.utcnow() - timedelta(hours=4),
            ),
        ]
        db.add_all(audit_records)

        # AI CFO Chat Consultation
        chat_sess = ChatSession(
            business_id=demo_business.id,
            user_id=demo_user.id,
            title="Q4 Runway & Payment Security Review",
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        db.add(chat_sess)
        db.commit()
        db.refresh(chat_sess)

        msg1 = ChatMessage(
            session_id=chat_sess.id,
            role="user",
            content="What is our current runway and how much can we spend before triggering executive dual-approval?",
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        msg2 = ChatMessage(
            session_id=chat_sess.id,
            role="assistant",
            content=(
                "Your current treasury balance is $148,500.00 across operating accounts with a 4.2-month runway horizon. "
                "Under current business settings, any single payout above $1,000.00 requires dual approval, while transactions "
                "under $250.00 from verified vendors are pre-cleared by Guardian AI."
            ),
            reasoning_meta=json.dumps({"metric_checked": "runway_months", "dual_approval_ceiling": 1000.00}),
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        db.add_all([msg1, msg2])
        db.commit()

    return {
        "user_email": demo_user.email,
        "business_name": demo_business.name,
        "business_id": demo_business.id,
    }
