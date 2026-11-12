# 🛡️ GUARDIAN CFO
### *The AI CFO That Thinks Before It Pays*

**Guardian CFO** is an autonomous financial intelligence, cash flow analytics, and payment security system designed for small and medium businesses (SMBs). It calculates real ledger revenue, expenses, and cash flow margins, detects unusual expense spikes and recurring commitments, enforces fraud guardrails, executes verified payments through PayPal REST APIs, and maintains a tamper-resistant explainability audit trail.

---

## 📚 Complete Project Documentation

| Documentation Guide | Target Focus |
|:---|:---|
| 🏛️ **[System Architecture](docs/ARCHITECTURE.md)** | Zero-trust pipeline, dual-engine AI CFO, 10-signal risk engine, PayPal Orders v2 |
| 🗄️ **[Database Schema & ERD](docs/DATABASE_SCHEMA.md)** | Full specification of all 14 relational tables, Alembic migrations, tenant isolation |
| 🔌 **[REST API Reference](docs/API_DOCUMENTATION.md)** | Complete endpoints reference, request/response models, error codes |
| 💳 **[PayPal Sandbox Setup Guide](docs/PAYPAL_SANDBOX_SETUP.md)** | Developer sandbox keys, Orders v2 checkout, webhook signature verification |
| 💻 **[Installation Guide](docs/INSTALLATION_GUIDE.md)** | Step-by-step local setup for Windows, macOS, and Linux |
| 🧪 **[Comprehensive Testing Report](docs/TESTING_REPORT.md)** | Full audit report across 18 mandated security and operational dimensions |
| 🎬 **[Hackathon Demo Presentation Script](docs/DEMO_SCRIPT.md)** | 4-scene demonstration script with talking points for hackathon judges |
| ⚠️ **[Known Limitations & Roadmap](docs/KNOWN_LIMITATIONS.md)** | Truthfully documented demonstration constraints and production hardening path |
| 🐳 **[Production Deployment Guide](docs/DEPLOYMENT.md)** | Multi-container Docker Compose and cloud containerization instructions |

---

## 🧭 The Core Workflow Pipeline

Guardian CFO enforces an autonomous 8-stage zero-trust decision cycle:

$$\text{Understand} \longrightarrow \text{Analyze} \longrightarrow \text{Investigate} \longrightarrow \text{Decide} \longrightarrow \text{Approve} \longrightarrow \text{Pay} \longrightarrow \text{Monitor} \longrightarrow \text{Explain}$$

| # | Stage | Agent / Module | Responsibility |
|---|---|---|---|
| **1** | **Understand** | **AI CFO** | Ingests invoices, vendor details, currency, and line items. |
| **2** | **Analyze** | **Analytics Engine** | Evaluates treasury impact, cash flow, burn rate, and runway consumption. |
| **3** | **Investigate** | **Guardian AI** | Runs fraud checks, duplicate detection, and vendor domain verification. |
| **4** | **Decide** | **Guardian AI** | Synthesizes threat scores (0–100) and produces cryptographic integrity hashes. |
| **5** | **Approve** | **Governance** | Authorizes payout under executive policies and thresholds. |
| **6** | **Pay** | **Payment Agent** | Generates authentic PayPal REST API v2 Orders and sandbox checkout flows. |
| **7** | **Monitor** | **System Watcher** | Captures payment completion and verifies ledger balance settlement. |
| **8** | **Explain** | **Explainability** | Produces clear natural-language rationale and immutable audit trails. |

---

## 📊 Financial Analytics Engine (Zero Hallucination)

All financial metrics are computed deterministically in Python using verified database records:

$$\text{Net Cash Flow} = \text{Total Revenue} - \text{Total Expenses}$$

$$\text{Revenue Growth (\%)} = \left(\frac{\text{Current Revenue} - \text{Previous Revenue}}{\text{Previous Revenue}}\right) \times 100$$

