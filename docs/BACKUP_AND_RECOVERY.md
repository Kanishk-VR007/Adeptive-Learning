# AdeptLearn – Backup, Consistency & Disaster Recovery Guide
**Milestone 6 Operational Continuity**

---

## 1. Database Backup Procedures

### 1.1 Development Environment (SQLite)
AdeptLearn uses SQLite in WAL (Write-Ahead Logging) mode during development.
To generate a hot, non-blocking backup:

```powershell
# In PowerShell:
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "backups\adaptive_learning_$timestamp.db"

# Create backups directory if missing
if (!(Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" }

# Safe online backup via sqlite3 command line
sqlite3 adaptive_learning.db ".backup '$backupFile'"
Write-Host "Database successfully backed up to $backupFile"
```

### 1.2 Production Environment (PostgreSQL)
For production PostgreSQL containers:

```bash
# Automated dump via pg_dump
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/adeptlearn"
mkdir -p "$BACKUP_DIR"

docker exec -t adeptlearn_postgres pg_dump -U adeptlearn -F c -b -v -f "/var/lib/postgresql/data/backup_${TIMESTAMP}.dump" adeptlearn_db

# Transfer dump out of container
docker cp adeptlearn_postgres:"/var/lib/postgresql/data/backup_${TIMESTAMP}.dump" "${BACKUP_DIR}/adeptlearn_${TIMESTAMP}.dump"
```

---

## 2. Restoration Playbook

### 2.1 SQLite Restoration
```powershell
# 1. Stop backend service
Stop-Process -Name "uvicorn" -Force

# 2. Archive corrupted database
Move-Item adaptive_learning.db "adaptive_learning.db.corrupt"

# 3. Restore clean backup
Copy-Item "backups\adaptive_learning_20261031.db" adaptive_learning.db

# 4. Restart backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2.2 PostgreSQL Restoration
```bash
# Drop existing database and recreate from clean dump
docker exec -i adeptlearn_postgres dropdb -U adeptlearn --if-exists adeptlearn_db
docker exec -i adeptlearn_postgres createdb -U adeptlearn adeptlearn_db
docker exec -i adeptlearn_postgres pg_restore -U adeptlearn -d adeptlearn_db -v "/var/lib/postgresql/data/backup_clean.dump"
```

---

## 3. Transaction Boundaries & Idempotent Failure Recovery

Multi-step learning turns and revision completions are protected by strict transaction boundaries:

### 3.1 Idempotency Key Specification
- Every BKT update creates an immutable audit row in `learning_history` with a unique `evidence_id`:
  `evidence_id = "ev_<session_id>_<student_id>_<question_id>_<timestamp>"`
- Before executing a Bayesian update, `MasteryService` checks for existing evidence. If already present, the posterior is not recalculated, preventing double-counting.
- FSRS review submissions accept an optional or auto-generated `idempotency_key` stored on `review_history`. Repeating a review request returns the previous review result with `is_idempotent_duplicate: true` without incrementing repetitions or shifting intervals.

### 3.2 Failure Scenario Recovery Playbook

#### Scenario A: DeepSeek Reasoning Succeeds, BKT Updates, but Llama Feedback Fails
1. **System State:**
   - DeepSeek evaluation and BKT mastery transitions have already been committed.
   - The LangGraph state captures `execution_status = "error"` with the completed evaluation result.
2. **Recovery Action:**
   - The student or client retries `POST /api/v1/learning/turns`.
   - The graph recognizes existing evaluation evidence for the turn, skips re-running DeepSeek and BKT, and re-executes only the failed Llama feedback stage.
   - Student receives valid feedback without inflated mastery or duplicate attempt statistics.

#### Scenario B: GPU Memory OOM or Service Crash During Inference
1. **System State:**
   - Request terminates with HTTP 503 (Inference Service Unavailable).
   - Incomplete state is dropped; no database mutation occurred.
2. **Recovery Action:**
   - Client re-submits turn safely when GPU manager re-enters `idle` state.
   - System resumes normal learning progression.
