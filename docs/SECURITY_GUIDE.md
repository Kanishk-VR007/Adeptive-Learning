# AdeptLearn – Security & Privacy Architecture Guide
**Milestone 6 Security Hardening & Compliance**

---

## 1. Authentication & Session Security

### 1.1 Password Cryptography
- Passwords are encrypted using **bcrypt** via Python `passlib.context.CryptContext(schemes=["bcrypt"])`.
- Plaintext passwords are never logged, persisted, or cached in memory.
- Passwords must meet complexity requirements (minimum 8 characters, letters and numbers).

### 1.2 JWT Token Architecture
- Tokens are digitally signed using **HMAC-SHA256 (HS256)** using an environment-injected `SECRET_KEY`.
- Tokens contain:
  - `sub`: Internal user ID string.
  - `role`: Role enum value (`STUDENT` or `TEACHER`).
  - `exp`: Explicit expiration timestamp (default 1,440 minutes / 24 hours).
- Signature validation is strictly enforced on every protected request. Tampered tokens return `401 Unauthorized`.

---

## 2. Role-Based Access Control (RBAC) & Tenant Isolation

AdeptLearn enforces zero-trust object access control across all domains:

### 2.1 Role Guards
Endpoints utilize FastAPI dependency injection with `require_role(...)`:
- **Student-only:** `/api/v1/diagnostic/*`, `/api/v1/learning/*`, `/api/v1/revisions/*`, `/api/v1/teachers/join`.
- **Teacher-only:** `/api/v1/teachers/classes*`, `/api/v1/analytics/classes/*`.

### 2.2 Insecure Direct Object Reference (IDOR) Mitigation
- **Class Ownership:** Teachers can only inspect rosters, student records, and analytics for classes where `class.teacher_id == current_user.id`. Accessing another teacher's class returns `403 Forbidden` or `404 Not Found`.
- **Student Data Privacy:** Students can only view their own learning sessions, turn execution traces, FSRS review states, and revision histories (`resource.student_id == current_user.id`). Cross-student inspection returns `403 Forbidden`.

---

## 3. Local LLM Security & Prompt Injection Defense

Model outputs and student answers are classified as untrusted input:

```
[Untrusted Student Input]
          |
          v
[Pydantic Sanitization & Schema Validation]
          |
          v
[System-Prompt Policy Fence] (DeepSeek-R1 / Llama 3.2)
          |
          v
[Structured JSON Extraction with Fallbacks]
          |
          v
[Pydantic Output Validation] (DeepSeekAnalysisOutput)
          |
          v
[Deterministic Python Business Logic (BKT & FSRS)]
```

### 3.1 Policy Invariants:
1. **Zero Direct Database Access:** Neither DeepSeek nor Llama has access to SQL engines, database connections, or ORM sessions.
2. **Deterministic Mathematical Authority:** LLMs are never permitted to calculate BKT probability transitions or FSRS review intervals. Python computes all posterior equations and intervals deterministically.
3. **No Code Execution:** Model outputs are treated as textual feedback only. Execution of generated code or shell commands is impossible by design.
4. **Prompt Injection Containment:** Prompt templates encapsulate student answers inside delineated delimiters. System instructions specify that student inputs cannot alter grading criteria, role definitions, or system outputs.

---

## 4. Privacy, GDPR Portability & Account Deletion

### 4.1 Right to Data Portability (GDPR Article 20)
Students can download their complete educational record via `GET /api/v1/users/me/export`. The exported JSON bundle includes:
- User profile data (ID, name, email, account creation date).
- Persisted BKT mastery states across all syllabus concepts.
- Complete FSRS memory card intervals (stability, difficulty, due dates).
- Immutable historical audit logs of learning events.

### 4.2 Right to Erasure / Account Deletion (GDPR Article 17)
Users can request permanent deactivation and deletion via `DELETE /api/v1/users/me` with password re-verification:
- Cascading foreign key constraints (`ondelete="CASCADE"`) remove all linked mastery records, active review states, learning session checkpoints, and class enrollments.
- Alternatively, soft deactivation (`permanent: false`) disables login (`is_active=False`) while maintaining historical class aggregation integrity.