$$\text{Expense Change (\%)} = \left(\frac{\text{Current Expense} - \text{Previous Expense}}{\text{Previous Expense}}\right) \times 100$$

### Key Features
1. **Total Revenue & Expenses**: Aggregated across completed transactions with period comparison.
2. **Net Cash Flow**: Calculated directly from verified income and expenditure.
3. **Monthly Trends**: 6-month historical timeline visualizer for revenue, expenses, and net cash flow.
4. **Expense Categorization**: Proportional percentage share calculation across spend buckets.
5. **Unusual Expense Increase Alerts**: Algorithmic detection of month-over-month category spikes (e.g. surges > 35%).
6. **Recurring Obligations**: Identification of regular subscriptions (AWS, Stripe, GitHub, Facilities).

---

## 🤖 AI CFO: Intelligent Natural Language Financial Assistant

The AI CFO translates complex balance sheets, expenses, and transaction logs into natural, actionable executive advice. It supports multi-turn conversations and generates dynamic insight cards.

### Core Capabilities
- **Strictly Read-Only & Zero Hallucination**: Financial figures are never guessed or invented by the LLM. The AI only cites figures queried from the database via approved tools.
- **Approved Analytics Tools**:
  - `get_financial_summary`: Real-time revenue, burn rate, cash flow, and runway months.
  - `get_category_breakdown`: Relative expenditure share across operating buckets.
  - `get_top_vendors`: High-cost vendor commitments and vendor trust scores.
  - `check_affordability`: Proposed purchase impact on treasury balance, runway days, and monthly budget.
  - `get_unusual_spending_patterns`: Month-over-month cost spikes and anomaly flags.
  - `get_recurring_commitments`: Recurring software subscriptions and fixed overhead.
  - `compare_periods`: Period-over-period growth and net cash delta.
- **Security Boundaries**: AI CFO is strictly an **advisory system**. It cannot alter balances, modify ledgers, or authorize payments. Payment disbursement requires human executive approval and Guardian AI risk verification.
- **Dual Engine Architecture**: Works seamlessly with OpenAI GPT-4o structured tool calling when `OPENAI_API_KEY` is provided, and automatically switches to an internal algorithmic fallback engine when running offline or in zero-configuration mode.

---

## 🛡️ Guardian AI: Deterministic Payment Risk Detection Engine

Guardian AI intercepts proposed invoices and audits them against 10 discrete fraud signals before disbursement can be approved.

### Configurable Risk Policy Thresholds
- **LOW (0–24)**: Verdict: `SAFE_TO_PAY` | Action: `ALLOW`
- **MEDIUM (25–49)**: Verdict: `REQUIRES_MANUAL_REVIEW` | Action: `MANUAL_REVIEW_REQUIRED`
- **HIGH (50–74)**: Verdict: `REQUIRES_DUAL_EXECUTIVE_APPROVAL` | Action: `DUAL_EXECUTIVE_APPROVAL_REQUIRED`
- **CRITICAL (75–100)**: Verdict: `BLOCKED` | Action: `REJECT_AND_BLOCK`
*(Demonstration policy thresholds, not validated fraud probabilities)*

### 10 Discrete Risk Signals
1. **First-Time Vendor**: Checks for lack of settled historical transactions.
2. **Unusual Payment Amount**: Flags statistical outliers and payments exceeding 2.5x vendor historical averages.
3. **Duplicate Invoice**: Detects matching invoice reference numbers across historical drafts.
4. **Duplicate Payment (Velocity Replay)**: Detects identical payment amounts to the same payee within 72 hours.
5. **Unusual Payment Frequency**: Flags high-velocity payment bursts (> 3 requests in 7 days).
6. **Vendor Information Mismatch**: Identifies brand spoofing (e.g. corporate brand name on generic/unrelated domain).
7. **Payment Exceeding Business Limits**: Enforces hard single-payment limits and monthly budget ceilings.
8. **Unusual Category Spending**: Cross-checks category outflow surges (> 40% month-over-month increase).
9. **Unusual Transaction Timing**: Detects weekend and off-hours corporate payment submissions.
10. **Missing Vendor Verification Information**: Tracks missing contact info, unverified domains, or low trust scores.

