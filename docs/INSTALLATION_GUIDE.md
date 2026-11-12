# Guardian CFO: Local Installation & Setup Guide

This guide covers installing, configuring, and running **Guardian CFO** locally on Windows, macOS, or Linux.

---

## 1. System Prerequisites

Before starting, ensure the following tools are installed:
- **Python**: Version `3.11` or `3.12` (recommended). Verify with `python --version`.
- **Node.js**: Version `18.17+` or `20.x` LTS. Verify with `node -v`.
- **npm**: Version `9.x` or `10.x`. Verify with `npm -v`.
- **Git**: Installed and available in PATH.

---

## 2. Repository Setup

Clone or extract the project repository and open the project root directory:

```bash
cd "pay pal project"
```

---

## 3. Backend Setup (FastAPI & Database)

### Step 1: Create a Python Virtual Environment
On Windows (PowerShell / Command Prompt):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

On macOS / Linux:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the template configuration:
```bash
cp .env.example .env
```
*(On Windows Command Prompt, use `copy .env.example .env`)*

By default, the backend connects to a zero-configuration local SQLite database (`guardian_cfo.db`). If using PostgreSQL in production, update `DATABASE_URL` in `.env`.

### Step 4: Run Database Migrations
Apply all schema tables using Alembic:
```bash
alembic upgrade head
```

### Step 5: Start the Backend Server
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI backend will start at **`http://127.0.0.1:8000`**.  
Interactive Swagger API documentation is available at **`http://127.0.0.1:8000/docs`**.

---

## 4. Frontend Setup (Next.js 14)

### Step 1: Open Frontend Directory
Open a new terminal window:
```bash
cd frontend
```

### Step 2: Install Node Dependencies
```bash
npm install
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

### Step 4: Start Next.js Development Server
```bash
npm run dev
```
The frontend application will start at **`http://localhost:3000`**.

---

## 5. One-Click Launchers (Windows)

For convenience on Windows machines, pre-configured launcher scripts are provided in the project root:

- **Run Backend**: Double-click `run-backend.bat`
- **Run Frontend**: Double-click `run-frontend.bat`

---

## 6. Accessing the Application

1. Open your browser and navigate to **`http://localhost:3000`**.
2. Click **Sign In / Demo** in the top-right header to automatically initialize the pre-seeded **Acme Autonomous Corp** ecosystem.
3. The dashboard will load with live telemetry:
   - FastAPI: **Online**
   - DB: **SQLITE** (or **POSTGRESQL**)
   - PayPal Sandbox: **Ready** (or **Config Needed**)
   - DEMO MODE active badge.

---

## 7. Running the Automated Test Suite

To verify system health and test all modules:

```powershell
# Master 18-dimension security audit suite:
.\backend\venv\Scripts\python.exe backend/tests/test_complete_security_audit.py

# Verify the 4 hackathon demo scenes:
.\backend\venv\Scripts\python.exe backend/tests/verify_demo_scenes.py

# Verify Next.js frontend production build:
cd frontend && npm run build
```

