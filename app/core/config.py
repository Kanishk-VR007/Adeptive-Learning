from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Adaptive Exam-Prep Tutor"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database connection string
    # SQLite default, easily swapped with PostgreSQL URL:
    # postgresql+psycopg2://user:password@localhost:5432/adaptive_learning
    DATABASE_URL: str = "sqlite:///./adaptive_learning.db"

    # JWT Authentication
    SECRET_KEY: str = "adaptive-exam-prep-tutor-super-secret-development-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Local AI Configuration - Model A (Reasoning: LM Studio)
    LMSTUDIO_BASE_URL: str = "http://localhost:1234"
    LMSTUDIO_MODEL: str = "oreal-deepseek-r1-distill-qwen-7b"
    LMSTUDIO_API_TOKEN: str = ""
    LMSTUDIO_CONTEXT_LENGTH: int = 4096
    LMSTUDIO_MAX_TOKENS: int = 2048
    LMSTUDIO_TEMPERATURE: float = 0.6
    LMSTUDIO_GPU_OFFLOAD: str = "max"

    # Local AI Configuration - Model B (Formatting: Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:latest"
    OLLAMA_CONTEXT_LENGTH: int = 4096
    OLLAMA_MAX_TOKENS: int = 2048
    OLLAMA_TEMPERATURE: float = 0.3
    OLLAMA_KEEP_ALIVE: str = "0"

    # GPU Execution & Concurrency Manager
    GPU_EXECUTION_MODE: str = "sequential"
    GPU_PREWARM_MODE: str = "disabled"
    MODEL_REQUEST_TIMEOUT: int = 120
    MODEL_LOAD_TIMEOUT: int = 180
    MODEL_UNLOAD_TIMEOUT: int = 60
    GPU_MAX_MEMORY_FRACTION: float = 0.90
    GPU_MONITORING_ENABLED: bool = True

    # Real Hardware Integration Test Flag (0 or 1 / False or True)
    RUN_LOCAL_LLM_INTEGRATION: bool = False
    RUN_AGENTIC_LOCAL_INTEGRATION: bool = False

    # Adaptive Learning Policy Thresholds
    ADAPTIVE_MASTERY_REMEDIATION_THRESHOLD: float = 0.40
    ADAPTIVE_MASTERY_PRACTICE_THRESHOLD: float = 0.70
    ADAPTIVE_MASTERY_ADVANCE_THRESHOLD: float = 0.90
    EVALUATION_CONFIDENCE_THRESHOLD: float = 0.60

    # LangGraph Checkpointing
    LANGGRAPH_CHECKPOINT_DB: str = "sqlite:///./checkpoints.db"

    # FSRS Spaced Repetition Configuration
    FSRS_DESIRED_RETENTION: float = 0.90
    FSRS_ENABLE_FUZZING: bool = True
    FSRS_MAXIMUM_INTERVAL: int = 36500
    FSRS_DEFAULT_TIMEZONE: str = "UTC"
    FSRS_DAILY_NEW_LIMIT: int = 5
    FSRS_DAILY_REVIEW_LIMIT: int = 20

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