### Integrity & Audit Guarantee
- **No LLM Overrides**: The LLM cannot calculate, reduce, or bypass risk scores or policy restrictions.
- **Cryptographic Hash**: Every assessment receives an immutable SHA-256 verification hash (`verification_hash`).
- **Real-Time Security Alerts**: Critical-risk payments generate open `SecurityAlert` records in the database.

---

## 🔐 Multi-Tenant Architecture & Database Schema (14 Tables)

Guardian CFO guarantees strict tenant isolation. One business can never access another business's data.

1. **`users`**: Authentication credentials (bcrypt salted hashes), roles, and active states.
2. **`businesses`**: Isolated business accounts, treasury balances, and currency configurations.
3. **`business_settings`**: Governance policies, auto-approval thresholds, and risk tolerance levels.
4. **`transactions`**: Ledger records of all income and expenses with PayPal order IDs.
5. **`vendors`**: Payee directory with domain verification, trust scores, and lifetime settlement totals.
6. **`payment_drafts`**: Proposed invoices undergoing CFO runway analysis.
7. **`payment_approvals`**: Dual authorization audit records.
8. **`risk_assessments`**: Threat scores (0–100), heuristic anomaly flags, and SHA-256 integrity digests.
9. **`security_alerts`**: Intercepted high-risk invoice notifications.
10. **`audit_logs`**: Immutable audit history across all 8 pipeline stages.
11. **`chat_sessions`**: Advisory consultation sessions.
12. **`chat_messages`**: Contextual reasoning messages with tool metadata.
13. **`webhook_events`**: Idempotent PayPal event processing records.
14. **`notifications`**: Persistent real-time user notification and alert stream.

*(For full column types, indexes, and ER diagram, see **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)**)*

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts, Lucide Icons.
- **Backend**: Python 3.13, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings, PyJWT, bcrypt.
- **Database & Migrations**: SQLAlchemy 2.0 with Alembic migrations, PostgreSQL standard (psycopg3) and zero-config SQLite local development fallback.
- **Payments**: PayPal REST API v2 (OAuth2 client credentials & orders capture in Sandbox mode).

---

## 🚀 Quickstart Guide: Running in VS Code

