from typing import List, Optional, Tuple, Dict, Set
from collections import deque
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.syllabus import Concept
from app.models.concept_graph import ConceptPrerequisite, RelationshipType
from app.schemas.concept_graph import (
    GraphNode,
    GraphEdge,
    SubjectGraphResponse,
    ValidatePrerequisiteResponse,
    LearningPathResponse
)
from app.schemas.syllabus import ConceptResponse


class GraphService:
    @staticmethod
    def _find_path(
        adjacency: Dict[int, List[int]],
        start_node: int,
        target_node: int
    ) -> Optional[List[int]]:
        """
        Find directed path from start_node to target_node using BFS.
        Returns list of node IDs along path if found, else None.
        """
        if start_node == target_node:
            return [start_node]

        queue = deque([[start_node]])
        visited = {start_node}

        while queue:
            current_path = queue.popleft()
            node = current_path[-1]

            for neighbor in adjacency.get(node, []):
                if neighbor == target_node:
                    return current_path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(current_path + [neighbor])
        return None

    @classmethod
    def check_cycle_if_added(
        cls,
        db: Session,
        concept_id: int,
        prerequisite_id: int
    ) -> Tuple[bool, Optional[List[int]]]:
        """
        Check if adding the edge (concept_id depends on prerequisite_id) would introduce a cycle.
        A cycle is created if and only if concept_id is already reachable from prerequisite_id
        along existing dependency edges (i.e. prerequisite_id already depends on concept_id).
        """
        if concept_id == prerequisite_id:
            return True, [concept_id, prerequisite_id]

        # Fetch all existing prerequisite edges: node -> list of prerequisites it depends on
        all_edges = db.query(ConceptPrerequisite.concept_id, ConceptPrerequisite.prerequisite_id).all()
        adjacency: Dict[int, List[int]] = {}
        for c_id, p_id in all_edges:
            adjacency.setdefault(c_id, []).append(p_id)

        # Trace if path exists from prerequisite_id to concept_id
        path = cls._find_path(adjacency, prerequisite_id, concept_id)
        if path:
            # Cycle would be: concept_id -> path (which starts at prerequisite_id and ends at concept_id)
            return True, [concept_id] + path
        return False, None

    @classmethod
    def validate_prerequisite(
        cls,
        db: Session,
        concept_id: int,
        prerequisite_id: int
    ) -> ValidatePrerequisiteResponse:
        """Pre-flight check to validate whether a prerequisite can be added without violating DAG."""
        if concept_id == prerequisite_id:
            return ValidatePrerequisiteResponse(
                is_valid=False,
                would_form_cycle=True,
                message="A concept cannot be a prerequisite of itself (self-loop).",
                cycle_path=[concept_id, prerequisite_id]
            )

        c = db.query(Concept).filter(Concept.id == concept_id).first()
        p = db.query(Concept).filter(Concept.id == prerequisite_id).first()

        if not c:
            return ValidatePrerequisiteResponse(
                is_valid=False,
                would_form_cycle=False,
                message=f"Concept ID {concept_id} not found."
            )
        if not p:
            return ValidatePrerequisiteResponse(
                is_valid=False,
                would_form_cycle=False,
                message=f"Prerequisite Concept ID {prerequisite_id} not found."
            )

        # Check existing edge
        exists = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id == concept_id,
            ConceptPrerequisite.prerequisite_id == prerequisite_id
        ).first()
        if exists:
            return ValidatePrerequisiteResponse(
                is_valid=False,
                would_form_cycle=False,
                message="Prerequisite relationship already exists."
            )

        would_cycle, cycle_path = cls.check_cycle_if_added(db, concept_id, prerequisite_id)
        if would_cycle:
            return ValidatePrerequisiteResponse(
                is_valid=False,
                would_form_cycle=True,
                message=f"Invalid dependency: adding this prerequisite creates a circular dependency cycle.",
                cycle_path=cycle_path
            )

        return ValidatePrerequisiteResponse(
            is_valid=True,
            would_form_cycle=False,
            message="Valid prerequisite relationship. Safe to add."
        )

    @classmethod
    def add_prerequisite(
        cls,
        db: Session,
        concept_id: int,
        prerequisite_id: int,
        relationship_type: RelationshipType = RelationshipType.STRICT
    ) -> ConceptPrerequisite:
        """Add a directed prerequisite relationship after strict cycle detection."""
        if concept_id == prerequisite_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A concept cannot be a prerequisite of itself."
            )

        c = db.query(Concept).filter(Concept.id == concept_id).first()
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} does not exist."
            )

        p = db.query(Concept).filter(Concept.id == prerequisite_id).first()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prerequisite Concept with ID {prerequisite_id} does not exist."
            )

        # Check existing
        existing = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id == concept_id,
            ConceptPrerequisite.prerequisite_id == prerequisite_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Prerequisite relationship already exists between concept {concept_id} and {prerequisite_id}."
            )

        # Cycle check
        would_cycle, cycle_path = cls.check_cycle_if_added(db, concept_id, prerequisite_id)
        if would_cycle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "CyclicDependencyError",
                    "message": "Cannot add prerequisite: this would create a circular dependency cycle.",
                    "cycle_path": cycle_path
                }
            )

        edge = ConceptPrerequisite(
            concept_id=concept_id,
            prerequisite_id=prerequisite_id,
            relationship_type=relationship_type
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge

    @classmethod
    def remove_prerequisite(cls, db: Session, concept_id: int, prerequisite_id: int) -> None:
        """Remove an existing prerequisite relationship."""
        edge = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id == concept_id,
            ConceptPrerequisite.prerequisite_id == prerequisite_id
        ).first()
        if not edge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prerequisite relationship between {concept_id} and {prerequisite_id} not found."
            )
        db.delete(edge)
        db.commit()

    @classmethod
    def get_subject_graph(cls, db: Session, subject_id: int) -> SubjectGraphResponse:
        """Retrieve the complete concept graph (nodes and directed edges) for a subject."""
        concepts = db.query(Concept).filter(Concept.subject_id == subject_id).all()
        concept_ids = {c.id for c in concepts}

        nodes = [GraphNode.model_validate(c) for c in concepts]

        # Retrieve all edges where either target or prerequisite is within this subject
        edges_db = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id.in_(concept_ids)
        ).all()

        edges = [
            GraphEdge(
                from_concept_id=e.prerequisite_id,
                to_concept_id=e.concept_id,
                relationship_type=e.relationship_type
            )
            for e in edges_db
        ]

        return SubjectGraphResponse(
            subject_id=subject_id,
            total_nodes=len(nodes),
            total_edges=len(edges),
            nodes=nodes,
            edges=edges
        )

    @classmethod
    def get_learning_path(cls, db: Session, target_concept_id: int) -> LearningPathResponse:
        """
        Compute the topological prerequisite learning path to master the target concept.
        Returns an ordered sequence starting from foundational concepts up to the target.
        """
        target = db.query(Concept).filter(Concept.id == target_concept_id).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {target_concept_id} not found."
            )

        # 1. Collect all reachable prerequisite concepts (backward reachability from target)
        relevant_concept_ids: Set[int] = {target_concept_id}
        queue = deque([target_concept_id])

        while queue:
            curr_id = queue.popleft()
            prereq_edges = db.query(ConceptPrerequisite.prerequisite_id).filter(
                ConceptPrerequisite.concept_id == curr_id
            ).all()

            for (p_id,) in prereq_edges:
                if p_id not in relevant_concept_ids:
                    relevant_concept_ids.add(p_id)
                    queue.append(p_id)

        # 2. Fetch all concepts in the subgraph
        concepts_by_id = {
            c.id: c
            for c in db.query(Concept).filter(Concept.id.in_(relevant_concept_ids)).all()
        }

        # 3. Induce subgraph edges
        # In learning order: prerequisite -> downstream concept
        # An in-degree counts how many prerequisites a concept still needs
        in_degree: Dict[int, int] = {cid: 0 for cid in relevant_concept_ids}
        forward_adj: Dict[int, List[int]] = {cid: [] for cid in relevant_concept_ids}

        edges = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id.in_(relevant_concept_ids),
            ConceptPrerequisite.prerequisite_id.in_(relevant_concept_ids)
        ).all()

        for e in edges:
            forward_adj[e.prerequisite_id].append(e.concept_id)
            in_degree[e.concept_id] += 1

        # 4. Kahn's Algorithm for Topological Sorting
        zero_in_degree = deque([cid for cid, deg in in_degree.items() if deg == 0])
        ordered_ids: List[int] = []

        while zero_in_degree:
            curr = zero_in_degree.popleft()
            ordered_ids.append(curr)

            for dependent in forward_adj[curr]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    zero_in_degree.append(dependent)

        # Convert ordered IDs to ConceptResponse objects
        learning_sequence = [
            ConceptResponse.model_validate(concepts_by_id[cid])
            for cid in ordered_ids
            if cid in concepts_by_id
        ]

        return LearningPathResponse(
            target_concept_id=target.id,
            target_concept_name=target.name,
            total_steps=len(learning_sequence),
            learning_sequence=learning_sequence
        )

    @classmethod
    def get_topological_sort(cls, db: Session, subject_id: int) -> List[int]:
        """Returns topological ordering of concept IDs for a subject."""
        concepts = db.query(Concept).filter(Concept.subject_id == subject_id).all()
        concept_ids = {c.id for c in concepts}
        if not concept_ids:
            return []

        in_degree: Dict[int, int] = {cid: 0 for cid in concept_ids}
        forward_adj: Dict[int, List[int]] = {cid: [] for cid in concept_ids}

        edges = db.query(ConceptPrerequisite).filter(
            ConceptPrerequisite.concept_id.in_(concept_ids),
            ConceptPrerequisite.prerequisite_id.in_(concept_ids)
        ).all()

        for e in edges:
            forward_adj[e.prerequisite_id].append(e.concept_id)
            in_degree[e.concept_id] += 1

        zero_in_degree = deque([cid for cid, deg in in_degree.items() if deg == 0])
        ordered_ids: List[int] = []

        while zero_in_degree:
            curr = zero_in_degree.popleft()
            ordered_ids.append(curr)

            for dependent in forward_adj[curr]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    zero_in_degree.append(dependent)

        for cid in concept_ids:
            if cid not in ordered_ids:
                ordered_ids.append(cid)

        return ordered_ids

