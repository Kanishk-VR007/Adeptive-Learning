import json
from datetime import datetime, timedelta, timezone
import pytest
from fsrs import Card, Rating, ReviewLog, Scheduler, State

from app.services.fsrs_service import FSRSService


class TestFSRSScheduler:
    """
    Unit and deterministic behavioral tests for official FSRS Scheduler (fsrs==6.3.2).
    Uses deterministic settings (fuzzing disabled) for exact transition verification.
    """

    @pytest.fixture
    def scheduler(self) -> Scheduler:
        # Deterministic scheduler with fuzzing disabled
        return FSRSService.create_scheduler(
            desired_retention=0.90,
            enable_fuzzing=False,
        )

    def test_scheduler_initialization_defaults(self):
        s = FSRSService.get_default_scheduler(enable_fuzzing=False)
        assert s.desired_retention == 0.90
        assert s.maximum_interval == 36500
        assert s.enable_fuzzing is False

    def test_card_initialization(self):
        card = FSRSService.create_new_card()
        assert card.state == State.Learning
        assert card.step == 0
        assert card.stability is None
        assert card.difficulty is None
        assert card.due is not None
        assert card.due.tzinfo == timezone.utc
        assert card.last_review is None

    def test_rating_again_transition(self, scheduler: Scheduler):
        card = FSRSService.create_new_card()
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        updated_card, log = FSRSService.review_card(
            scheduler=scheduler,
            card=card,
            rating=Rating.Again,
            review_datetime=now,
        )

        assert updated_card.state == State.Learning
        assert updated_card.step == 0
        assert updated_card.stability is not None
        assert updated_card.difficulty is not None
        assert updated_card.due > now
        assert updated_card.last_review == now
        assert log.rating == Rating.Again
        assert log.review_datetime == now

    def test_rating_hard_transition(self, scheduler: Scheduler):
        card = FSRSService.create_new_card()
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        updated_card, log = FSRSService.review_card(
            scheduler=scheduler,
            card=card,
            rating=Rating.Hard,
            review_datetime=now,
        )
        assert updated_card.state == State.Learning
        assert updated_card.stability is not None
        assert updated_card.difficulty is not None
        assert log.rating == Rating.Hard

    def test_rating_good_transition(self, scheduler: Scheduler):
        card = FSRSService.create_new_card()
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        updated_card, log = FSRSService.review_card(
            scheduler=scheduler,
            card=card,
            rating=Rating.Good,
            review_datetime=now,
        )
        assert updated_card.state == State.Learning
        assert updated_card.step == 1
        assert updated_card.stability is not None
        assert updated_card.difficulty is not None
        assert log.rating == Rating.Good

    def test_rating_easy_transition(self, scheduler: Scheduler):
        card = FSRSService.create_new_card()
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        updated_card, log = FSRSService.review_card(
            scheduler=scheduler,
            card=card,
            rating=Rating.Easy,
            review_datetime=now,
        )
        # Rating.Easy graduates immediately to State.Review
        assert updated_card.state == State.Review
        assert updated_card.step is None
        assert updated_card.stability is not None
        assert updated_card.difficulty is not None
        assert updated_card.due > now + timedelta(days=1)
        assert log.rating == Rating.Easy

    def test_relearning_after_lapse(self, scheduler: Scheduler):
        # 1. Graduate card to Review state with Easy
        now1 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
        card, _ = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Easy, review_datetime=now1)
        assert card.state == State.Review
        pre_lapse_stability = card.stability

        # 2. Review on due date and fail (Again) -> lapse
        now2 = card.due
        card_lapsed, log2 = FSRSService.review_card(scheduler, card, Rating.Again, review_datetime=now2)
        assert card_lapsed.state == State.Relearning
        assert log2.rating == Rating.Again
        # Stability post-lapse should be lower than pre-lapse stability
        assert card_lapsed.stability < pre_lapse_stability

    def test_desired_retention_effect(self):
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        # Higher retention (0.95) should require shorter intervals (earlier review) than lower retention (0.80)
        s_high = FSRSService.create_scheduler(desired_retention=0.95, enable_fuzzing=False)
        s_low = FSRSService.create_scheduler(desired_retention=0.80, enable_fuzzing=False)

        card1, _ = FSRSService.review_card(s_high, FSRSService.create_new_card(), Rating.Easy, review_datetime=now)
        card2, _ = FSRSService.review_card(s_low, FSRSService.create_new_card(), Rating.Easy, review_datetime=now)

        interval_high = (card1.due - now).total_seconds()
        interval_low = (card2.due - now).total_seconds()

        assert interval_high < interval_low

    def test_maximum_interval_clamping(self):
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        s_capped = FSRSService.create_scheduler(
            desired_retention=0.70,
            maximum_interval=30,  # Max 30 days
            enable_fuzzing=False,
        )
        card, _ = FSRSService.review_card(s_capped, FSRSService.create_new_card(), Rating.Easy, review_datetime=now)
        # Review several times with Easy to push interval beyond 30 days
        for _ in range(5):
            now = card.due
            card, _ = FSRSService.review_card(s_capped, card, Rating.Easy, review_datetime=now)

        days = (card.due - now).total_seconds() / 86400.0
        assert days <= 30.01

    def test_retrievability_decay_over_time(self, scheduler: Scheduler):
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        card, _ = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Good, review_datetime=now)

        # Immediate retrievability
        r_now = FSRSService.get_retrievability(scheduler, card, current_datetime=now)
        assert r_now == 1.0

        # 3 days later
        r_3d = FSRSService.get_retrievability(scheduler, card, current_datetime=now + timedelta(days=3))
        # 10 days later
        r_10d = FSRSService.get_retrievability(scheduler, card, current_datetime=now + timedelta(days=10))

        assert 0.0 < r_10d < r_3d < r_now
        assert r_now == 1.0

    def test_retrievability_for_new_card(self, scheduler: Scheduler):
        new_card = FSRSService.create_new_card()
        r = FSRSService.get_retrievability(scheduler, new_card)
        assert r == 0.0


