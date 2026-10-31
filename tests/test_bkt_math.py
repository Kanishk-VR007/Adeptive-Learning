import pytest
import math
from app.services.bkt_service import BKTService, BKTParameters


def test_bkt_default_parameters():
    params = BKTService.DEFAULT_PARAMETERS
    assert params.p_l0 == 0.20
    assert params.p_transit == 0.10
    assert params.p_guess == 0.20
    assert params.p_slip == 0.10


def test_bkt_correct_answer_standard():
    """
    With defaults: P(L0)=0.20, P(T)=0.10, P(G)=0.20, P(S)=0.10
    P(L | Correct) = (0.20 * 0.90) / ((0.20 * 0.90) + (0.80 * 0.20)) = 0.18 / 0.34 ≈ 0.5294117647
    P(L_next) = 0.5294117647 + (1 - 0.5294117647) * 0.10 ≈ 0.5764705882
    """
    result = BKTService.update_mastery(
        current_mastery=0.20,
        is_correct=True,
        params=BKTService.DEFAULT_PARAMETERS
    )

    expected_posterior = 0.18 / 0.34
    expected_next = expected_posterior + (1.0 - expected_posterior) * 0.10

    assert math.isclose(result.posterior_mastery, expected_posterior, rel_tol=1e-7)
    assert math.isclose(result.updated_mastery, expected_next, rel_tol=1e-7)
    assert math.isclose(result.posterior_mastery, 0.5294117647, abs_tol=1e-5)
    assert math.isclose(result.updated_mastery, 0.5764705882, abs_tol=1e-5)


def test_bkt_incorrect_answer_from_half_prior():
    """
    From P(L) = 0.50:
    P(L | Incorrect) = (0.50 * 0.10) / ((0.50 * 0.10) + (0.50 * 0.80)) = 0.05 / 0.45 = 1/9 ≈ 0.1111111111
    P(L_next) = 1/9 + (8/9) * 0.10 = 0.20
    """
    result = BKTService.update_mastery(
        current_mastery=0.50,
        is_correct=False,
        params=BKTService.DEFAULT_PARAMETERS
    )

    expected_posterior = 1.0 / 9.0
    expected_next = 0.20

    assert math.isclose(result.posterior_mastery, expected_posterior, rel_tol=1e-7)
    assert math.isclose(result.updated_mastery, expected_next, rel_tol=1e-7)
    assert math.isclose(result.posterior_mastery, 0.1111111111, abs_tol=1e-5)
    assert math.isclose(result.updated_mastery, 0.20, abs_tol=1e-5)


def test_bkt_incorrect_answer_from_default_prior():
    """
    From P(L0) = 0.20:
    P(L | Incorrect) = (0.20 * 0.10) / ((0.20 * 0.10) + (0.80 * 0.80)) = 0.02 / 0.66 = 1/33 ≈ 0.030303
    Wait, (1 - P(G)) = 1 - 0.20 = 0.80.
    Denominator = 0.02 + 0.80 * 0.80 = 0.02 + 0.64 = 0.66.
    """
    result = BKTService.update_mastery(
        current_mastery=0.20,
        is_correct=False,
        params=BKTService.DEFAULT_PARAMETERS
    )
    expected_posterior = 0.02 / 0.66
    expected_next = expected_posterior + (1.0 - expected_posterior) * 0.10

    assert math.isclose(result.posterior_mastery, expected_posterior, rel_tol=1e-7)
    assert math.isclose(result.updated_mastery, expected_next, rel_tol=1e-7)
    assert 0.0 <= result.updated_mastery <= 1.0


def test_repeated_correct_answers_monotonically_increase():
    """Consecutive correct answers should monotonically increase mastery toward 1.0."""
    m = 0.20
    for _ in range(6):
        res = BKTService.update_mastery(current_mastery=m, is_correct=True)
        assert res.updated_mastery > m
        assert 0.0 <= res.updated_mastery <= 1.0
        m = res.updated_mastery
    # After 6 correct answers, mastery should exceed 0.90
    assert m > 0.90


def test_repeated_incorrect_answers():
    """Consecutive incorrect answers should decrease mastery."""
    m = 0.80
    for _ in range(5):
        res = BKTService.update_mastery(current_mastery=m, is_correct=False)
        assert res.updated_mastery < m
        assert 0.0 <= res.updated_mastery <= 1.0
        m = res.updated_mastery


def test_alternating_responses_stability():
    """Alternating correct and incorrect answers remain stable within [0, 1]."""
    m = 0.20
    sequence = [True, False, True, False, True, True]
    for ans in sequence:
        res = BKTService.update_mastery(current_mastery=m, is_correct=ans)
        assert 0.0 <= res.updated_mastery <= 1.0
        m = res.updated_mastery


def test_invalid_parameter_rejection():
    """Invalid parameter values must raise ValueError."""
    # Negative probability
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        BKTService.validate_parameters(BKTParameters(p_l0=-0.1))

    # Probability > 1
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        BKTService.validate_parameters(BKTParameters(p_transit=1.5))

    # Non-numeric
    with pytest.raises(ValueError, match="must be a numeric value"):
        BKTService.validate_parameters(BKTParameters(p_guess="high"))  # type: ignore

    # Degenerate P(G) + P(S) >= 1.0
    with pytest.raises(ValueError, match="Degenerate BKT parameter configuration"):
        BKTService.validate_parameters(BKTParameters(p_guess=0.6, p_slip=0.5))


def test_zero_denominator_protection():
    """Extreme edge case: prior=0.0 with incorrect answer produces zero division handled safely."""
    res = BKTService.update_mastery(
        current_mastery=0.0,
        is_correct=False,
        params=BKTParameters(p_l0=0.0, p_transit=0.0, p_guess=0.2, p_slip=0.1)
    )
    assert 0.0 <= res.updated_mastery <= 1.0
