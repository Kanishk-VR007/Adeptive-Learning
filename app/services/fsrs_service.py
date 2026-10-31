from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import json

from fsrs import Card, Rating, ReviewLog, Scheduler, State

from app.core.config import settings


class FSRSService:
    """
    Modular, deterministic wrapper around official Py-FSRS library (fsrs==6.3.2).
    Encapsulates Scheduler instantiation, Card creation, review execution,
    retrievability calculation, and card/log serialization.
    """

    DEFAULT_RETENTION: float = getattr(settings, "FSRS_DESIRED_RETENTION", 0.90)
    DEFAULT_MAX_INTERVAL: int = getattr(settings, "FSRS_MAXIMUM_INTERVAL", 36500)
    DEFAULT_ENABLE_FUZZING: bool = getattr(settings, "FSRS_ENABLE_FUZZING", True)

    @classmethod
    def validate_desired_retention(cls, desired_retention: float) -> bool:
        """Validates that retention target is within safe mathematical bounds [0.70, 0.99]."""
        return 0.70 <= desired_retention <= 0.99

    @classmethod
    def create_scheduler(
        cls,
        parameters: Optional[Sequence[float]] = None,
        desired_retention: Optional[float] = None,
        learning_steps: Optional[Union[Tuple[timedelta, ...], List[timedelta]]] = None,
        relearning_steps: Optional[Union[Tuple[timedelta, ...], List[timedelta]]] = None,
        maximum_interval: Optional[int] = None,
        enable_fuzzing: Optional[bool] = None,
    ) -> Scheduler:
        """
        Creates an official FSRS Scheduler instance with configured or default parameters.
        """
        kwargs: Dict[str, Any] = {}

        if parameters is not None:
            if len(parameters) != 21:
                raise ValueError("FSRS 6.3.2 requires exactly 21 model parameters.")
            kwargs["parameters"] = tuple(parameters)

        retention = desired_retention if desired_retention is not None else cls.DEFAULT_RETENTION
        if not cls.validate_desired_retention(retention):
            raise ValueError(f"Desired retention must be between 0.70 and 0.99, received {retention}")
        kwargs["desired_retention"] = retention

        if learning_steps is not None:
            kwargs["learning_steps"] = tuple(learning_steps)

        if relearning_steps is not None:
            kwargs["relearning_steps"] = tuple(relearning_steps)

        kwargs["maximum_interval"] = maximum_interval if maximum_interval is not None else cls.DEFAULT_MAX_INTERVAL
        kwargs["enable_fuzzing"] = enable_fuzzing if enable_fuzzing is not None else cls.DEFAULT_ENABLE_FUZZING

        return Scheduler(**kwargs)

    @classmethod
    def get_default_scheduler(cls, enable_fuzzing: Optional[bool] = None) -> Scheduler:
        """Helper to get a standard scheduler instance with official defaults."""
        return cls.create_scheduler(enable_fuzzing=enable_fuzzing)

    @classmethod
    def create_new_card(cls, card_id: Optional[int] = None) -> Card:
        """
        Initializes an official FSRS Card representing the student's memory state
        for a concept.
        """
        if card_id is not None:
            return Card(card_id=card_id)
        return Card()

    @classmethod
    def review_card(
        cls,
        scheduler: Scheduler,
        card: Card,
        rating: Union[Rating, int],
        review_datetime: Optional[datetime] = None,
        review_duration: Optional[int] = None,
    ) -> Tuple[Card, ReviewLog]:
        """
        Executes a scheduled review on the card using the official Scheduler.
        Ensures review_datetime is UTC timezone-aware.
        """
        if isinstance(rating, int):
            fsrs_rating = Rating(rating)
        elif isinstance(rating, Rating):
            fsrs_rating = rating
        else:
            raise ValueError(f"Invalid rating type: {type(rating)}. Expected Rating enum or int.")

        if review_datetime is not None:
            if review_datetime.tzinfo is None:
                raise ValueError("Review datetime must be timezone-aware (UTC).")
            # Convert to UTC if in another timezone
            review_datetime = review_datetime.astimezone(timezone.utc)
        else:
            review_datetime = datetime.now(timezone.utc)

        updated_card, review_log = scheduler.review_card(
            card=card,
            rating=fsrs_rating,
            review_datetime=review_datetime,
            review_duration=review_duration,
        )
        return updated_card, review_log

    @classmethod
    def get_retrievability(
        cls,
        scheduler: Scheduler,
        card: Card,
        current_datetime: Optional[datetime] = None,
    ) -> float:
        """
        Calculates estimated memory retrievability (recall probability) using official FSRS.
        Returns 0.0 for new unreviewed cards.
        """
        if card.stability is None:
            return 0.0

        if current_datetime is not None:
            if current_datetime.tzinfo is None:
                raise ValueError("Current datetime must be timezone-aware (UTC).")
            current_datetime = current_datetime.astimezone(timezone.utc)
        else:
            current_datetime = datetime.now(timezone.utc)

        r = scheduler.get_card_retrievability(card, current_datetime=current_datetime)
        return max(0.0, min(1.0, float(r)))

    # --- Official Serialization Interfaces ---

    @classmethod
    def card_to_dict(cls, card: Card) -> Dict[str, Any]:
        """Serializes Card to JSON-compatible dictionary."""
        return card.to_dict()

    @classmethod
    def card_from_dict(cls, data: Dict[str, Any]) -> Card:
        """Deserializes Card from dictionary."""
        return Card.from_dict(data)

    @classmethod
    def card_to_json(cls, card: Card) -> str:
        """Serializes Card to JSON string using official Card.to_json()."""
        return card.to_json()

    @classmethod
    def card_from_json(cls, json_str: str) -> Card:
        """Deserializes Card from JSON string using official Card.from_json()."""
        return Card.from_json(json_str)

    @classmethod
    def review_log_to_dict(cls, log: ReviewLog) -> Dict[str, Any]:
        """Serializes ReviewLog to dictionary."""
        return log.to_dict()

    @classmethod
    def review_log_from_dict(cls, data: Dict[str, Any]) -> ReviewLog:
        """Deserializes ReviewLog from dictionary."""
        return ReviewLog.from_dict(data)

    @classmethod
    def review_log_to_json(cls, log: ReviewLog) -> str:
        """Serializes ReviewLog to JSON string using official ReviewLog.to_json()."""
        return log.to_json()

    @classmethod
    def review_log_from_json(cls, json_str: str) -> ReviewLog:
        """Deserializes ReviewLog from JSON string using official ReviewLog.from_json()."""
        return ReviewLog.from_json(json_str)
