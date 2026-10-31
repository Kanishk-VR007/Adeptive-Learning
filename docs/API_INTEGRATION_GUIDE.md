# AdeptLearn – API Integration Guide
**Version:** 1.0.0 (Milestone 6 Production Release)  
**Base URL:** `http://localhost:8000/api/v1` (API Endpoints)  
**Health Check URL:** `http://localhost:8000/health`  

---

## 1. Overview & Architecture Boundary

AdeptLearn provides a strictly decoupled REST API backend. The system coordinates:
- **Bayesian Knowledge Tracing (BKT)**: Probabilistic real-time learner knowledge modeling.
- **Free Spaced Repetition Scheduler (FSRS)**: Memory consolidation & optimal review interval scheduling.
- **LangGraph Agentic Orchestration**: Evaluates multi-turn reasoning and misconceptions through DeepSeek-R1 and generates socratic feedback through Llama 3.2.
- **Deterministic Analytics**: Aggregated class metrics without synthetic data fabrication.

The React frontend does not interact with AI runtimes or database drivers directly; all interactions flow through the versioned API endpoints documented below.

---

## 2. Authentication & Authorization

### 2.1 Token Format & Headers
All protected routes require an HTTP `Authorization` header containing an issued JSON Web Token (JWT):
```http
Authorization: Bearer <your_jwt_access_token>
```

### 2.2 Endpoints

#### Register New User
- **Method:** `POST /api/v1/auth/register`
- **Access:** Public
- **Request Body:**
```json
{
  "email": "student@adeptlearn.org",
  "password": "SecurePassword123!",
  "full_name": "Marie Curie",
  "role": "STUDENT"
}
```
*Note: `role` must be either `"STUDENT"` or `"TEACHER"`.*
- **Response:** `201 Created`
```json
{
  "id": 1,
  "email": "student@adeptlearn.org",
  "full_name": "Marie Curie",
  "role": "STUDENT",
  "is_active": true,
  "created_at": "2026-10-31T20:00:00Z"
}
```

#### Login (OAuth2 Form & JSON)
- **Method:** `POST /api/v1/auth/login` (Standard form) or `POST /api/v1/auth/login/json`
- **Request Body (JSON):**
```json
{
  "email": "student@adeptlearn.org",
  "password": "SecurePassword123!"
}
```
- **Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "student@adeptlearn.org",
    "full_name": "Marie Curie",
    "role": "STUDENT"
  }
}
```

---

## 3. Syllabus & Concept Hierarchy

### 3.1 List Subjects
- **Method:** `GET /api/v1/subjects`
- **Access:** Authenticated
- **Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "General Physics",
    "code": "PHYS-101",
    "description": "Foundational classical physics",
    "created_at": "2026-10-31T20:00:00Z"
  }
]
```

### 3.2 Get Concept Tree & Prerequisites
- **Method:** `GET /api/v1/concepts/tree?subject_id=1`
- **Access:** Authenticated
- **Response:** `200 OK` (Hierarchical DAG nodes with prerequisite IDs).

---

## 4. Student Learning Lifecycle

### 4.1 Diagnostic Assessment

#### Start Diagnostic
- **Method:** `POST /api/v1/diagnostic/start`
- **Access:** Student Only
- **Request Body:**
```json
{
  "subject_id": 1
}
```
- **Response:** `201 Created`
```json
{
  "session_id": 14,
  "subject_id": 1,
  "subject_name": "General Physics",
  "total_questions": 3,
  "questions": [
    {
      "question_id": 101,
      "concept_id": 12,
      "concept_name": "Vectors and Scalars",
      "concept_code": "PHYS-VEC-01",
      "question_text": "What characterizes a vector quantity in contrast to a scalar?",
      "options": ["Direction and magnitude", "Magnitude only", "Mass only"],
      "difficulty_level": "BEGINNER"
    }
  ]
}
```

