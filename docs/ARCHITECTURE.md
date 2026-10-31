# AdeptLearn – System Architecture & Service Boundaries
**Milestone 6 Final Production Architecture**

---

## 1. Architectural Philosophy & Ownership Boundaries

AdeptLearn is designed as a unified agentic AI adaptive tutoring system. It enforces strict separation of responsibilities to guarantee deterministic pedagogical guarantees, numerical reproducibility, data integrity, and safe local AI inference on constrained consumer hardware (NVIDIA RTX 4050 6GB VRAM).

```
+-----------------------------------------------------------------------------------+
|                                 FASTAPI API LAYER                                 |
|  - Request Validation (Pydantic v2)        - JWT Auth & Role-Based RBAC           |
|  - Rate Limiting & CORS Filtering          - Response DTO Serialization           |
+-----------------------------------------------------------------------------------+
        |                          |                          |
        v                          v                          v
+------------------+     +--------------------+     +-------------------------------+
|  STUDENT LIFECYCLE|     |  TEACHER & CLASSES |     |  SYSTEM OBSERVABILITY         |
|  - /diagnostic   |     |  - /teachers       |     |  - /health/live, /ready       |
|  - /learning     |     |  - /analytics      |     |  - /api/v1/system/status      |
|  - /revisions    |     |  - /users          |     |  - Structured Logging         |
+------------------+     +--------------------+     +-------------------------------+
        |                          |                          |
        +--------------------------+--------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------------------+
|                        LANGGRAPH AGENTIC ORCHESTRATION                            |
|  1. Validate Submission Node                                                      |
|  2. DeepSeek Evaluator Node (Reasoning & Misconceptions)                          |
|  3. BKT Mastery Transition Node (Deterministic Python)                            |
|  4. Llama Pedagogical Feedback Node (Socratic Hints & Encouragement)              |
|  5. Checkpoint & Memory Saver Recovery                                            |
+-----------------------------------------------------------------------------------+
             |                                             |
             v                                             v
+-----------------------------+               +-------------------------------------+
|   GPU EXECUTION MANAGER     |               |   DETERMINISTIC PYTHON ENGINES      |
|  - Mutex Inference Queue    |               |  - Bayesian Knowledge Tracing (BKT) |
|  - Exclusive Residency      |               |  - Free Spaced Repetition (FSRS)    |
|  - Model Swapping & Unload  |               |  - Concept Prerequisite DAG (DFS)   |
|  - RTX 4050 VRAM Guard      |               |  - Teacher Class Analytics Aggregations|
+-----------------------------+               +-------------------------------------+
        |             |                                    |
        v             v                                    v
+---------------+ +---------------+           +-------------------------------------+
| LM STUDIO     | | OLLAMA        |           | DATABASE PERSISTENCE LAYER          |
| DeepSeek-R1-  | | Llama 3.2     |           | - SQLite (Dev) / PostgreSQL (Prod)  |
| Distill-7B    | | (3B Parameters|           | - SQLAlchemy 2.0 ORM                |
| (Port 1234)   | | (Port 11434)  |           | - Alembic Versioned Migrations      |
+---------------+ +---------------+           +-------------------------------------+
```

---

## 2. Component Responsibilities & Invariants

| Component | Strict Responsibility | Prohibited Actions |
|---|---|---|
| **FastAPI** | REST HTTP endpoints, JWT validation, schema validation, HTTP error codes. | Does NOT execute model inference or write raw mathematical equations. |
| **LangGraph** | Multi-node turn workflow execution, conditional branching, recovery checkpoints. | Does NOT access raw database connections directly without service wrappers. |
| **DeepSeek-R1-Distill-7B** | Complex answer reasoning, multi-step error deduction, misconception diagnosis. | Never updates BKT probabilities or revision intervals directly. |
| **Llama 3.2** | Student-facing feedback generation, Socratic questioning, conversational hints. | Never makes mastery determinations or evaluates mathematical correctness. |
| **Python Core Engines** | Bayesian Knowledge Tracing (BKT), FSRS scheduling intervals, DAG topological sort. | Zero LLM prompt-based hallucinated numbers. Pure deterministic mathematics. |
| **GPUExecutionManager**| Centralized FIFO serialized inference lock, model loading/unloading, VRAM limit guards. | Disallows concurrent GPU residency of DeepSeek and Llama on 6GB VRAM. |
| **Database (SQLAlchemy)**| ACID storage of users, syllabus graph, mastery states, revision intervals, audit logs. | Untrusted LLMs cannot execute raw SQL or mutate database schema. |

---

## 3. The 13-Stage Student Learning Lifecycle

```
[1. Student Registration & Auth]
              |
              v
[2. Syllabus Selection & DAG Inspection]
              |
              v
[3. Diagnostic Assessment] -------------> Initializes Empirical BKT Prior P(L0)
              |
              v
[4. Topological DAG Path Recommendation]
              |
              v
[5. Adaptive Question Generation / Retrieval]
              |
              v
[6. Student Submits Free-form / MCQ Answer]
              |
              v
[7. DeepSeek-R1 Analyzes Reasoning & Misconceptions] (LM Studio)
              |
              v
[8. Deterministic BKT Knowledge State Update] (Python)
              |
              v
[9. Adaptive Action Decision (Advance / Remediate / Socratic)]
              |
              v
[10. Llama 3.2 Formulates Socratic Feedback] (Ollama)
              |
              v
[11. FSRS Spaced Repetition Enrollment & Interval Scheduling]
              |
              v
[12. Immutable Historical Audit & Checkpoint Persistence]
              |
              v
[13. Deterministic Teacher Class Aggregations & Analytics]
```

---

## 4. GPU Exclusivity & Inference Serialization on RTX 4050

The NVIDIA GeForce RTX 4050 Laptop GPU contains **6,141 MB of physical VRAM**.
- **DeepSeek-R1-Distill-Qwen-7B (Q4_K_M)** occupies ~4,456 MB VRAM.
- **Llama 3.2 (3B)** occupies ~2,100 MB VRAM.
- Simultaneous residency of both models consumes 6,556 MB, causing immediate `CUDA Out of Memory (OOM)`.

### Centralized Execution Protocol:
1. `GPUExecutionManager` acquires an `asyncio.Lock` for every learning turn request.
2. If DeepSeek is loaded, it is executed; once inference finishes, `LMStudioProvider.unload_model()` is invoked.
3. Resilient polling checks LM Studio runtime `/api/v1/models` every 500ms until VRAM deallocation is confirmed.
4. Llama 3.2 is then loaded via Ollama runtime API, executes feedback generation, and is kept or unloaded based on memory-saving configuration.
5. All concurrent API calls queue transparently behind the lock, ensuring zero GPU collisions.
