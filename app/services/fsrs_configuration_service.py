from datetime import timedelta, timezone, datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fsrs import Scheduler

from app.core.config import settings
from app.models.fsrs_review import FSRSConfigRecord, ReviewPreferences
from app.services.fsrs_service import FSRSService


class FSRSConfigurationService:
    """
    Maintains versioned FSRS scheduler configurations and resolves
    student-specific schedulers combining system parameters and student preferences.
    """

    @classmethod
    def get_or_create_active_config(cls, db: Session) -> FSRSConfigRecord:
        """
        Retrieves the current active system configuration or creates an initial
        default record based on settings.
        """
        config = db.query(FSRSConfigRecord).filter(
            FSRSConfigRecord.is_active == True
        ).order_by(FSRSConfigRecord.config_version.desc()).first()

        if not config:
            config = FSRSConfigRecord(
                library_version="6.3.2",
                desired_retention=getattr(settings, "FSRS_DESIRED_RETENTION", 0.90),
                learning_steps=[60, 600],  # 1 min, 10 min represented as seconds
                relearning_steps=[600],    # 10 min
                maximum_interval=getattr(settings, "FSRS_MAXIMUM_INTERVAL", 36500),
                enable_fuzzing=getattr(settings, "FSRS_ENABLE_FUZZING", True),
                parameters=None,           # Use official 21 defaults
                config_version=1,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(config)
            db.commit()
            db.refresh(config)

        return config

    @classmethod
    def get_scheduler_for_student(
        cls,
        db: Session,
        student_id: int,
        enable_fuzzing: Optional[bool] = None,
    ) -> Scheduler:
        """
        Builds an official FSRS Scheduler for a given student.
        Merges system parameters with student's desired retention preference.
        """
        active_config = cls.get_or_create_active_config(db)

        # Retrieve student preferences
        student_pref = db.query(ReviewPreferences).filter(
            ReviewPreferences.student_id == student_id
        ).first()

        desired_retention = student_pref.desired_retention if student_pref else active_config.desired_retention

        # Convert step seconds to timedeltas if stored
        learning_steps = None
        if active_config.learning_steps:
            learning_steps = [timedelta(seconds=s) for s in active_config.learning_steps]

        relearning_steps = None
        if active_config.relearning_steps:
            relearning_steps = [timedelta(seconds=s) for s in active_config.relearning_steps]

        fuzzing = enable_fuzzing if enable_fuzzing is not None else active_config.enable_fuzzing

        return FSRSService.create_scheduler(
            parameters=active_config.parameters,
            desired_retention=desired_retention,
            learning_steps=learning_steps,
            relearning_steps=relearning_steps,
            maximum_interval=active_config.maximum_interval,
            enable_fuzzing=fuzzing,
        )

    @classmethod
    def create_new_config_version(
        cls,
        db: Session,
        desired_retention: float,
        learning_steps_seconds: Optional[List[int]] = None,
        relearning_steps_seconds: Optional[List[int]] = None,
        maximum_interval: int = 36500,
        enable_fuzzing: bool = True,
        parameters: Optional[List[float]] = None,
    ) -> FSRSConfigRecord:
        """
        Creates a new versioned system configuration, deactivating older active records.
        """
        if not FSRSService.validate_desired_retention(desired_retention):
            raise ValueError(f"Invalid desired retention rate: {desired_retention}")

        if parameters is not None and len(parameters) != 21:
            raise ValueError("FSRS 6.3.2 parameters must contain exactly 21 values.")

        current_active = db.query(FSRSConfigRecord).filter(
            FSRSConfigRecord.is_active == True
        ).all()
        for rec in current_active:
            rec.is_active = False

        highest = db.query(FSRSConfigRecord).order_by(
            FSRSConfigRecord.config_version.desc()
        ).first()
        next_version = (highest.config_version + 1) if highest else 1

        new_rec = FSRSConfigRecord(
            library_version="6.3.2",
            desired_retention=desired_retention,
            learning_steps=learning_steps_seconds,
            relearning_steps=relearning_steps_seconds,
            maximum_interval=maximum_interval,
            enable_fuzzing=enable_fuzzing,
            parameters=parameters,
            config_version=next_version,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_rec)
        db.commit()
        db.refresh(new_rec)
        return new_rec
