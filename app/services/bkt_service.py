from typing import NamedTuple, Optional


class BKTParameters(NamedTuple):
    p_l0: float = 0.20      # Prior probability of knowing concept
    p_transit: float = 0.10 # Learning transition rate
    p_guess: float = 0.20   # Guess probability
    p_slip: float = 0.10    # Slip probability


class BKTUpdateResult(NamedTuple):
    previous_mastery: float
    posterior_mastery: float
    updated_mastery: float
    is_correct: bool
    parameters_used: BKTParameters


class BKTService:
    """
    Pure Python implementation of Bayesian Knowledge Tracing (BKT).
    Deterministic, numerically stable, and free of external LLM dependencies.
    """

    DEFAULT_PARAMETERS = BKTParameters(
        p_l0=0.20,
        p_transit=0.10,
        p_guess=0.20,
        p_slip=0.10
    )

    @classmethod
    def validate_parameters(cls, params: BKTParameters) -> None:
        """Validate that all BKT probabilities lie strictly within [0, 1]."""
        for name, val in [
            ("P(L0)", params.p_l0),
            ("P(T)", params.p_transit),
            ("P(G)", params.p_guess),
            ("P(S)", params.p_slip)
        ]:
            if not isinstance(val, (int, float)):
                raise ValueError(f"BKT parameter {name} must be a numeric value, got {type(val).__name__}")
            if val < 0.0 or val > 1.0:
                raise ValueError(f"BKT parameter {name} must be between 0.0 and 1.0, got {val}")

        # Identifiability and degenerate boundary check
        if params.p_guess + params.p_slip >= 1.0:
            raise ValueError(
                f"Degenerate BKT parameter configuration: P(G) + P(S) must be less than 1.0. "
                f"Got P(G)={params.p_guess}, P(S)={params.p_slip}"
            )

    @classmethod
    def calculate_posterior(
        cls,
        prior_mastery: float,
        is_correct: bool,
        params: BKTParameters
    ) -> float:
        """
        Calculate posterior probability P(L | observation) given evidence.
        """
        if not (0.0 <= prior_mastery <= 1.0):
            raise ValueError(f"Prior mastery must be within [0.0, 1.0], got {prior_mastery}")

        cls.validate_parameters(params)
        p_l = prior_mastery
        p_s = params.p_slip
        p_g = params.p_guess

        if is_correct:
            numerator = p_l * (1.0 - p_s)
            denominator = numerator + ((1.0 - p_l) * p_g)
        else:
            numerator = p_l * p_s
            denominator = numerator + ((1.0 - p_l) * (1.0 - p_g))

        # Numerical stability against zero division
        if abs(denominator) < 1e-12:
            return p_l

        posterior = numerator / denominator
        return max(0.0, min(1.0, posterior))

    @classmethod
    def apply_transition(
        cls,
        posterior_mastery: float,
        params: BKTParameters
    ) -> float:
        """
        Apply learning transition: P(L_next) = P(L | Answer) + [1 - P(L | Answer)] * P(T)
        """
        cls.validate_parameters(params)
        p_post = max(0.0, min(1.0, posterior_mastery))
        p_next = p_post + ((1.0 - p_post) * params.p_transit)
        return max(0.0, min(1.0, p_next))

    @classmethod
    def update_mastery(
        cls,
        current_mastery: float,
        is_correct: bool,
        params: Optional[BKTParameters] = None
    ) -> BKTUpdateResult:
        """
        Execute full BKT step: calculates posterior and applies learning transition.
        """
        parameters = params or cls.DEFAULT_PARAMETERS
        posterior = cls.calculate_posterior(current_mastery, is_correct, parameters)
        updated = cls.apply_transition(posterior, parameters)

        return BKTUpdateResult(
            previous_mastery=current_mastery,
            posterior_mastery=posterior,
            updated_mastery=updated,
            is_correct=is_correct,
            parameters_used=parameters
        )
