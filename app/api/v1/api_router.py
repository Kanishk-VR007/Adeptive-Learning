from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    subjects,
    chapters,
    concepts,
    graph,
    questions,
    assessments,
    mastery,
    learners,
    ai,
    learning,
    revisions,
    teachers,
    analytics,
    diagnostic,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(subjects.router)
api_router.include_router(chapters.router)
api_router.include_router(concepts.router)
api_router.include_router(graph.router)
api_router.include_router(questions.router)
api_router.include_router(assessments.router)
api_router.include_router(mastery.router)
api_router.include_router(learners.router)
api_router.include_router(ai.router)
api_router.include_router(learning.router)
api_router.include_router(revisions.router)
api_router.include_router(teachers.router)
api_router.include_router(analytics.router)
api_router.include_router(diagnostic.router)