#### Submit Diagnostic
- **Method:** `POST /api/v1/diagnostic/submit`
- **Access:** Student Only
- **Request Body:**
```json
{
  "session_id": 14,
  "answers": [
    {
      "question_id": 101,
      "student_answer": "Direction and magnitude"
    }
  ]
}
```
- **Response:** `200 OK`
```json
{
  "session_id": 14,
  "total_questions": 1,
  "correct_count": 1,
  "score_percentage": 100.0,
  "initialized_masteries": {
    "Vectors and Scalars": 0.55
  },
  "prerequisite_gaps": [],
  "recommended_concept_id": 13,
  "recommended_concept_name": "1D Kinematics",
  "diagnostic_summary": "Diagnostic completed. 1/1 correct (100.0%). Next recommended concept: '1D Kinematics'."
}
```

---

### 4.2 Adaptive Learning Practice Turns

#### Submit Learning Turn
- **Method:** `POST /api/v1/learning/turns`
- **Access:** Student Only
- **Request Body:**
```json
{
  "question_id": 101,
  "student_answer": "Direct molecular contact causes conduction.",
  "session_id": 14
}
```
- **Response:** `200 OK`
```json
{
  "run_id": "run_982bf731-92b1-4c59-bf72-872f0ec387bf",
  "student_id": 1,
  "execution_status": "completed",
  "updated_mastery": 0.68,
  "node_execution_trace": ["validate_submission", "deepseek_evaluation", "bkt_state_update", "student_feedback"]
}
```

#### Retrieve Turn Feedback & Result
- **Method:** `GET /api/v1/learning/turns/{run_id}/result`
- **Access:** Student Only (enforces student ownership)
- **Response:** `200 OK`
```json
{
  "run_id": "run_982bf731-92b1-4c59-bf72-872f0ec387bf",
  "student_feedback": {
    "feedback": "Excellent reasoning! You correctly identified conduction as direct kinetic transfer.",
    "socratic_hint": null,
    "next_question": "How does thermal conductivity affect heat transfer rate in metals?",
    "adaptive_action": "ADVANCE_CONCEPT",
    "display_mastery": 0.68
  }
}
```

---

### 4.3 Spaced Repetition (FSRS) Revision

#### Revision Summary
- **Method:** `GET /api/v1/revisions/summary`
- **Access:** Student Only
- **Response:** `200 OK`
```json
{
  "due_today_count": 2,
  "overdue_count": 0,
  "upcoming_count": 5,
  "new_count": 1,
  "total_reviewed_count": 3,
  "student_timezone": "UTC"
}
```

#### Revision Queue
- **Method:** `GET /api/v1/revisions/queue?limit=20`
- **Access:** Student Only
- **Response:** `200 OK`
```json
{
  "total_count": 2,
  "timezone": "UTC",
  "items": [
    {
      "concept_id": 12,
      "concept_name": "Vectors and Scalars",
      "subject_id": 1,
      "subject_name": "General Physics",
      "chapter_id": 1,
      "chapter_title": "Mechanics",
      "due_at_utc": "2026-10-31T18:00:00Z",
      "status": "DUE_TODAY",
      "current_bkt_mastery": 0.75,
      "stability": 3.4,
      "difficulty": 4.1,
      "priority_score": 85.2,
      "recommended_action": "Scheduled revision due today for optimal memory consolidation."
    }
  ]
}
```

#### Start Revision
- **Method:** `POST /api/v1/revisions/{concept_id}/start`
- **Access:** Student Only
- **Response:** `200 OK` (Serves revision retrieval question).

#### Complete Revision & Recall Rating
- **Method:** `POST /api/v1/revisions/{concept_id}/complete`
- **Access:** Student Only
- **Request Body:**
```json
{
  "question_id": 101,
  "response_text": "Direction and magnitude",
  "rating": 3
}
```
*Rating Scale: `1: AGAIN` (Failed recall), `2: HARD`, `3: GOOD` (Correct recall), `4: EASY`.*
- **Response:** `200 OK`
```json
{
  "idempotency_key": "fsrs_rev_4a31980f...",
  "concept_id": 12,
  "concept_name": "Vectors and Scalars",
  "rating": 3,
  "rating_name": "Good",
  "answer_correctness": true,
  "rating_valid": true,
  "updated_stability": 8.7,
  "updated_difficulty": 3.9,
  "next_due_at_utc": "2026-11-08T18:00:00Z",
  "updated_bkt_mastery": 0.81
}
```

