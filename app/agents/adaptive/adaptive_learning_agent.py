import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.agents.state.learning_state import AdaptiveActionType, LearningState
from app.core.config import settings
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery

logger = logging.getLogger(__name__)


class AdaptiveLearningAgent:
    """
    Agent 6: Adaptive Learning Agent (Pure Python).
    Inspects updated BKT mastery, prerequisite reachability, and diagnosed misconceptions
    to make a deterministic pedagogical next-action decision.
    """

    @classmethod
    async def run(cls, state: LearningState, db: Session) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("adaptive_decision")

        # 1. If evaluation was uncertain, request clarification
        if state.get("is_uncertain_evaluation", False):
            return {
                "adaptive_action": AdaptiveActionType.CLARIFICATION_REQUIRED,
                "adaptive_reasoning": "Student response was ambiguous or confidence fell below threshold. Clarification requested.",
                "node_execution_trace": trace,
            }

        student_id = state.get("student_id")
        current_concept_id = state.get("current_concept_id") or state.get("concept_id")
        candidate_concept_id = state.get("candidate_next_concept_id")
        mastery = state.get("updated_mastery", state.get("current_mastery", 0.20))
        if mastery is None:
            mastery = 0.20

        misc_analysis = state.get("misconception_analysis", {}) or {}
        has_misconception = misc_analysis.get("detected", False)
        misc_category = misc_analysis.get("category", "none")

        # Thresholds from config
        remediation_threshold = settings.ADAPTIVE_MASTERY_REMEDIATION_THRESHOLD  # 0.40
        practice_threshold = settings.ADAPTIVE_MASTERY_PRACTICE_THRESHOLD        # 0.70
        advance_threshold = settings.ADAPTIVE_MASTERY_ADVANCE_THRESHOLD          # 0.90

        # Check prerequisite health of current concept
        prereqs = db.query(ConceptPrerequisite.prerequisite_id).filter(
            ConceptPrerequisite.concept_id == current_concept_id
        ).all()
        prereq_ids = [p[0] for p in prereqs]

        unmastered_prereq_found = False
        weak_prereq_id = None
        if prereq_ids and student_id:
            prereq_records = db.query(LearnerMastery).filter(
                LearnerMastery.student_id == student_id,
                LearnerMastery.concept_id.in_(prereq_ids)
            ).all()
            pm_dict = {r.concept_id: r.current_mastery for r in prereq_records}
            for pid in prereq_ids:
                if pm_dict.get(pid, 0.20) < practice_threshold:
                    unmastered_prereq_found = True
                    weak_prereq_id = pid
                    break

        # Decision Policy:
        # Case A: Low mastery (< 0.40) or severe misconception -> CONCEPT_REMEDIATION
        if mastery < remediation_threshold or (has_misconception and misc_category in ("conceptual_misconception", "incorrect_prerequisite_knowledge")):
            action = AdaptiveActionType.CONCEPT_REMEDIATION
            if unmastered_prereq_found and weak_prereq_id:
                reasoning = (
                    f"Mastery ({mastery:.2f}) is below {remediation_threshold:.2f} and prerequisite "
                    f"concept #{weak_prereq_id} is incomplete. Routing to prerequisite remediation."
                )
                chosen_concept_id = weak_prereq_id
            else:
                reasoning = (
                    f"Mastery ({mastery:.2f}) indicates fundamental misconceptions ({misc_category}). "
                    f"Recommending foundational remediation on current concept."
                )
                chosen_concept_id = current_concept_id

        # Case B: Developing mastery (0.40 <= mastery < 0.70) -> TARGETED_PRACTICE
        elif remediation_threshold <= mastery < practice_threshold:
            action = AdaptiveActionType.TARGETED_PRACTICE
            reasoning = (
                f"Mastery ({mastery:.2f}) is in the developing range [{remediation_threshold:.2f}, {practice_threshold:.2f}). "
                f"Recommending targeted practice on current concept."
            )
            chosen_concept_id = current_concept_id

        # Case C: Good mastery (0.70 <= mastery < 0.90) -> Consolidation or Advancing practice
        elif practice_threshold <= mastery < advance_threshold:
            if candidate_concept_id and candidate_concept_id != current_concept_id and not unmastered_prereq_found:
                action = AdaptiveActionType.ADVANCE_TO_NEXT_CONCEPT
                reasoning = (
                    f"Mastery ({mastery:.2f}) exceeds practice threshold ({practice_threshold:.2f}). "
                    f"Candidate concept #{candidate_concept_id} is eligible for progression."
                )
                chosen_concept_id = candidate_concept_id
            else:
                action = AdaptiveActionType.TARGETED_PRACTICE
                reasoning = (
                    f"Mastery ({mastery:.2f}) is good. Consolidation practice on advanced applications recommended."
                )
                chosen_concept_id = current_concept_id

        # Case D: Mastered (mastery >= 0.90)
        else:
            if candidate_concept_id and candidate_concept_id != current_concept_id:
                action = AdaptiveActionType.ADVANCE_TO_NEXT_CONCEPT
                reasoning = (
                    f"Mastery ({mastery:.2f}) achieves full mastery (>= {advance_threshold:.2f}). "
                    f"Advancing student to next concept #{candidate_concept_id}."
                )
                chosen_concept_id = candidate_concept_id
            else:
                action = AdaptiveActionType.REVISION_RECOMMENDATION
                reasoning = (
                    f"Mastery ({mastery:.2f}) achieves mastery threshold with no remaining forward prerequisites. "
                    f"Recommending spaced revision."
                )
                chosen_concept_id = current_concept_id

        logger.info(f"Adaptive Decision: {action} (Target Concept: {chosen_concept_id}) - {reasoning}")

        return {
            "adaptive_action": action,
            "adaptive_reasoning": reasoning,
            "candidate_next_concept_id": chosen_concept_id,
            "node_execution_trace": trace,
        }
