from typing import Tuple
from fsrs import Rating


class ReviewRatingService:
    """
    Enforces deterministic validation rules between objective/evaluative answer
    correctness and the student's self-reported recall rating (Again, Hard, Good, Easy).
    """

    RATING_NAMES = {
        Rating.Again.value: "Again",
        Rating.Hard.value: "Hard",
        Rating.Good.value: "Good",
        Rating.Easy.value: "Easy",
    }

    @classmethod
    def get_rating_name(cls, rating: int) -> str:
        return cls.RATING_NAMES.get(rating, f"Unknown ({rating})")

    @classmethod
    def validate_rating(
        cls,
        rating: int,
        is_correct: bool,
        is_partially_correct: bool = False,
        is_unclear: bool = False,
    ) -> Tuple[bool, str]:
        """
        Validates whether the student's submitted recall rating matches the verified correctness:
        - Unclear answer: reject rating update (clarification needed).
        - Incorrect answer: MUST be Again (1).
        - Partially correct: MUST be Again (1) or Hard (2).
        - Correct answer: MUST be Hard (2), Good (3), or Easy (4).
        """
        if rating not in (Rating.Again.value, Rating.Hard.value, Rating.Good.value, Rating.Easy.value):
            return False, f"Invalid rating value: {rating}. Allowed ratings are 1 (Again), 2 (Hard), 3 (Good), 4 (Easy)."

        if is_unclear:
            return False, "Answer evaluation is unclear; clarification is requested and FSRS cannot be updated."

        if not is_correct:
            if rating != Rating.Again.value:
                return False, (
                    f"Answer was incorrect. Policy strictly requires rating 'Again' (1), "
                    f"but received '{cls.get_rating_name(rating)}' ({rating})."
                )
            return True, "Rating accepted for incorrect answer (Again)."

        if is_partially_correct:
            if rating not in (Rating.Again.value, Rating.Hard.value):
                return False, (
                    f"Answer was partially correct. Policy only permits 'Again' (1) or 'Hard' (2), "
                    f"but received '{cls.get_rating_name(rating)}' ({rating})."
                )
            return True, f"Rating accepted for partially correct answer ({cls.get_rating_name(rating)})."

        # Correct answer
        if rating not in (Rating.Hard.value, Rating.Good.value, Rating.Easy.value):
            return False, (
                f"Answer was verified correct. Policy permits 'Hard' (2), 'Good' (3), or 'Easy' (4), "
                f"but received '{cls.get_rating_name(rating)}' ({rating})."
            )

        return True, f"Rating accepted for correct answer ({cls.get_rating_name(rating)})."
