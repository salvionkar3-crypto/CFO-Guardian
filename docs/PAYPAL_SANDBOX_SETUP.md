# Guardian CFO: PayPal REST API & Sandbox Setup Guide

This guide provides step-by-step instructions for integrating the official **PayPal REST API (Orders v2)** in Sandbox mode with Guardian CFO.

---

## 1. Overview of PayPal Integration

Guardian CFO integrates with the official PayPal REST API in two directions:
1. **Outbound API (Orders v2)**: Creates orders, generates buyer approval URLs, and executes order capture.
2. **Inbound Webhooks**: Receives asynchronous event notifications (order approval, settlement capture) and cryptographically validates the transmission signature before reconciling ledger states.

---

## 2. Obtaining PayPal Developer Sandbox Credentials

### Step 1: Log in to PayPal Developer
1. Go to the [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/).
2. Log in with your standard PayPal account credentials.

### Step 2: Create a Sandbox REST App
1. In the left navigation, select **Apps & Credentials**.
2. Make sure the toggle at the top is set to **Sandbox** (not Live).
3. Click the **Create App** button.
4. Enter an App Name (e.g., `Guardian CFO Sandbox App`).
5. Choose **Merchant** as the App Type.
6. Click **Create App**.

### Step 3: Copy Your Credentials
Once created, your app dashboard will display:
- **Client ID**: A long alphanumeric string (e.g. `Aed...`).
- **Secret**: Click **Show** to reveal the secret key.

---

## 3. Configuring Guardian CFO Environment

### Backend Configuration (`backend/.env`)
Copy your credentials into `backend/.env`:

```ini
# PayPal REST API Credentials (Developer Sandbox)
PAYPAL_MODE="sandbox"
PAYPAL_CLIENT_ID="your_sandbox_client_id_here"
PAYPAL_CLIENT_SECRET="your_sandbox_client_secret_here"
PAYPAL_WEBHOOK_ID="your_sandbox_webhook_id_here"
```

### Frontend Configuration (`frontend/.env.local`)
Provide the client ID to the frontend for SDK initialization:

```ini
NEXT_PUBLIC_API_URL="http://localhost:8000"
NEXT_PUBLIC_PAYPAL_CLIENT_ID="your_sandbox_client_id_here"
```

---

## 4. Setting Up PayPal Webhooks

Webhooks allow PayPal to notify Guardian CFO immediately when a buyer approves or settles an order in Sandbox.

### Step 1: Expose Your Local Backend (for Local Testing)
To receive webhooks locally, expose port 8000 using a secure tunnel tool (e.g. ngrok):
```bash
ngrok http 8000
```
Copy the generated HTTPS URL (e.g. `https://abc123.ngrok-free.app`).

### Step 2: Register Webhook in PayPal Dashboard
1. In your PayPal App Settings in Developer Dashboard, scroll down to **Sandbox Webhooks**.
2. Click **Add Webhook**.
3. In **Webhook URL**, enter:
   `https://<your-tunnel-url>/api/v1/webhooks/paypal`
4. In **Event types**, select:
   - `Checkout order approved` (`CHECKOUT.ORDER.APPROVED`)
   - `Payment capture completed` (`PAYMENT.CAPTURE.COMPLETED`)
   - `Payment capture denied` (`PAYMENT.CAPTURE.DENIED`)
5. Click **Save**.
6. Copy the **Webhook ID** and paste it as `PAYPAL_WEBHOOK_ID` in `backend/.env`.

---

## 5. Creating Sandbox Test Accounts

PayPal Developer automatically provisions sandbox accounts:
1. Navigate to **Testing Tools** > **Sandbox Accounts**.
2. You will find:
   - A **Personal** (Buyer) Account: Use this to log in to the PayPal Sandbox checkout page during payment demonstration.
   - A **Business** (Facilitator) Account: Represents the merchant account.
3. Click the three dots (`...`) next to the Personal account > **View/Edit Account** to see the test login email and system-generated password.

---

## 6. End-to-End Verification Flow

1. **Start Backend & Frontend**:
   ```powershell
   .\run-backend.bat
   .\run-frontend.bat
   ```
2. **Log In to Dashboard**:
   - Navigate to `http://localhost:3000`.
   - Click **Sign In / Demo** (uses pre-seeded demo user).
3. **Inspect PayPal Status in Header**:
   - The header displays `PayPal Sandbox: Ready` when credentials are loaded.
4. **Draft & Approve a Payment**:
   - In **Secure Payment Center**, click **Create Payment Draft**.
   - Select a vendor (e.g. Amazon Web Services) and enter an amount ($420.00).
   - Review Guardian risk signals (Score: Low/Safe).
   - Click **Approve Payment**.
5. **Execute via PayPal Sandbox**:
   - Click **Execute Payment (PayPal Sandbox)**.
   - Guardian CFO creates an authentic Orders v2 session and opens the PayPal Sandbox login modal.
   - Complete checkout with your test Buyer Sandbox account.
   - On capture confirmation, Guardian CFO decrements the ledger balance and records the transaction with PayPal Order ID and Capture ID.

---

## 7. Troubleshooting & Security Guarantees

- **Unconfigured Credentials**: If `PAYPAL_CLIENT_ID` or `PAYPAL_CLIENT_SECRET` are omitted, the backend truthfully returns `HTTP 400` with `paypal_not_configured`. Guardian CFO **never fabricates fake transactions**.
- **Signature Rejection**: If an inbound webhook fails cryptographic validation or is received with an invalid certificate chain, the backend rejects it with `HTTP 400 Bad Request`.
- **Replay Protection**: If an identical `event_id` is received twice, Guardian CFO acknowledges it with `HTTP 200` but discards the duplicate payload without re-executing balance adjustments.