---

## 5. Teacher Class & Analytics Management

### 5.1 Create Class
- **Method:** `POST /api/v1/teachers/classes`
- **Access:** Teacher Only
- **Request Body:**
```json
{
  "name": "Physics Period 3",
  "subject_id": 1,
  "description": "Fall 2026 AP Physics"
}
```
- **Response:** `201 Created`
```json
{
  "id": 5,
  "name": "Physics Period 3",
  "enrollment_code": "PHYS3A91",
  "teacher_id": 2,
  "subject_id": 1,
  "is_active": true
}
```

### 5.2 Student Join via Code
- **Method:** `POST /api/v1/teachers/join`
- **Access:** Student Only
- **Request Body:**
```json
{
  "enrollment_code": "PHYS3A91"
}
```
- **Response:** `200 OK`

### 5.3 Class Analytics Report
- **Method:** `GET /api/v1/analytics/classes/{class_id}` (or `/classes/{class_id}/summary`)
- **Access:** Teacher Only (verified owner)
- **Response:** `200 OK`
```json
{
  "class_id": 5,
  "class_name": "Physics Period 3",
  "subject_id": 1,
  "subject_name": "General Physics",
  "total_enrolled": 24,
  "active_students_count": 22,
  "participation_rate": 91.67,
  "average_mastery": 0.78,
  "weak_concepts": [
    {
      "concept_id": 15,
      "concept_name": "Projectile Motion",
      "concept_code": "PHYS-PROJ-01",
      "average_mastery": 0.42,
      "students_remediating": 14,
      "error_rate": 58.33
    }
  ],
  "common_misconceptions": [
    {
      "category": "INVERSE_PROPORTIONALITY_CONFUSION",
      "description": "Students assume gravity affects horizontal velocity component.",
      "occurrence_count": 18,
      "concept_names": ["Projectile Motion"]
    }
  ]
}
```

---

## 6. User Profile, GDPR Portability & Account Deletion

### 6.1 View Profile
- **Method:** `GET /api/v1/users/me`
- **Access:** Authenticated

### 6.2 Update Profile
- **Method:** `PATCH /api/v1/users/me`
- **Request Body:** `{"full_name": "New Full Name"}`

### 6.3 Change Password
- **Method:** `POST /api/v1/users/me/change-password`
- **Request Body:** `{"current_password": "OldPassword123", "new_password": "NewSecretPassword456"}`

### 6.4 Export Learning Data (GDPR Compliance)
- **Method:** `GET /api/v1/users/me/export`
- **Access:** Authenticated
- **Response:** `200 OK` containing all personal mastery probabilities, revision cards, and audit logs.

### 6.5 Account Deletion
- **Method:** `DELETE /api/v1/users/me`
- **Request Body:** `{"password": "CurrentPassword123", "permanent": true}`
- **Response:** `200 OK` (Cascades and deletes or anonymizes records).

---

## 7. System Health & Readiness Probes

| Endpoint | Method | Expected Status | Description |
|---|---|---|---|
| `/health/live` | `GET` | `200 OK` | Fast Kubernetes/container liveness probe verifying process is active. |
| `/health/ready` | `GET` | `200 OK` | Readiness check verifying PostgreSQL/SQLite connectivity. |
| `/api/v1/system/status` | `GET` | `200 OK` | Detailed operational inventory: DB, LM Studio, Ollama, GPU memory. |

---

## 8. TypeScript Frontend Client Example

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Example: Complete an adaptive turn
export async function submitLearningTurn(questionId: number, answerText: string, sessionId: number) {
  const turnResp = await api.post('/learning/turns', {
    question_id: questionId,
    student_answer: answerText,
    session_id: sessionId,
  });
  
  const { run_id } = turnResp.data;
  
  // Fetch generated feedback
  const feedbackResp = await api.get(`/learning/turns/${run_id}/result`);
  return feedbackResp.data.student_feedback;
}
```
