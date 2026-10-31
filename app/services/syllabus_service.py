from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.concept_graph import ConceptPrerequisite, RelationshipType
from app.schemas.syllabus import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    ConceptDetailResponse,
    ConceptSummary
)


class SyllabusService:
    # --- Subject Management ---
    @staticmethod
    def get_subject(db: Session, subject_id: int) -> Optional[Subject]:
        return db.query(Subject).filter(Subject.id == subject_id).first()

    @staticmethod
    def get_subject_by_code(db: Session, code: str) -> Optional[Subject]:
        return db.query(Subject).filter(Subject.code == code.strip().upper()).first()

    @classmethod
    def list_subjects(cls, db: Session, skip: int = 0, limit: int = 100) -> List[SubjectResponse]:
        subjects = db.query(Subject).offset(skip).limit(limit).all()
        result = []
        for s in subjects:
            chapters_count = db.query(func.count(Chapter.id)).filter(Chapter.subject_id == s.id).scalar() or 0
            resp = SubjectResponse.model_validate(s)
            resp.chapters_count = chapters_count
            result.append(resp)
        return result

    @classmethod
    def create_subject(cls, db: Session, obj_in: SubjectCreate) -> SubjectResponse:
        existing = cls.get_subject_by_code(db, obj_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subject with code '{obj_in.code.upper()}' already exists"
            )
        subject = Subject(
            code=obj_in.code.strip().upper(),
            name=obj_in.name.strip(),
            description=obj_in.description.strip() if obj_in.description else None
        )
        db.add(subject)
        db.commit()
        db.refresh(subject)
        resp = SubjectResponse.model_validate(subject)
        resp.chapters_count = 0
        return resp

    @classmethod
    def update_subject(cls, db: Session, subject_id: int, obj_in: SubjectUpdate) -> SubjectResponse:
        subject = cls.get_subject(db, subject_id)
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        if obj_in.code:
            code_clean = obj_in.code.strip().upper()
            if code_clean != subject.code:
                existing = cls.get_subject_by_code(db, code_clean)
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Subject with code '{code_clean}' already exists"
                    )
                subject.code = code_clean

        if obj_in.name is not None:
            subject.name = obj_in.name.strip()
        if obj_in.description is not None:
            subject.description = obj_in.description.strip() if obj_in.description else None

        db.commit()
        db.refresh(subject)
        chapters_count = db.query(func.count(Chapter.id)).filter(Chapter.subject_id == subject.id).scalar() or 0
        resp = SubjectResponse.model_validate(subject)
        resp.chapters_count = chapters_count
        return resp

    @classmethod
    def delete_subject(cls, db: Session, subject_id: int) -> None:
        subject = cls.get_subject(db, subject_id)
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
        db.delete(subject)
        db.commit()

    # --- Chapter Management ---
    @staticmethod
    def get_chapter(db: Session, chapter_id: int) -> Optional[Chapter]:
        return db.query(Chapter).filter(Chapter.id == chapter_id).first()

    @classmethod
    def list_chapters(
        cls,
        db: Session,
        subject_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChapterResponse]:
        query = db.query(Chapter)
        if subject_id is not None:
            query = query.filter(Chapter.subject_id == subject_id)
        chapters = query.order_by(Chapter.chapter_number).offset(skip).limit(limit).all()

        result = []
        for ch in chapters:
            concepts_count = db.query(func.count(Concept.id)).filter(Concept.chapter_id == ch.id).scalar() or 0
            resp = ChapterResponse.model_validate(ch)
            resp.concepts_count = concepts_count
            result.append(resp)
        return result

    @classmethod
    def create_chapter(cls, db: Session, obj_in: ChapterCreate) -> ChapterResponse:
        subject = cls.get_subject(db, obj_in.subject_id)
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent subject not found")

        existing = db.query(Chapter).filter(
            Chapter.subject_id == obj_in.subject_id,
            Chapter.chapter_number == obj_in.chapter_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Chapter #{obj_in.chapter_number} already exists for subject {subject.name}"
            )

        chapter = Chapter(
            subject_id=obj_in.subject_id,
            chapter_number=obj_in.chapter_number,
            title=obj_in.title.strip(),
            description=obj_in.description.strip() if obj_in.description else None
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        resp = ChapterResponse.model_validate(chapter)
        resp.concepts_count = 0
        return resp

    @classmethod
    def update_chapter(cls, db: Session, chapter_id: int, obj_in: ChapterUpdate) -> ChapterResponse:
        chapter = cls.get_chapter(db, chapter_id)
        if not chapter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

        if obj_in.chapter_number is not None and obj_in.chapter_number != chapter.chapter_number:
            existing = db.query(Chapter).filter(
                Chapter.subject_id == chapter.subject_id,
                Chapter.chapter_number == obj_in.chapter_number
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Chapter #{obj_in.chapter_number} already exists in this subject"
                )
            chapter.chapter_number = obj_in.chapter_number

        if obj_in.title is not None:
            chapter.title = obj_in.title.strip()
        if obj_in.description is not None:
            chapter.description = obj_in.description.strip() if obj_in.description else None

        db.commit()
        db.refresh(chapter)
        concepts_count = db.query(func.count(Concept.id)).filter(Concept.chapter_id == chapter.id).scalar() or 0
        resp = ChapterResponse.model_validate(chapter)
        resp.concepts_count = concepts_count
        return resp

    @classmethod
    def delete_chapter(cls, db: Session, chapter_id: int) -> None:
        chapter = cls.get_chapter(db, chapter_id)
        if not chapter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
        db.delete(chapter)
        db.commit()

    # --- Concept Management ---
    @staticmethod
    def get_concept(db: Session, concept_id: int) -> Optional[Concept]:
        return db.query(Concept).filter(Concept.id == concept_id).first()

    @staticmethod
    def get_concept_by_code(db: Session, concept_code: str) -> Optional[Concept]:
        return db.query(Concept).filter(Concept.concept_code == concept_code.strip().upper()).first()

    @classmethod
    def list_concepts(
        cls,
        db: Session,
        subject_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        difficulty_level: Optional[DifficultyLevel] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ConceptResponse]:
        query = db.query(Concept)
        if subject_id is not None:
            query = query.filter(Concept.subject_id == subject_id)
        if chapter_id is not None:
            query = query.filter(Concept.chapter_id == chapter_id)
        if difficulty_level is not None:
            query = query.filter(Concept.difficulty_level == difficulty_level)

        concepts = query.offset(skip).limit(limit).all()
        return [ConceptResponse.model_validate(c) for c in concepts]

    @classmethod
    def get_concept_detail(cls, db: Session, concept_id: int) -> ConceptDetailResponse:
        concept = cls.get_concept(db, concept_id)
        if not concept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

        prereqs = [
            ConceptSummary.model_validate(p.prerequisite_concept)
            for p in concept.prerequisites
            if p.prerequisite_concept
        ]
        dependents = [
            ConceptSummary.model_validate(d.concept)
            for d in concept.dependents
            if d.concept
        ]

        resp = ConceptDetailResponse.model_validate(concept)
        resp.prerequisites = prereqs
        resp.dependents = dependents
        return resp

    @classmethod
    def create_concept(cls, db: Session, obj_in: ConceptCreate) -> ConceptResponse:
        # Validate unique code
        existing = cls.get_concept_by_code(db, obj_in.concept_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Concept with code '{obj_in.concept_code.upper()}' already exists"
            )

        # Validate subject & chapter hierarchy
        subject = cls.get_subject(db, obj_in.subject_id)
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        chapter = cls.get_chapter(db, obj_in.chapter_id)
        if not chapter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

        if chapter.subject_id != subject.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified chapter does not belong to the specified subject"
            )

        concept = Concept(
            concept_code=obj_in.concept_code.strip().upper(),
            subject_id=obj_in.subject_id,
            chapter_id=obj_in.chapter_id,
            name=obj_in.name.strip(),
            description=obj_in.description.strip(),
            difficulty_level=obj_in.difficulty_level,
            learning_objectives=obj_in.learning_objectives or []
        )
        db.add(concept)
        db.commit()
        db.refresh(concept)

        # Handle initial prerequisites if specified
        if obj_in.prerequisite_ids:
            from app.services.graph_service import GraphService
            for prereq_id in obj_in.prerequisite_ids:
                GraphService.add_prerequisite(
                    db=db,
                    concept_id=concept.id,
                    prerequisite_id=prereq_id,
                    relationship_type=RelationshipType.STRICT
                )

        db.refresh(concept)
        return ConceptResponse.model_validate(concept)

    @classmethod
    def update_concept(cls, db: Session, concept_id: int, obj_in: ConceptUpdate) -> ConceptResponse:
        concept = cls.get_concept(db, concept_id)
        if not concept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

        if obj_in.chapter_id is not None and obj_in.chapter_id != concept.chapter_id:
            chapter = cls.get_chapter(db, obj_in.chapter_id)
            if not chapter or chapter.subject_id != concept.subject_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid chapter ID or chapter belongs to another subject"
                )
            concept.chapter_id = obj_in.chapter_id

        if obj_in.name is not None:
            concept.name = obj_in.name.strip()
        if obj_in.description is not None:
            concept.description = obj_in.description.strip()
        if obj_in.difficulty_level is not None:
            concept.difficulty_level = obj_in.difficulty_level
        if obj_in.learning_objectives is not None:
            concept.learning_objectives = obj_in.learning_objectives

        db.commit()
        db.refresh(concept)
        return ConceptResponse.model_validate(concept)

    @classmethod
    def delete_concept(cls, db: Session, concept_id: int) -> None:
        concept = cls.get_concept(db, concept_id)
        if not concept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")
        db.delete(concept)
        db.commit()
