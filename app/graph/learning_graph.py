import logging
import uuid
from typing import Any, Dict, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session

from app.agents.state.learning_state import LearningState
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.service import get_gpu_execution_manager
from app.core.config import settings
from app.graph.graph_builder import build_learning_graph

logger = logging.getLogger(__name__)

# Global checkpointer instance
_default_memory_saver = MemorySaver()
_compiled_graph_singleton: Optional[CompiledStateGraph] = None


def get_compiled_graph(checkpointer: Optional[Any] = None) -> CompiledStateGraph:
    """
    Returns a compiled LangGraph instance.
    Uses memory saver checkpointer by default, or accepts a custom checkpointer (e.g. SqliteSaver).
    """
    global _compiled_graph_singleton
    if checkpointer is not None:
        builder = build_learning_graph()
        return builder.compile(checkpointer=checkpointer)

    if _compiled_graph_singleton is None:
        builder = build_learning_graph()
        _compiled_graph_singleton = builder.compile(checkpointer=_default_memory_saver)

    return _compiled_graph_singleton


async def execute_learning_turn(
    initial_state: LearningState,
    db: Session,
    execution_manager: Optional[GPUExecutionManager] = None,
    checkpointer: Optional[Any] = None,
) -> LearningState:
    """
    Coordinates and invokes the compiled LangGraph for a single learning turn.
    Ensures safe thread scoping: thread_id = session_{session_id}_student_{student_id}.
    """
    graph = get_compiled_graph(checkpointer=checkpointer)

    run_id = initial_state.get("run_id") or f"run_{uuid.uuid4().hex[:12]}"
    student_id = initial_state.get("student_id")
    session_id = initial_state.get("session_id")
    if session_id:
        thread_id = f"session_{session_id}_student_{student_id}"
    else:
        thread_id = f"turn_{run_id}_student_{student_id}"

    state_payload = dict(initial_state)
    state_payload["run_id"] = run_id
    state_payload.setdefault("node_execution_trace", [])
    state_payload.setdefault("metrics", {})
    state_payload.setdefault("execution_status", "in_progress")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "db": db,
            "execution_manager": execution_manager or get_gpu_execution_manager(),
        }
    }

    logger.info(f"Starting LangGraph learning turn [run_id={run_id}, thread_id={thread_id}]")
    result = await graph.ainvoke(state_payload, config=config)
    logger.info(f"Completed LangGraph learning turn [run_id={run_id}, status={result.get('execution_status')}]")

    return result
