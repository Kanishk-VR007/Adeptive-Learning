# AdeptLearn – Testing Architecture & Execution Guide
**Milestone 6 Automated Verification Protocol**

---

## 1. Testing Philosophy & Test Pyramid

AdeptLearn mandates a strict validation discipline:
`AUDIT → DESIGN → IMPLEMENT → TEST → DEBUG → RE-TEST → VALIDATE → PROCEED`

No feature is marked complete without executed, passing automated tests. All tests use isolated test databases and mock AI runtimes to prevent test non-determinism, with dedicated hardware suites verifying live GPU execution.

```
                    /\
                   /  \   End-to-End Scenarios & Concurrency
                  / E2E\  (tests/test_e2e_student_lifecycle.py)
                 /------\
                /        \   Integration & Security Suites
               /  INTEG   \  (tests/test_learning_api.py, test_fsrs_api_security.py, ...)
              /------------\
             /     UNIT     \  Unit Tests (BKT, FSRS, Graph, RBAC, GPU Mutex)
            /----------------\ (tests/test_bkt_math.py, test_fsrs_scheduler.py, ...)
```

---

## 2. Test Execution Commands

### 2.1 Complete Automated Regression Suite (199 Tests)
Executes all unit, integration, RBAC security, transactional consistency, and end-to-end lifecycle tests with mocked AI runtimes:

```powershell
.venv\Scripts\python -m pytest --ignore=tests/test_ai_hardware_integration.py -v
```

### 2.2 End-to-End Student Lifecycle Suite (8 Scenarios)
Tests the complete journey from student registration through diagnostic assessment, adaptive learning, misconception remediation, FSRS spaced repetition, and 10-student concurrency:

```powershell
.venv\Scripts\python -m pytest tests/test_e2e_student_lifecycle.py -v
```

### 2.3 Teacher Management & Analytics Suite
Verifies class creation, student enrollment by code, roster access, and deterministic aggregation calculations:

```powershell
.venv\Scripts\python -m pytest tests/test_teacher_classes.py tests/test_teacher_analytics.py -v
```

### 2.4 System Health & Readiness Suite
Verifies container liveness, database readiness, and operational status probes:

```powershell
.venv\Scripts\python -m pytest tests/test_system_health.py -v
```

### 2.5 Real Hardware RTX 4050 Integration Suite
*Requires live LM Studio on port 1234 and Ollama on port 11434 with RTX 4050 GPU:*

```powershell
.venv\Scripts\python -m pytest tests/test_ai_hardware_integration.py -v -s
```
*Note: Real hardware tests verify VRAM limits, model load times, inference latency, and clean memory deallocation under actual physical conditions.*

---

## 3. Test Database Isolation

- **In-Memory SQLite:** Standard unit and integration tests use `sqlite:///:memory:` with `StaticPool` and `foreign_keys=ON`, recreated fresh for every test function.
- **File-Backed SQLite (WAL Mode):** Concurrency tests (`test_fsrs_concurrency.py`) instantiate temporary `.db` files with Write-Ahead Logging and 30s timeouts to ensure multi-threaded transaction isolation.
- **PostgreSQL CI:** GitHub Actions workflows run against a live PostgreSQL 16 container service.
