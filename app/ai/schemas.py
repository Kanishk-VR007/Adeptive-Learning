from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Chat & Inference Schemas
# ============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the author: system, user, assistant")
    content: str = Field(..., description="Text content of the message")


class InferenceOptions(BaseModel):
    temperature: Optional[float] = 0.6
    max_tokens: Optional[int] = 2048
    format_json: bool = False
    stream: bool = False
    context_length: Optional[int] = 4096


class InferenceStats(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    eval_duration_ms: float = 0.0


class LLMResponse(BaseModel):
    content: str
    raw: Optional[Dict[str, Any]] = None
    stats: InferenceStats = Field(default_factory=InferenceStats)


class ModelInfo(BaseModel):
    model_id: str
    name: str
    size_bytes: Optional[int] = None
    quantization: Optional[str] = None
    is_loaded: bool = False
    runtime: str  # "lmstudio" or "ollama"


class ProviderHealth(BaseModel):
    provider: str
    is_online: bool
    base_url: str
    loaded_models: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# GPU & Execution State Schemas
# ============================================================================

class ExecutionState(str, Enum):
    IDLE = "IDLE"
    DEEPSEEK_LOADING = "DEEPSEEK_LOADING"
    DEEPSEEK_ACTIVE = "DEEPSEEK_ACTIVE"
    DEEPSEEK_UNLOADING = "DEEPSEEK_UNLOADING"
    LLAMA_LOADING = "LLAMA_LOADING"
    LLAMA_ACTIVE = "LLAMA_ACTIVE"
    LLAMA_UNLOADING = "LLAMA_UNLOADING"
    DEEPSEEK_PREWARMING = "DEEPSEEK_PREWARMING"
    ERROR = "ERROR"


class GPUMemorySnapshot(BaseModel):
    total_mb: float = 0.0
    used_mb: float = 0.0
    free_mb: float = 0.0
    utilization_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    is_available: bool = False
    timestamp: float = 0.0


class GPUExecutionStatus(BaseModel):
    state: ExecutionState
    active_model: Optional[str] = None
    queue_size: int = 0
    last_transition_time: float = 0.0
    prewarmed_model: Optional[str] = None
    mode: str = "sequential"
    prewarm_mode: str = "disabled"
    gpu_snapshot: Optional[GPUMemorySnapshot] = None


# ============================================================================
# Reasoning & Formatting Domain DTOs
# ============================================================================

class DeepSeekReasoningInput(BaseModel):
    student_answer: str
    question_text: str
    expected_answer: str
    evaluation_criteria: Optional[str] = None
    concept_name: str
    concept_description: Optional[str] = None
    prior_mastery: Optional[float] = None
    relevant_history: Optional[List[str]] = None


class DeepSeekReasoningOutput(BaseModel):
    answer_interpretation: str = Field(..., description="Summary of student's intent and logic")
    reasoning_analysis: str = Field(..., description="Deep step-by-step diagnostic reasoning")
    identified_misconception: Optional[str] = Field(None, description="Specific conceptual misunderstanding")
    conceptual_correctness: bool = Field(..., description="True if answer is conceptually sound, False otherwise")
    recommended_learning_intervention: Optional[str] = Field("Proceed to next practice problem", description="Actionable pedagogical next step")
    diagnostic_explanation: str = Field(..., description="Detailed diagnostic for student feedback")
    suggested_follow_up_question: Optional[str] = Field(None, description="Calibrated follow-up probe")


class LlamaFormatInput(BaseModel):
    reasoning: DeepSeekReasoningOutput
    student_name: Optional[str] = "Student"
    question_text: str
    concept_name: str


class LlamaFormatOutput(BaseModel):
    friendly_feedback: str = Field(..., description="Encouraging, clear feedback addressing the student directly")
    socratic_hint: Optional[str] = Field(None, description="Gentle guiding question or hint without giving away the full answer")
    formatted_next_question: Optional[str] = Field(None, description="Formatted next practice or follow-up question")
    explanation: str = Field(..., description="Clear explanation adapted to student level")
    conceptual_correctness: bool = Field(..., description="Mirrors reasoning conceptual correctness")


class ExecutionTurnMetrics(BaseModel):
    deepseek_load_ms: float = 0.0
    deepseek_inference_ms: float = 0.0
    deepseek_unload_ms: float = 0.0
    llama_load_ms: float = 0.0
    llama_inference_ms: float = 0.0
    llama_unload_ms: float = 0.0
    total_turn_ms: float = 0.0
    peak_vram_mb: float = 0.0


class LearningTurnInput(BaseModel):
    student_id: Optional[int] = None
    concept_id: Optional[int] = None
    concept_name: str
    question_id: Optional[int] = None
    question_text: str
    expected_answer: str
    student_answer: str
    evaluation_criteria: Optional[str] = None
    prior_mastery: Optional[float] = None


class LearningTurnOutput(BaseModel):
    success: bool
    reasoning: Optional[DeepSeekReasoningOutput] = None
    formatted_response: Optional[LlamaFormatOutput] = None
    metrics: ExecutionTurnMetrics = Field(default_factory=ExecutionTurnMetrics)
    error_message: Optional[str] = None