### Option A: Using VS Code Integrated Tasks (Recommended)
1. Open the project folder in VS Code (`File` > `Open Folder...`).
2. Press `Ctrl + Shift + P` and type `Tasks: Run Task`.
3. Select **`Run Backend (FastAPI)`** (starts backend on `http://127.0.0.1:8000`).
4. Press `Tasks: Run Task` and select **`Run Frontend (Next.js)`** (starts frontend on `http://localhost:3000`).
5. Open your browser to **[http://localhost:3000](http://localhost:3000)**.
6. Click the **"Safe Demo Login"** button in the header or login modal to explore the pre-seeded **Acme Autonomous Corp** multi-month ecosystem.

---

### Option B: Using Windows Batch Launchers
```powershell
# Terminal 1 (Backend):
.\run-backend.bat

# Terminal 2 (Frontend):
.\run-frontend.bat
```

---

## 🧪 Automated Testing

### 1. Financial Analytics Calculations & API Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_analytics.py
```
Verifies:
- Revenue, expense, and net cash flow formula precision
- Division by zero and missing data safety
- 6-month trend aggregation
- Categorization percentage shares
- Unusual expense increase detection
- Recurring subscription tracking
- Authenticated analytics API endpoints

### 2. AI CFO Intelligent Financial Assistant Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_ai_cfo.py
```
Verifies:
- Approved read-only tool calling execution directly against SQLite ledger
- Natural language queries across all required question intents
- Payout affordability checks with treasury runway & dual approval guardrails
- Multi-turn conversation history persistence in `chat_sessions` and `chat_messages`
- Tenant data boundary protection (prevents cross-business access)
- Advisory-only security constraint (no balance alteration or unapproved disbursements)

### 3. Guardian AI Payment Risk Detection Engine Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_guardian_risk.py
```
Verifies:
- Normal payment baseline (Score 0.0/100, `SAFE_TO_PAY`, `ALLOW`)
- Unusual payment amount and category surge (`REQUIRES_MANUAL_REVIEW`)
- Duplicate invoice reference and 72-hour replay velocity detection
- Critical brand impersonation and policy limit breach (Score >= 75.0, `BLOCKED`, `REJECT_AND_BLOCK`)
- Automatic `SecurityAlert` creation and resolution endpoints
- SHA-256 cryptographic digest integrity

### 4. Secure Payment Management System Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_payment_system.py
```
Verifies:
- Payee vendor registration with domain trust evaluation and directory listing
- Payment draft creation with server-side validations (amount, currency whitelist, purpose)
- Idempotency deduplication preventing duplicate drafts and replay submissions
- Automatic Guardian AI risk scanning integration
- Approval invalidation on draft modification (clears approval timestamp and resets to `REVIEW_REQUIRED`)
- Explicit user approval and cryptographic `details_hash` locking
- Execution prevention on unapproved or altered drafts (HTTP 400 guardrail)
- Simulated Clearing Provider execution (`APPROVED` -> `PROVIDER_PENDING` -> `COMPLETED`)
- Treasury ledger balance decrements and vendor lifetime paid updates
- Idempotent execution preventing double debits

### 5. Core API, Authentication & Guardian Integration Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_api.py
```
Verifies:
- Database health check
- User registration and JWT login
- Scoped company metrics
- Invoice ingestion and runway evaluation
- Guardian AI threat scoring and audit trail generation

### 6. PayPal REST API v2 Orders & Sandbox Integration Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_paypal_integration.py
```
Verifies:
- Safe credential status query (masked client ID, zero secret exposure)
- In-memory OAuth2 token caching with expiration buffers and cache invalidation
- Pre-flight security guardrails (blocks unapproved drafts from initiating orders)
- Orders v2 creation (`POST /v2/checkout/orders`) with idempotency and approval URL capture
- Orders v2 live status query (`GET /v2/checkout/orders/{id}`)
- Orders v2 capture (`POST /v2/checkout/orders/{id}/capture`), treasury balance debit, and vendor updates
- Order cancellation (`POST /v2/checkout/orders/{id}/cancel`) and draft status rollback to `APPROVED`
- HTTP endpoints with strict error handling and clean JSON error responses

### 7. Mandatory Approval & Security Workflow Tests
```powershell
.\backend\venv\Scripts\python.exe backend\tests\test_approval_security_workflow.py
```
Verifies:
- Approval bypass attempts blocked on unapproved drafts (HTTP 400)
- Exact payee, amount, currency, purpose, and invoice binding via SHA-256 `details_hash`
- Covert tampering detection (direct database modification revokes approval and halts execution)
- API-level parameter modification invalidates approval and resets status to `REVIEW_REQUIRED`
- Mandatory blocks for critical-risk invoices (HTTP 403 Forbidden, non-overrideable by prompt/chat)
- Configurable dual-control review rules (Four-Eyes Principle: requires two distinct executive signers for high risk/value payouts)
- Separation of duties enforcement (same executive cannot self-dual-approve)
- Safe expiration of stale approvals (validity window of 24 hours)
- Replay and duplicate execution prevention
- Formal rejection recording with required corporate justification and audit history
- Full HTTP API endpoints via `TestClient`

---

## 🔐 Mandatory Payment Approval & Security Policy Engine

Guardian CFO enforces strict backend security invariants to eliminate single points of failure, unauthorized disbursements, and fraud.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MANDATORY PAYMENT APPROVAL PIPELINE                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
  1. Draft Ingestion          -> Server-side validation (amount > 0, currency whitelist, purpose)
  2. Guardian AI Scan         -> 10-signal threat investigation & composite scoring (0–100)
  3. Policy Determination     -> Evaluates limits, fraud verdict, and dual-control rules
  4. Executive Review Screen  -> Comprehensive payee verification, runway impact, and threat audit
  5. User Sign-off / Rejection-> Explicit human authorization or rejection with mandatory rationale
  6. Cryptographic Binding    -> SHA-256 details_hash locks payee, amount, currency, and purpose
  7. Pre-Execution Clearance  -> Strict checks: Approved, Unexpired (24h), Tamper-intact, Dual-approved
  8. Provider Disbursement    -> Official PayPal Orders v2 or Simulated Clearing Provider
  9. Ledger Reconciliation    -> Verifies provider COMPLETED status before decrementing treasury balances
```

### Core Security Invariants
- **Backend-Enforced Governance**: Every policy check, limit, and authorization threshold is enforced exclusively in Python backend code—never delegated to an LLM.
- **Non-Overrideable Critical Blocks**: When Guardian AI flags a transaction as `CRITICAL` (score >= 75 or verdict `BLOCKED`), approval is strictly forbidden with HTTP 403. Prompt injection and natural-language instructions cannot bypass this block.
- **Four-Eyes Principle (Dual-Control)**: Disbursements exceeding the corporate threshold (`$1,000` default) or flagged with elevated risk (`HIGH`) require two distinct executive authorizations. The primary signer cannot self-grant secondary approval.
- **Tamper Detection & Invalidation**: Modifying payee, amount, currency, or purpose immediately invalidates prior approvals, clears authorization timestamps, and resets the draft to `REVIEW_REQUIRED`.
- **Safe 24-Hour Expiration**: Stale approvals automatically expire after 24 hours. The system transitions them to `EXPIRED` and requires a fresh risk scan and re-authorization before funds can be released.
- **Replay & Double-Charge Immunity**: Client-supplied `idempotency_key` ensures replay attempts return existing settlement records without re-debiting corporate funds.

---

## 💳 Secure Payment Management System

The Payment Management System enables controlled corporate disbursements under strict dual-control governance:

### 10 Payment Lifecycle States
1. **`DRAFT`**: Proposal created with vendor, amount, currency, purpose, and invoice reference.
2. **`RISK_REVIEWED`**: Guardian AI 10-signal scan completed with low risk.
3. **`AWAITING_APPROVAL`**: Medium-to-high risk draft awaiting authorized sign-off.
4. **`APPROVED`**: Explicit executive approval granted; cryptographic `details_hash` locked.
5. **`PROVIDER_PENDING`**: Dispatched to clearing house or PayPal Sandbox awaiting confirmation.
6. **`COMPLETED`**: Provider confirmed settlement; treasury balances decremented.
7. **`REJECTED`**: Blocked by Guardian policy or explicitly rejected by user.
8. **`FAILED`**: Provider rejected transaction or communication error.
9. **`EXPIRED`**: Invoice passed validity period.
10. **`REVIEW_REQUIRED`**: Core parameters modified after review; approval invalidated for re-audit.

### Security Guarantees & Safeguards
- **Server-Side Validation**: Enforces positive amounts, whitelisted ISO currencies (`USD`, `EUR`, `GBP`, `INR`, `CAD`, `AUD`), and explicit commercial purpose.
- **Idempotency Keys**: All drafts and executions accept client idempotency keys to eliminate double debits and replay attacks.
- **Approval Invalidation**: Any change to payee, amount, currency, or purpose triggers automatic approval revocation.
- **AI Chat Guardrail**: Natural language AI CFO chat is strictly advisory; payments can only be initiated and authorized via explicit user action in the Payment Center.
- **Dual Execution Engine**:
  - `SIMULATED_PROVIDER`: Immediate verified local clearing with ledger debit for zero-dependency development and demonstration.
  - `PAYPAL_SANDBOX`: Official PayPal REST API v2 Checkout Orders and Capture workflow.

---

## 🅿️ PayPal REST API Sandbox Setup Guide

Guardian CFO natively integrates with the official **PayPal REST API Orders v2** using PayPal Sandbox ([Official PayPal Documentation](https://developer.paypal.com/api/rest/)).

```
┌──────────────┐          ┌────────────────┐          ┌───────────────────────┐
│   Frontend   │          │ Guardian CFO   │          │   PayPal Sandbox      │
│ (Payment UI) │          │    Backend     │          │    REST API v2        │
└──────┬───────┘          └───────┬────────┘          └───────────┬───────────┘
       │                          │                               │
       │ 1. Execute Draft         │                               │
       │─────────────────────────>│                               │
       │                          │ 2. Fetch OAuth2 Bearer Token  │
       │                          │──────────────────────────────>│
       │                          │<──────────────────────────────│
       │                          │                               │
       │                          │ 3. Create Order v2 (CAPTURE)  │
       │                          │──────────────────────────────>│
       │                          │<──────────────────────────────│
       │                          │    (Returns Approval URL)     │
       │ 4. Return Approval URL   │                               │
       │<─────────────────────────│                               │
       │                                                          │
       │ 5. User Authorizes in Sandbox Window                     │
       │─────────────────────────────────────────────────────────>│
       │                                                          │
       │ 6. Auto-Redirect / Capture                               │
       │─────────────────────────>│                               │
       │                          │ 7. Capture Order v2           │
       │                          │──────────────────────────────>│
       │                          │<──────────────────────────────│
       │                          │    (Status == COMPLETED)      │
       │                          │                               │
       │                          │ 8. Settle Treasury Ledger     │
       │                          │    & Log Audit Stages         │
       │ 9. Confirmed Completed   │                               │
       │<─────────────────────────│                               │
```

### Step 1: Create a PayPal Developer Account
1. Visit the [PayPal Developer Portal](https://developer.paypal.com/).
2. Log in with your standard PayPal credentials or create a new developer account.

### Step 2: Create a Sandbox REST API App
1. Go to the [PayPal Developer Dashboard > Apps & Credentials](https://developer.paypal.com/dashboard/applications/sandbox).
2. Ensure the toggle is set to **Sandbox**.
3. Click **"Create App"**.
4. Set App Name to `Guardian CFO Sandbox` and App Type to **Merchant**.
5. Click **"Create App"**.

### Step 3: Copy Sandbox Credentials to Backend
1. Copy the **Client ID** and click "Show" to copy the **Secret Key**.
2. Open `backend/.env` (or copy from `backend/.env.example`).
3. Set your credentials:
   ```env
   PAYPAL_MODE="sandbox"
   PAYPAL_CLIENT_ID="AXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
   PAYPAL_CLIENT_SECRET="EYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"
   ```
4. Save the file. The backend loads these environment variables on startup.

### Step 4: Locate Sandbox Buyer Test Account
1. In the PayPal Developer Dashboard, navigate to **Testing Tools** > **Sandbox Accounts**.
2. PayPal automatically generates two accounts for you:
   - **Business Account** (facilitator / merchant)
   - **Personal Account** (buyer)
3. Click the three dots `...` next to the **Personal (Buyer)** account and select **View/Edit Account**.
4. Note the **Email ID** (e.g. `sb-buyer123@personal.example.com`) and **System Generated Password**.

### Step 5: Execute an End-to-End Sandbox Payment
1. Open the Guardian CFO web app at **[http://localhost:3000](http://localhost:3000)**.
2. In the top navigation, click **Payment Center**.
3. Under the **"PayPal REST API Status"** badge in the header:
   - If credentials are set, it will display a green **"Connected"** badge with masked Client ID.
   - If not set, it displays **"Setup Required"** with a guided setup modal (the app will guide you and will never fabricate a false PayPal transaction).
4. Create a payment draft or select an existing draft.
5. If the draft is in `REVIEW_REQUIRED`, click **"Run Risk Scan"** to let Guardian AI evaluate the draft.
6. Click **"Approve Draft"** to lock the cryptographic integrity hash.
7. Click **"Execute Approved Payout"**.
8. Select **"PayPal Sandbox (Official REST API v2)"** as the payment method and click **"Execute via Clearing Provider"**.
9. A PayPal Sandbox authorization window opens automatically.
10. Log in with your Sandbox **Personal (Buyer)** account credentials and click **"Complete Purchase"**.
11. PayPal redirects back to Guardian CFO. The backend verifies capture completion (`COMPLETED`), decrements the business treasury balance, updates vendor lifetime paid metrics, and records immutable `PAY` and `MONITOR` audit log events!

### Security & Compliance Invariants
- **Zero Exposure**: `PAYPAL_CLIENT_SECRET` is strictly read by the backend server; it is never exposed over any API endpoint or in client JavaScript bundles.
- **Strict Pre-Flight Check**: Only drafts with status `APPROVED` and matching `details_hash` can initiate PayPal Orders. Unapproved or modified drafts are rejected with HTTP 400.
- **Idempotency Protection**: Every order creation and capture request transmits a unique `PayPal-Request-Id` to prevent duplicate checkout sessions or double debits.
- **Zero Frontend Trust**: The frontend status is never trusted. Transactions are only marked `COMPLETED` when the PayPal REST API explicitly returns `status == "COMPLETED"`.
- **Truthful Status Reporting**: If PayPal credentials are not configured, Guardian CFO truthfully reports `paypal_not_configured` and never fabricates a simulated PayPal transaction under the guise of the real API.

---

## 🔍 Explainability, Audit, Notifications & PayPal Webhooks

Guardian CFO provides end-to-end transparency, real-time alerts, and cryptographic webhook verification.

### 1. The 6-Question Transparent Explainability Framework
For any financial decision or payment draft, Guardian CFO generates structured, deterministic answers:
1. **What happened?** — Complete narrative breakdown of draft origination, payee, amount, currency, invoice reference, and current lifecycle state.
2. **Why was it flagged?** — Plain-language executive rationale explaining the Guardian AI risk score (0–100) and security verdict.
3. **What evidence was detected?** — Granular signal breakdown (e.g. first-time vendor, velocity anomaly, duplicate invoice reference, domain mismatch).
4. **What action was taken?** — Specific governance policy action enforced (e.g., Mandatory Block, Dual-Control Authorization mandated, or Single Sign-off cleared).
5. **Who approved or rejected it?** — Verified multi-party signer records with roles (Signer 1, Signer 2), emails, timestamps, and notes, or explicit rejection rationale.
6. **What is the final provider status?** — PayPal REST API gateway reconciliation, including PayPal Order ID, Capture ID, execution mode (Sandbox/Live), and ledger settlement timestamp.

### 2. Comprehensive Immutable Audit Trail
Records immutable events across the 8-stage pipeline:
- **`USER_LOGIN` / `USER_REGISTER`**: Session establishment and tenant provisioning.
- **`PAYMENT_DRAFT_CREATED`**: Cryptographic fingerprint computation.
- **`FRAUD_RISK_INVESTIGATION`**: Heuristic evaluation and risk scoring.
- **`PRIMARY_APPROVAL_GRANTED` / `DUAL_APPROVAL_COMPLETED`**: Multi-party executive authorizations.
- **`PAYMENT_REJECTED`**: Explicit reasons recorded.
- **`CREATE_PAYPAL_ORDER` / `CAPTURE_PAYPAL_ORDER`**: REST API interactions.
- **`PAYPAL_WEBHOOK_RECEIVED` / `PAYPAL_WEBHOOK_CAPTURE_COMPLETED`**: Asynchronous reconciliation.
- **`POLICY_VIOLATION`**: Rejection of unauthorized bypasses, critical-risk executions, or self-approvals.
- **`CONFIGURATION_CHANGED`**: Updates to treasury guardrails, spending ceilings, or dual-approval thresholds.

### 3. Real-Time Security Notifications
Maintains persistent alerts with severity badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`):
- `HIGH_RISK_DETECTED`: Intercepted fraudulent or high-risk invoices.
- `PAYMENT_AWAITING_APPROVAL`: Secondary or executive sign-off required.
- `PAYMENT_APPROVED`: Ready for provider clearing.
- `PAYMENT_REJECTED`: Declined with reason.
- `PAYMENT_COMPLETED`: Provider capture confirmed.
- `PAYMENT_FAILED`: Clearing declined or voided.
- `UNUSUAL_FINANCIAL_ACTIVITY`: Anomaly in spending patterns or customer dispute.

