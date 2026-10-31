import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.agents.state.learning_state import LearningState
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Concept

logger = logging.getLogger(__name__)


class ConceptSelectionAgent:
    """
    Agent 2: Concept Selection Agent (Pure Python).
    Deterministically evaluates prerequisite knowledge, mastery states, and graph reachability
    to propose a candidate concept for the subsequent learning step BEFORE LLM inference.
    NEVER uses an LLM for graph traversal.
    """

    @classmethod
    async def run(cls, state: LearningState, db: Session) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("select_candidate_concept")

        student_id = state.get("student_id")
        current_concept_id = state.get("current_concept_id")

        if not current_concept_id:
            return {
                "execution_status": "error",
                "error_code": "NO_CURRENT_CONCEPT",
                "error_message": "Cannot select candidate concept without a valid current_concept_id.",
                "node_execution_trace": trace,
            }

        try:
            curr_concept = db.query(Concept).filter(Concept.id == current_concept_id).first()
            if not curr_concept:
                return {
                    "execution_status": "error",
                    "error_code": "CONCEPT_NOT_FOUND",
                    "error_message": f"Concept {current_concept_id} not found.",
                    "node_execution_trace": trace,
                }

            # 1. Inspect direct prerequisites of current concept
            prereq_edges = db.query(ConceptPrerequisite.prerequisite_id).filter(
                ConceptPrerequisite.concept_id == current_concept_id
            ).all()
            prereq_ids = [p_id for (p_id,) in prereq_edges]

            weak_prereq_id: Optional[int] = None
            if prereq_ids:
                prereq_masteries = db.query(LearnerMastery).filter(
                    LearnerMastery.student_id == student_id,
                    LearnerMastery.concept_id.in_(prereq_ids)
                ).all()
                mastery_by_cid = {m.concept_id: m.current_mastery for m in prereq_masteries}
                
                # Check for any prerequisite with mastery below 0.70
                for pid in prereq_ids:
                    p_mastery = mastery_by_cid.get(pid, 0.20)
                    if p_mastery < 0.70:
                        weak_prereq_id = pid
                        break

            # 2. Inspect dependent concepts (concepts that have current_concept_id as prerequisite)
            dep_edges = db.query(ConceptPrerequisite.concept_id).filter(
                ConceptPrerequisite.prerequisite_id == current_concept_id
            ).all()
            candidate_dependent_ids = [c_id for (c_id,) in dep_edges]

            eligible_next_id: Optional[int] = None
            for dep_id in candidate_dependent_ids:
                # Check if ALL prerequisites of this dependent concept are mastered >= 0.70
                dep_prereqs = db.query(ConceptPrerequisite.prerequisite_id).filter(
                    ConceptPrerequisite.concept_id == dep_id
                ).all()
                all_prereq_ids = [p[0] for p in dep_prereqs]
                
                if all_prereq_ids:
                    pm_records = db.query(LearnerMastery).filter(
                        LearnerMastery.student_id == student_id,
                        LearnerMastery.concept_id.in_(all_prereq_ids)
                    ).all()
                    pm_dict = {m.concept_id: m.current_mastery for m in pm_records}
                    all_satisfied = all(pm_dict.get(pid, 0.20) >= 0.70 for pid in all_prereq_ids)
                    if all_satisfied:
                        eligible_next_id = dep_id
                        break
                else:
                    eligible_next_id = dep_id
                    break

            # 3. Decision policy for candidate concept:
            # - If weak prerequisite exists: select weak prerequisite as candidate (for potential remediation)
            # - Else if eligible dependent concept exists and current mastery is strong (>= 0.70): select dependent
            # - Otherwise: remain on current concept for targeted practice or consolidation
            current_mastery = state.get("current_mastery")
            if current_mastery is None:
                curr_m = db.query(LearnerMastery).filter(
                    LearnerMastery.student_id == student_id,
                    LearnerMastery.concept_id == current_concept_id
                ).first()
                current_mastery = curr_m.current_mastery if curr_m else 0.20

            if weak_prereq_id is not None and current_mastery < 0.50:
                selected_candidate_id = weak_prereq_id
            elif eligible_next_id is not None and current_mastery >= 0.70:
                selected_candidate_id = eligible_next_id
            else:
                selected_candidate_id = current_concept_id

            candidate_concept = db.query(Concept).filter(Concept.id == selected_candidate_id).first()
            candidate_name = candidate_concept.name if candidate_concept else curr_concept.name

            return {
                "candidate_next_concept_id": selected_candidate_id,
                "candidate_next_concept_name": candidate_name,
                "node_execution_trace": trace,
            }

        except Exception as e:
            logger.error(f"Error selecting candidate concept: {e}", exc_info=True)
            return {
                "execution_status": "error",
                "error_code": "CONCEPT_SELECTION_ERROR",
                "error_message": f"Error selecting concept: {str(e)}",
                "node_execution_trace": trace,
            }
