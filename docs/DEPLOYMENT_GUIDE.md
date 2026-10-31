# AdeptLearn – Deployment & Operations Guide
**Milestone 6 Production Readiness**

---

## 1. Local Development Deployment (Native Windows/Linux)

### 1.1 Prerequisites
- **Operating System:** Windows 11 or Ubuntu 22.04 LTS
- **Python:** Version 3.11 or 3.12 (with active virtual environment)
- **GPU Hardware:** NVIDIA RTX 4050 Laptop GPU (6 GB VRAM) or equivalent with latest Game Ready / Studio drivers.
- **Local AI Runtimes:**
  - **LM Studio:** Running on `http://localhost:1234` with model `oreal-deepseek-r1-distill-qwen-7b`.
  - **Ollama:** Running on `http://localhost:11434` with model `llama3.2:latest`.

### 1.2 Environment Setup & Dependency Installation
```powershell
# 1. Clone repository & navigate to directory
cd "d:\Adaptive Learning"

# 2. Activate virtual environment
.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate  # Linux/macOS

# 3. Install core dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3 Database Migration Execution
```powershell
# Apply latest Alembic migrations to head
alembic upgrade head
```

### 1.4 Launch Local Model Services
1. **LM Studio:**
   - Launch LM Studio desktop app.
   - Load or configure `oreal-deepseek-r1-distill-qwen-7b` on Developer tab.
   - Start local inference server on port `1234` (CORS enabled).
2. **Ollama:**
   - Open terminal and verify service is running:
   ```powershell
   ollama list
   # Verify llama3.2 is available
   ollama pull llama3.2
   ```

### 1.5 Launch FastAPI Backend
```powershell
# Start Uvicorn development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify backend is responding:
```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

---

## 2. Docker & Containerized Deployment

AdeptLearn supports a hybrid container deployment where the FastAPI backend and PostgreSQL database run in Docker, communicating with local host GPU AI runtimes via host networking bridge.

### 2.1 Host-to-Container Network Bridge
In `docker-compose.yml`, the backend service communicates with host AI servers using:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  - LM_STUDIO_BASE_URL=http://host.docker.internal:1234
  - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### 2.2 Starting Services with Docker Compose
```bash
# Build and start services in background
docker compose up -d --build

# View real-time container logs
docker compose logs -f backend

# Verify health status
docker compose ps
```

### 2.3 Executing Migrations in Container
```bash
docker compose exec backend alembic upgrade head
```

---

## 3. Production Hardening & Recommendations

### 3.1 PostgreSQL Database Configuration
In production environments, SQLite is replaced by PostgreSQL 16.
Update `.env`:
```ini
DATABASE_URL=postgresql://adeptlearn:YOUR_STRONG_PASSWORD@localhost:5432/adeptlearn_db
```
PostgreSQL connection pooling is managed via SQLAlchemy's `QueuePool`:
- `pool_size=20`
- `max_overflow=10`
- `pool_pre_ping=True` (reconnects dropped connections automatically)

### 3.2 HTTPS & Reverse Proxy Termination
Always terminate SSL/TLS in production via Nginx or Caddy:
```nginx
server {
    listen 443 ssl http2;
    server_name api.adeptlearn.org;

    ssl_certificate /etc/letsencrypt/live/api.adeptlearn.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.adeptlearn.org/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3.3 GPU Serialization & Scaling Bounds
Because a 6GB VRAM GPU can only execute one model at a time, API throughput for learning turns is serialized.
- **Workers:** Run a single Uvicorn process (`--workers 1`) or use a dedicated Celery/Redis worker for AI inference tasks if scaling multi-process FastAPI workers.
- **Queue Limits:** Requests waiting for GPU execution will queue up to the configured queue timeout (default 60s) before returning `503 Service Unavailable (GPU Overload)`.
