from typing import Optional
from sqlalchemy.orm import Session
from app.models.learner_mastery import BKTParameterConfig
from app.models.syllabus import Concept
from app.services.bkt_service import BKTParameters, BKTService
from app.schemas.learner_mastery import BKTParameterOverrideCreate, BKTParameterResponse


class BKTParameterManager:
    """
    Manages and resolves hierarchical BKT parameters:
    Concept-level override > Subject-level override > Global default parameters.
    """

    GLOBAL_DEFAULT = BKTParameters(
        p_l0=0.20,
        p_transit=0.10,
        p_guess=0.20,
        p_slip=0.10
    )

    @classmethod
    def get_parameters_for_concept(
        cls,
        db: Session,
        concept_id: int
    ) -> BKTParameters:
        """Resolve the most specific applicable BKT parameters for a concept."""
        # 1. Concept-level override
        c_override = db.query(BKTParameterConfig).filter(
            BKTParameterConfig.concept_id == concept_id
        ).first()
        if c_override:
            return BKTParameters(
                p_l0=c_override.p_l0,
                p_transit=c_override.p_transit,
                p_guess=c_override.p_guess,
                p_slip=c_override.p_slip
            )

        # 2. Subject-level override
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if concept and concept.subject_id:
            s_override = db.query(BKTParameterConfig).filter(
                BKTParameterConfig.subject_id == concept.subject_id,
                BKTParameterConfig.concept_id.is_(None)
            ).first()
            if s_override:
                return BKTParameters(
                    p_l0=s_override.p_l0,
                    p_transit=s_override.p_transit,
                    p_guess=s_override.p_guess,
                    p_slip=s_override.p_slip
                )

        # 3. Global default
        return cls.GLOBAL_DEFAULT

    @classmethod
    def set_parameter_override(
        cls,
        db: Session,
        override_in: BKTParameterOverrideCreate
    ) -> BKTParameterResponse:
        """Create or update a subject or concept BKT parameter override."""
        params = BKTParameters(
            p_l0=override_in.p_l0,
            p_transit=override_in.p_transit,
            p_guess=override_in.p_guess,
            p_slip=override_in.p_slip
        )
        BKTService.validate_parameters(params)

        query = db.query(BKTParameterConfig)
        if override_in.concept_id:
            query = query.filter(BKTParameterConfig.concept_id == override_in.concept_id)
        elif override_in.subject_id:
            query = query.filter(
                BKTParameterConfig.subject_id == override_in.subject_id,
                BKTParameterConfig.concept_id.is_(None)
            )

        existing = query.first()
        if existing:
            existing.p_l0 = override_in.p_l0
            existing.p_transit = override_in.p_transit
            existing.p_guess = override_in.p_guess
            existing.p_slip = override_in.p_slip
            db.commit()
            db.refresh(existing)
            return BKTParameterResponse.model_validate(existing)

        config = BKTParameterConfig(
            subject_id=override_in.subject_id,
            concept_id=override_in.concept_id,
            p_l0=override_in.p_l0,
            p_transit=override_in.p_transit,
            p_guess=override_in.p_guess,
            p_slip=override_in.p_slip
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return BKTParameterResponse.model_validate(config)
