import logging
from typing import Any, Dict, Optional
from app.agents.state.learning_state import MisconceptionItem

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "conceptual_misconception",
    "calculation_error",
    "incorrect_formula_application",
    "incomplete_understanding",
    "careless_mistake",
    "incorrect_prerequisite_knowledge",
    "unclear_response",
    "none",
}


class MisconceptionDetectionAgent:
    """
    Agent 4: Misconception Detection Agent.
    Specialized agent for classifying misconceptions and diagnosing underlying cognitive gaps.
    Can be run independently or verified post-DeepSeek inference.
    """

    @classmethod
    def classify_error(
        cls,
        is_correct: bool,
        answer_text: str,
        reasoning_text: str,
        concept_id: Optional[int] = None,
        detected_category: Optional[str] = None,
    ) -> MisconceptionItem:
        """
        Classifies misconception with robust fallback and validation.
        Does not force a misconception if the answer was correct.
        """
        if is_correct:
            return MisconceptionItem(
                detected=False,
                concept_id=concept_id,
                category="none",
                description="No misconception detected; answer is correct."
            )

        cat = (detected_category or "conceptual_misconception").lower()
        if cat not in VALID_CATEGORIES:
            cat = "conceptual_misconception"

        desc = reasoning_text or "Incorrect application of concept principles."
        return MisconceptionItem(
            detected=True,
            concept_id=concept_id,
            category=cat,
            description=desc,
        )
