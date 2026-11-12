# Guardian CFO: Known Limitations & Production Roadmap

This document outlines the current demonstration limitations of Guardian CFO as presented for the PayPal AI Hackathon, along with the engineering roadmap for enterprise production hardening.

---

## 1. Documented Known Limitations

### 1.1. PayPal Sandbox Live Credentials Dependency
- **Current Behavior:** In environments where developers have not yet configured `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in `backend/.env`, the payment agent gracefully returns `HTTP 400` with `error: "paypal_not_configured"`. 
- **Security Invariant:** The system strictly refuses to fabricate fake PayPal Order IDs or claim authentic checkout success without live provider API confirmation. Users can explore the full flow using the `SIMULATED_PROVIDER` mode until credentials are provided.

### 1.2. OpenAI API Online Dependency & Offline Fallback
- **Current Behavior:** If `OPENAI_API_KEY` is not configured or OpenAI servers experience rate limits, Guardian CFO activates its internal deterministic algorithmic fallback engine.
- **Scope:** The fallback engine accurately executes identical database analytics tools (`get_financial_summary`, `get_category_breakdown`, `compare_periods`, `check_affordability`) and generates rich markdown insight cards. However, open-ended conversational questions outside standard financial intents return guided suggestions rather than unconstrained prose.

### 1.3. Multi-Currency Live Foreign Exchange (FX) Rates
- **Current Behavior:** The database schema supports ISO 4217 currency codes (USD, EUR, GBP, CAD, INR). However, in sandbox demonstration mode, cross-currency settlements use fixed standard conversion baselines rather than a real-time live FX streaming feed.

### 1.4. Invoice Document OCR Ingestion
- **Current Behavior:** Payment drafts ingest metadata (vendor, amount, currency, invoice reference, and invoice URL). In production, an asynchronous OCR pipeline (e.g. AWS Textract or Google Cloud Document AI) would automatically parse uploaded PDF invoices into draft fields.

---

## 2. Production Hardening Roadmap

| Milestone | Target Capability | Production Requirement |
|:---|:---|:---|
| **Phase 1** | **KMS & Secrets Management** | Migrate `.env` credentials to AWS Secrets Manager or HashiCorp Vault. Store JWT signing keys in Cloud KMS. |
| **Phase 2** | **PostgreSQL Multi-Region HA** | Migrate from single-instance SQLite/PostgreSQL to Amazon Aurora Serverless v2 with cross-region read replicas. |
| **Phase 3** | **Open Banking & PSD2 Feeds** | Integrate Plaid or Yapily for real-time commercial bank account balances alongside PayPal merchant balances. |
| **Phase 4** | **Hardware Security Modules (HSM)** | Sign payment details hashes and approvals using FIPS 140-2 Level 3 HSM hardware tokens. |
| **Phase 5** | **SOC 2 Type II Compliance** | Implement automated log immutability via AWS CloudTrail with write-once-read-many (WORM) S3 buckets. |

---

## 3. Security Policy on Real Financial Transactions

> [!CAUTION]
> **MANDATORY PRODUCTION NOTICE**  
> Under no circumstances should Guardian CFO be switched to PayPal Live Mode (`PAYPAL_MODE="live"`) without a separate formal third-party security audit, penetration test, and organization-specific executive approval policy sign-off.

