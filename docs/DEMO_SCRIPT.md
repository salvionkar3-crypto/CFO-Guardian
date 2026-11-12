# Guardian CFO: PayPal AI Hackathon Demo Presentation Script

**Presentation Duration:** 3–5 Minutes  
**Audience:** PayPal AI Hackathon Judges & Engineering Leads  
**Key Value Proposition:** *"The AI CFO that thinks before it pays — combining real ledger analytics, deterministic risk guardrails, and authentic PayPal REST checkout."*  

---

## 🎤 Opening Hook (30 Seconds)

> *"Judges, every small business owner fears two things: running out of cash without noticing, and accidentally paying a fraudulent or unauthorized supplier invoice. Today, AI chatbots summarize documents, but they cannot manage real money because they hallucinate numbers, have no concept of risk, and can be prompt-injected.*
>
> *Introducing **Guardian CFO** — an autonomous financial intelligence and payment security agent. It calculates real ledger metrics with zero hallucination, audits proposed payments against 10 discrete fraud signals, enforces cryptographic human approval, and executes verified disbursements through the official PayPal REST API. Let's see it in action across four real-world scenarios."*

---

## 🎬 SCENE 1: AI CFO Natural Language Consultation (1 Minute)

### Action in UI:
1. Open the dashboard at `http://localhost:3000`.
2. Notice the live telemetry in the header: **FastAPI: Online**, **DB: SQLITE**, **PayPal Sandbox: Ready**, **DEMO MODE**.
3. Click the floating **Ask AI CFO** button in the bottom right, or click the **AI CFO Chat** banner.
4. In the chat drawer, type or click the quick prompt:
   **`"How is my business performing this month?"`**

### What to Show the Judges:
- Point out the **Tools Executed** badge: `['get_financial_summary']`.
- Highlight that the numbers cited in the response are **exact database figures**:
  - **Revenue:** `$18,750.00`
  - **Expenses:** `$17,445.00`
  - **Net Cash Flow:** `$1,305.00`
  - **Runway:** `7.8 Months`
- Point to the dynamic **Insight Card** that rendered alongside the text.

### Key Talking Points:
> *"Notice that the AI did not invent these numbers. Guardian CFO enforces a strict boundary: the LLM is an **advisory intelligence** with access only to read-only database tools. It cannot guess balances, and it has zero authority to execute payments or modify ledgers."*

---

## 🎬 SCENE 2: Normal Payment to Known Vendor (1 Minute)

### Action in UI:
1. Switch to the **Secure Payment Center** tab.
2. Click **Create Payment Draft**.
3. Select an existing verified vendor: **Datadog Cloud Observability** (or **Amazon Web Services**).
4. Enter Amount: **`$280.00`**, Purpose: **`"Monthly application telemetry and infrastructure monitoring per MSA"`**, Invoice #: **`INV-DD-2026-9042`**.
5. Click **Submit Payment Draft**.

### What to Show the Judges:
- **Guardian AI Investigation**:
  - Show the live risk evaluation: Risk Score **`LOW`**, Verdict **`SAFE_TO_PAY`**.
  - Show the financial runway impact: **`0.8% of monthly budget`**.
- **Human Governance Gate**:
  - Show that the payment is **not yet executed**; it is paused in `REVIEW_REQUIRED`.
  - Enter approval note: *"Verified against PO statement. Approved."* and click **Approve Payment**.
  - Show the cryptographic **Details Hash** (`details_hash`), which locks the exact payee, amount, currency, and purpose with SHA-256.
- **PayPal Sandbox Execution**:
  - Click **Execute Payment (PayPal Sandbox)**.
  - Show the authentic PayPal Orders v2 session created (`PROVIDER_PENDING`).
  - Demonstrate settlement capture: Transaction status moves to **`COMPLETED`**, and the treasury balance decrements cleanly.

### Key Talking Points:
> *"Here, Guardian CFO verified that the vendor is recognized and the amount is within safe policy limits. Once approved, the payment parameters were cryptographically sealed with a SHA-256 fingerprint before initiating PayPal Orders v2."*

---

## 🎬 SCENE 3: Suspicious Payment & Guardian Interception (1 Minute)

### Action in UI:
1. Still in the **Secure Payment Center**, click **Create Payment Draft**.
2. Select **+ Add New Payee**:
   - Vendor Name: **`Global Offshore FinTech Direct Ltd`**
   - Invoicing Email: **`transfers@global-offshore99.xyz`**
   - Website: **`http://global-offshore99.xyz`**
   - PayPal Email: **`wire-dest@global-offshore99.xyz`**
3. Enter Amount: **`$25,000.00`** (Exceeds the $5,000 business ceiling).
4. Purpose: **`"Urgent corporate re-structuring advance advisory fee"`**.
5. Click **Submit Payment Draft**.

### What to Show the Judges:
- Point out the **Guardian AI Risk Badge**:
  - Risk Score: **`85.0 / 100`** (**`CRITICAL`**).
  - Verdict: **`BLOCKED`** (Recommended Action: **`REJECT_AND_BLOCK`**).
- Expand the **Detected Risk Signals** accordion:
  1. **First-Time Vendor** (+20.0 pts): Unestablished payee with 0 prior transactions.
  2. **Unusual Payment Amount** (+25.0 pts): Outlier amount 44x higher than standard company average.
  3. **Exceeds Business Ceiling** (+25.0 pts): $25,000 exceeds the $5,000 maximum single-payment policy.
  4. **Unusual Transaction Timing** (+15.0 pts): Submission generated during non-standard hours.
- Show the **Policy Pause**:
  - The **Approve Payment** button is disabled with a red security banner: *"Mandatory Block: Critical risk payment cannot be approved."*
  - Demonstrate that attempting to bypass via API returns **`HTTP 403 Forbidden`**.

### Key Talking Points:
> *"This is where Guardian CFO shines. An employee or adversary attempting to push an urgent, unauthorized payment to an offshore entity is immediately stopped. The AI risk engine is deterministic—prompt injections cannot convince it to lower the score, and unilateral executive override is strictly prohibited."*

---

## 🎬 SCENE 4: 6-Question Explainability & Audit Trail (45 Seconds)

### Action in UI:
1. Click the **Security Activity & Audit** tab.
2. Select the recent payment drafts from the left list.
3. Show the **6-Question Transparent Explainability Inspector**:
   - **1. What happened?** $\rightarrow$ Plain-language summary of the proposed transaction.
   - **2. Why was it flagged?** $\rightarrow$ Specific risk heuristic rationale.
   - **3. What evidence was detected?** $\rightarrow$ Clear audit evidence bullet points.
   - **4. What action was taken?** $\rightarrow$ Governance and policy outcome.
   - **5. Who approved or rejected it?** $\rightarrow$ Detailed signer credentials, timestamps, and notes.
   - **6. What is the final provider status?** $\rightarrow$ PayPal Order ID, Capture ID, and settlement state.
4. Show the **Searchable Audit Timeline** below with chronological filter tags.
5. Click the **Notification Bell** in the top header to show real-time security alerts dispatched for high-risk payments.

### Key Talking Points:
> *"For compliance and accounting, every single action—from login to risk scan, executive approval, PayPal checkout, and webhook capture—is logged into an immutable audit trail. Regulators and accountants get complete transparency with zero black-box guesswork."*

---

## 🏆 Closing Summary (15 Seconds)

> *"To summarize: Guardian CFO gives small businesses the intelligence of an experienced CFO and the vigilance of an institutional fraud officer. It is grounded in real database math, protected by cryptographic zero-trust guardrails, and powered by PayPal's trusted payment rails. Thank you, and we welcome your questions!"*