### 4. PayPal Webhook Verification & Deduplication
- **Official Signature Verification**: Follows PayPal procedures using `POST /v1/notifications/verify-webhook-signature` with `paypal-auth-algo`, `paypal-cert-url`, `paypal-transmission-id`, `paypal-transmission-sig`, and `paypal-transmission-time`.
- **Zero Trust for Unverified Payloads**: Requests with invalid signatures are rejected immediately with HTTP 400 Bad Request and logged as `WEBHOOK_SIGNATURE_FAILED`.
- **Idempotent Deduplication**: Each webhook's `id` is checked against `webhook_events.event_id`. Duplicate events are acknowledged safely with HTTP 200 without duplicate ledger mutations.
- **Supported Webhook Events**:
  - `CHECKOUT.ORDER.APPROVED`: Updates draft to `PROVIDER_PENDING` and alerts officers.
  - `PAYMENT.CAPTURE.COMPLETED`: Reconciles capture, updates treasury balance, and notifies company.
  - `PAYMENT.CAPTURE.DENIED`: Marks draft as `FAILED` and raises high-severity alert.
  - `CUSTOMER.DISPUTE.CREATED`: Records audit event and raises `UNUSUAL_FINANCIAL_ACTIVITY` notification.

---

## 🧪 Comprehensive Automated Test Suites

