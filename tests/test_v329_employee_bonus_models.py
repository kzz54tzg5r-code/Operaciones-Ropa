"""Tests for replacement of employee Bonos 3, 4, 5 and 6."""
import pytest
from v329_employee_bonus_models_patch import evaluate_model, MODEL_NAMES


@pytest.mark.parametrize("bonus,expected", [
    (3, 1115.00), (4, 1060.00), (5, 1150.40), (6, 1118.40),
])
def test_four_bonus_formulas(bonus, expected):
    result = evaluate_model(bonus, 108, 12.5, 100, 10, 1000)
    assert result["estimated_amount"] == pytest.approx(expected)
    assert result["attendance_amount"] == pytest.approx(200)
    assert result["commercial_amount"] == pytest.approx(expected - 200)


@pytest.mark.parametrize("bonus", tuple(MODEL_NAMES))
def test_attendance_is_exactly_20_pct_unaccelerated(bonus):
    full = evaluate_model(bonus, 150, 20, 100, 10, 1000)
    half = evaluate_model(bonus, 150, 20, 50, 10, 1000)
    none = evaluate_model(bonus, 150, 20, 0, 10, 1000)
    assert full["estimated_amount"] - none["estimated_amount"] == pytest.approx(200)
    assert half["estimated_amount"] - none["estimated_amount"] == pytest.approx(100)
    assert full["attendance_amount"] == pytest.approx(200)
    assert 0 <= full["commercial_amount"] <= 1000


@pytest.mark.parametrize("bonus", tuple(MODEL_NAMES))
def test_missing_indicators_do_not_create_a_payment(bonus):
    assert evaluate_model(bonus, None, 12.5, 100) is None
    assert evaluate_model(bonus, 108, None, 100) is None
    assert evaluate_model(bonus, 108, 12.5, None) is None


@pytest.mark.parametrize("bonus", tuple(MODEL_NAMES))
def test_negative_ddi_reductions_cannot_be_paid_as_achievement(bonus):
    result = evaluate_model(bonus, 108, -20, 100)
    assert result["ddi_compliance_pct"] == 0
    assert result["attendance_amount"] == 200


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        evaluate_model(2, 108, 12.5, 100)
    with pytest.raises(ValueError):
        evaluate_model(3, 108, 12.5, 100, 0, 1000)
    with pytest.raises(ValueError):
        evaluate_model(3, 108, 12.5, 100, 10, -1000)


def test_investment_is_not_compensated_twice():
    # Only sales, DDI and attendance are accepted as payment inputs.
    # Investment has no scoring argument or weight.
    import inspect
    params = tuple(inspect.signature(evaluate_model).parameters)
    assert params == ("bonus_no", "sales_pct", "ddi_reduction_pct",
                      "attendance_pct", "ddi_target_pct", "base_amount")
