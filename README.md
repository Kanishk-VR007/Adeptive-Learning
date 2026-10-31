# AdeptLearn – Adaptive Exam-Prep Tutor
**Complete Production Backend Engine (Milestone 6 Release)**

AdeptLearn is a state-of-the-art, modular, agentic AI tutoring backend designed to guide students through a personalized, mastery-driven learning lifecycle. It unites:
1. **Bayesian Knowledge Tracing (BKT):** Deterministic mathematical modeling of student knowledge states and transition probabilities.
2. **Free Spaced Repetition Scheduler (FSRS):** Scientific memory consolidation intervals based on recall performance.
3. **LangGraph Agentic Orchestration:** Multi-node graph coordinating multi-turn student learning workflows, state checkpoints, and recovery.
4. **Local AI Dual-Model Architecture:**
   - **DeepSeek-R1-Distill-7B** (via LM Studio): Deep conceptual reasoning, error diagnosis, and misconception detection.
   - **Llama 3.2** (via Ollama): Socratic questioning, pedagogical hints, and empathetic student feedback.
5. **Centralized GPU Execution Manager:** Serialized FIFO model swapping and VRAM monitoring preventing OOM on 6 GB consumer GPUs (NVIDIA RTX 4050).
6. **Teacher Class & Analytics Dashboard:** Deterministic class rosters, enrollment codes, misconception distributions, and weak concept heatmaps.
7. **Production Containerization & Security:** Comprehensive RBAC, GDPR portability export, account deletion cascading, and Docker support.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Async, OpenAPI/Swagger Docs, Pydantic v2) |
| **Relational Database** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) ORM + [Alembic](https://alembic.sqlalchemy.org/) Migrations |
| **Supported Databases** | SQLite (Local Dev) / PostgreSQL 16 (Production) |
| **Authentication** | JWT (PyJWT) + bcrypt password hashing + `RoleChecker` RBAC |
| **Agent Orchestration** | [LangGraph](https://github.com/langchain-ai/langgraph) (Checkpointing, conditional routing) |
| **Memory Scheduler** | [fsrs-rs / fsrs-python](https://github.com/open-spaced-repetition/fsrs4anki) |
| **Hardware Monitor** | [NVIDIA Management Library (NVML)](https://pypi.org/project/nvidia-ml-py/) |
| **Testing** | [Pytest](https://docs.pytest.org/), `pytest-asyncio`, `pytest-cov` (199+ automated tests) |

---

## 🚀 Quick Start Guide

### 1. Local Python Environment
```powershell
# Clone and enter workspace
cd "d:\Adaptive Learning"

# Activate Python 3.11 virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations to latest head
alembic upgrade head
```

### 2. Configure Local AI Runtimes
- **LM Studio:** Start server on `http://localhost:1234` with `oreal-deepseek-r1-distill-qwen-7b`.
- **Ollama:** Ensure service is running on `http://localhost:11434` with `llama3.2`.

### 3. Launch Backend
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Probe:** [http://localhost:8000/health/live](http://localhost:8000/health/live)
- **Readiness Probe:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- **System Inventory:** [http://localhost:8000/api/v1/system/status](http://localhost:8000/api/v1/system/status)

---

## 🐳 Docker Deployment

AdeptLearn includes container definitions configured with PostgreSQL and host networking bridges for local GPU models:

```bash
# Build and run backend + PostgreSQL
docker compose up -d --build

# Run migrations in container
docker compose exec backend alembic upgrade head
```

---

## 🧪 Comprehensive Automated Testing

The repository contains an exhaustive test suite verifying every component without test data fabrication:

```powershell
# 1. Run all regression, unit, and integration tests (199 passing tests)
.venv\Scripts\python -m pytest --ignore=tests/test_ai_hardware_integration.py -v

# 2. Run End-to-End Student Lifecycle Suite (8 Scenarios)
.venv\Scripts\python -m pytest tests/test_e2e_student_lifecycle.py -v

# 3. Run Teacher Classes & Analytics Tests
.venv\Scripts\python -m pytest tests/test_teacher_classes.py tests/test_teacher_analytics.py -v

# 4. Run Live RTX 4050 GPU Hardware Benchmark (Requires live LM Studio & Ollama)
.venv\Scripts\python -m pytest tests/test_ai_hardware_integration.py -v -s
```

---

## 📚 Technical Documentation Index

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Full architectural diagrams and component ownership boundaries.
- [docs/API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md): Complete REST endpoint contract, request/response JSON schemas, and TypeScript frontend client examples.
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md): Local and production containerization deployment playbooks.
- [docs/SECURITY_GUIDE.md](docs/SECURITY_GUIDE.md): RBAC, JWT cryptography, prompt injection defenses, and GDPR data portability.
- [docs/BACKUP_AND_RECOVERY.md](docs/BACKUP_AND_RECOVERY.md): SQLite/PostgreSQL backup scripts, disaster recovery, and idempotency guarantees.
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md): Test pyramid, fixtures, and execution procedures.
- [docs/MILESTONE_6_FINAL_INTEGRATION_REPORT.md](docs/MILESTONE_6_FINAL_INTEGRATION_REPORT.md): Final verification and acceptance criteria audit.