Run the full automated test suite covering all security, payment, and audit invariants:

```bash
# 1. Audit, Notifications, Explainability & PayPal Webhooks
backend/venv/Scripts/python.exe backend/tests/test_audit_notifications_webhooks.py

# 2. Mandatory Payment Approval & Security Workflow (Dual-Control & Expiration)
backend/venv/Scripts/python.exe backend/tests/test_approval_security_workflow.py

# 3. Official PayPal REST API (Sandbox Orders v2 & Capture Lifecycle)
backend/venv/Scripts/python.exe backend/tests/test_paypal_integration.py

# 4. Payment Management System & Clearing Provider
backend/venv/Scripts/python.exe backend/tests/test_payment_system.py

# 5. Guardian AI 10-Signal Risk Detection Engine
backend/venv/Scripts/python.exe backend/tests/test_guardian_risk.py

# 6. AI CFO Natural Language & Structured Tool-Calling Agent
backend/venv/Scripts/python.exe backend/tests/test_ai_cfo.py

# 7. Financial Analytics Calculation Engine
backend/venv/Scripts/python.exe backend/tests/test_analytics.py

# 8. API Sanity & End-to-End Pipeline
backend/venv/Scripts/python.exe backend/tests/test_api.py

# 9. Master 18-Dimension Security & Functional Audit
backend/venv/Scripts/python.exe backend/tests/test_complete_security_audit.py

# 10. Hackathon Demo Scenarios Verification (Scenes 1-4)
backend/venv/Scripts/python.exe backend/tests/verify_demo_scenes.py
```

---

## 🐳 Containerized Deployment (Docker Compose)

Run the full PostgreSQL, FastAPI backend, and Next.js frontend stack with a single command:

```bash
docker compose up -d --build
```
Open **[http://localhost:3000](http://localhost:3000)** to access the application. See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for cloud deployment instructions.



