from typing import Literal
from app.agents.state.learning_state import AdaptiveActionType, LearningState
from app.core.config import settings


def route_after_evaluation(
    state: LearningState,
) -> Literal["request_clarification", "update_bkt_mastery"]:
    """
    Decides whether the evaluation is sufficiently certain to update learner mastery,
    or whether clarification must be requested without updating BKT.
    """
    is_uncertain = state.get("is_uncertain_evaluation", False)
    confidence = state.get("evaluation_confidence", 1.0)
    eval_result = state.get("evaluation_result", {}) or {}
    answer_type = eval_result.get("answer_type", "correct")

    if is_uncertain or confidence < settings.EVALUATION_CONFIDENCE_THRESHOLD or answer_type == "ambiguous":
        return "request_clarification"
    return "update_bkt_mastery"


def route_after_adaptive(
    state: LearningState,
) -> Literal[
    "remediation_node",
    "targeted_practice_node",
    "advance_concept_node",
    "revision_node",
    "validate_question",
]:
    """
    Routes based on the deterministic adaptive decision.
    """
    action = state.get("adaptive_action")
    if action == AdaptiveActionType.CONCEPT_REMEDIATION:
        return "remediation_node"
    elif action == AdaptiveActionType.TARGETED_PRACTICE:
        return "targeted_practice_node"
    elif action == AdaptiveActionType.ADVANCE_TO_NEXT_CONCEPT:
        return "advance_concept_node"
    elif action == AdaptiveActionType.REVISION_RECOMMENDATION:
        return "revision_node"
    return "validate_question"