class TestFSRSSerialization:
    """
    Tests Card and ReviewLog JSON/dict serialization round-trips and
    persistence across simulated application restarts.
    """

    def test_card_to_and_from_json(self):
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card, _ = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Good)

        json_str = FSRSService.card_to_json(card)
        restored = FSRSService.card_from_json(json_str)

        assert restored.state == card.state
        assert restored.step == card.step
        assert restored.stability == card.stability
        assert restored.difficulty == card.difficulty
        assert restored.due == card.due
        assert restored.last_review == card.last_review

    def test_card_to_and_from_dict(self):
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card, _ = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Hard)

        d = FSRSService.card_to_dict(card)
        restored = FSRSService.card_from_dict(d)

        assert restored.stability == card.stability
        assert restored.difficulty == card.difficulty
        assert restored.due == card.due

    def test_review_log_to_and_from_json(self):
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        _, log = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Easy)

        json_str = FSRSService.review_log_to_json(log)
        restored_log = FSRSService.review_log_from_json(json_str)

        assert restored_log.rating == log.rating
        assert restored_log.review_datetime == log.review_datetime

    def test_restored_card_produces_identical_scheduling(self):
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        now = datetime(2026, 10, 31, 12, 0, 0, tzinfo=timezone.utc)
        card1, _ = FSRSService.review_card(scheduler, FSRSService.create_new_card(), Rating.Good, review_datetime=now)

        # Serialize card1 to simulate DB save
        saved_json = FSRSService.card_to_json(card1)

        # Restore in a fresh session
        card2 = FSRSService.card_from_json(saved_json)

        # Execute next review on both
        next_review_time = now + timedelta(days=1)
        next1, _ = FSRSService.review_card(scheduler, card1, Rating.Good, review_datetime=next_review_time)
        next2, _ = FSRSService.review_card(scheduler, card2, Rating.Good, review_datetime=next_review_time)

        assert next1.due == next2.due
        assert next1.stability == next2.stability
        assert next1.difficulty == next2.difficulty
        assert next1.state == next2.state


class TestFSRSConfigurationValidation:
    """
    Tests configuration parameter validation.
    """

    def test_valid_custom_retention(self):
        assert FSRSService.validate_desired_retention(0.85) is True
        assert FSRSService.validate_desired_retention(0.70) is True
        assert FSRSService.validate_desired_retention(0.99) is True

    def test_invalid_retention(self):
        assert FSRSService.validate_desired_retention(0.69) is False
        assert FSRSService.validate_desired_retention(1.00) is False
        assert FSRSService.validate_desired_retention(-0.1) is False

        with pytest.raises(ValueError, match="Desired retention must be between 0.70 and 0.99"):
            FSRSService.create_scheduler(desired_retention=0.65)

    def test_invalid_parameter_count(self):
        with pytest.raises(ValueError, match="FSRS 6.3.2 requires exactly 21 model parameters"):
            FSRSService.create_scheduler(parameters=[0.1, 0.2, 0.3])
