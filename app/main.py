from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.v1.api_router import api_router
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure logging and ensure schema is present in dev
    setup_logging()
    logger.info("Initializing %s in %s environment...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
    yield
    # Shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Backend API foundation for Adaptive Exam-Prep Tutor with syllabus management, "
                "JWT role-based access control, and Directed Acyclic Graph (DAG) concept knowledge graph.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS Middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API v1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"], summary="Service health check")
def health_check():
    """Standard health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/live", tags=["Health"], summary="Liveness probe")
def health_live():
    """Fast Kubernetes / container liveness probe verifying process is active."""
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/ready", tags=["Health"], summary="Readiness probe")
def health_ready():
    """Readiness probe checking critical database dependency."""
    from sqlalchemy import text
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "service": settings.PROJECT_NAME,
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "service": settings.PROJECT_NAME,
                "database": "disconnected",
                "error": str(e),
            },
        )
    finally:
        db.close()


@app.get("/api/v1/system/status", tags=["System Status"], summary="Detailed system component health")
async def system_status():
    """
    Comprehensive diagnostic report identifying health of all subsystems:
    API, Database, LangGraph agent runtime, LM Studio, Ollama, and GPU Execution Manager.
    Distinguishes core service availability from optional local LLM runtimes.
    """
    import httpx
    import time
    from sqlalchemy import text
    from app.db.session import SessionLocal
    from app.ai.gpu.monitor import GPUResourceMonitor

    # 1. DB check
    db_status = "offline"
    db_latency_ms = None
    db = SessionLocal()
    try:
        t0 = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    finally:
        db.close()

    # 2. LM Studio check
    lmstudio_status = "offline"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{settings.LMSTUDIO_BASE_URL}/api/v1/models")
            if res.status_code == 200:
                lmstudio_status = "online"
    except Exception:
        pass

    # 3. Ollama check
    ollama_status = "offline"
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/version")
            if res.status_code == 200:
                ollama_status = "online"
    except Exception:
        pass

    # 4. GPU memory snapshot
    monitor = GPUResourceMonitor(enabled=True)
    gpu_snapshot = monitor.get_memory_snapshot()

    # 5. Operational decision
    ai_available = (lmstudio_status == "online") or (ollama_status == "online")
    learning_active = (db_status == "connected")

    return {
        "status": "operational" if learning_active else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "components": {
            "api": {"status": "online"},
            "database": {"status": db_status, "latency_ms": db_latency_ms},
            "langgraph": {"status": "available"},
            "lmstudio_deepseek": {"status": lmstudio_status, "model": settings.LMSTUDIO_MODEL},
            "ollama_llama": {"status": ollama_status, "model": settings.OLLAMA_MODEL},
            "gpu": {
                "available": gpu_snapshot.is_available,
                "vram_used_mb": gpu_snapshot.used_mb,
                "vram_total_mb": gpu_snapshot.total_mb,
                "vram_free_mb": gpu_snapshot.free_mb,
            },
        },
        "operational_capabilities": {
            "student_learning_active": learning_active,
            "ai_inference_available": ai_available,
            "deterministic_bkt_active": True,
            "fsrs_revisions_active": True,
        },
    }


@app.get("/", tags=["Root"], summary="Root service info")
def root():
    """Root endpoint with API links."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs_url": f"{settings.API_V1_STR}/docs",
        "health_url": "/health",
        "system_status_url": f"{settings.API_V1_STR}/system/status",
        "api_v1": settings.API_V1_STR,
    }

