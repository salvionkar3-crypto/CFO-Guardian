# Guardian CFO: Production Deployment & Containerization Guide

This guide covers deploying **Guardian CFO** in production or staging environments using Docker, Docker Compose, or cloud container platforms (AWS ECS, Google Cloud Run, Azure Container Apps).

---

## 1. Security Pre-Flight Requirements

> [!IMPORTANT]
> **Mandatory Security Checklist Before Deployment:**
> 1. **Zero Secret Exposure**: Never commit `.env`, `.env.local`, or live API keys to Git.
> 2. **Sandbox Protection**: Verify that `PAYPAL_MODE` is strictly set to `"sandbox"`. Never switch to live payments without a dedicated external security audit.
> 3. **CORS Whitelist**: Update `CORS_ORIGINS` to match your exact production domain (e.g. `https://app.guardiancfo.ai`).
> 4. **JWT Secret Randomization**: Ensure that `SECRET_KEY` in `backend/app/core/config.py` is overridden via environment variable with a cryptographically secure 256-bit random string (`openssl rand -hex 32`).
> 5. **HTTPS Enforcement**: Always terminate TLS 1.3 at your reverse proxy (Nginx, Cloudflare, or AWS ALB).

---

## 2. Docker Compose Deployment (Recommended)

Guardian CFO provides a multi-container Docker Compose configuration containing:
- **`postgres`**: PostgreSQL 16 container with persistent data volume.
- **`backend`**: FastAPI application with automatic Alembic migrations on startup.
- **`frontend`**: Next.js 14 production standalone runner.

### Step 1: Configure Environment Variables
Create a root `.env` file from the provided `.env.example`:

```bash
cp .env.example .env
```

Ensure the following variables are configured:
```ini
POSTGRES_PASSWORD=your_secure_postgres_password
OPENAI_API_KEY=your_openai_api_key_or_empty
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your_paypal_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_paypal_sandbox_client_secret
PAYPAL_WEBHOOK_ID=your_paypal_webhook_id
```

### Step 2: Build and Launch Containers
```bash
docker compose up -d --build
```

### Step 3: Verify Health
Check container logs:
```bash
docker compose logs -f
```
The services will be reachable at:
- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`

---

## 3. Production Cloud Deployment (Cloud Run / AWS ECS)

### Backend Container:
- **Image**: Build using `backend/Dockerfile`.
- **Port**: `8000`.
- **Health Check**: `GET /api/v1/health`.
- **Database**: Connect to Amazon RDS PostgreSQL or Google Cloud SQL using `DATABASE_URL`.
- **Scaling**: Horizontally scale stateless FastAPI workers behind an Application Load Balancer.

### Frontend Container:
- **Image**: Build using `frontend/Dockerfile`.
- **Port**: `3000`.
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: Your backend API domain (e.g. `https://api.guardiancfo.ai`).
  - `NEXT_PUBLIC_PAYPAL_CLIENT_ID`: Your PayPal Sandbox client ID.

---

## 4. Database Migrations in CI/CD

Database migrations are managed via Alembic. When deploying updates to production:

```bash
# Run migrations inside the backend container
docker compose exec backend alembic upgrade head
```

To verify the migration head status:
```bash
docker compose exec backend alembic current
```
*(Current migration head: `8f20b345a1c2_add_notifications_table`)*

