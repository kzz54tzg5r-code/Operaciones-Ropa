"""V330: only real per-store indicators, no simulated inputs or payroll values."""
import pytest
from types import SimpleNamespace
from fastapi import FastAPI, Request
from v330_bonus_indicators_patch import (
    MODEL_NAMES, WEIGHTS, DESIGNS, ddi_improvement, evaluate_store, aggregate, install
)


def test_ddi_uses_only_improved_models_not_investment():
    catalogs = [
        {"models": 3, "ddi_reduced_models": 2, "investment_reduced_models": 3},
        {"models": 1, "ddi_reduced_models": 0, "investment_reduced_models": 1},
    ]
    assert ddi_improvement(catalogs, True) == {"pct": 50.0, "models": 4, "improved": 2}
    assert ddi_improvement(catalogs, False)["pct"] is None
    assert ddi_improvement([], True)["pct"] is None


def test_weights_and_approved_designs():
    assert DESIGNS == {3: "3.2", 4: "4.1", 5: "5.2", 6: "6.1"}
    for number in MODEL_NAMES:
        assert WEIGHTS[number]["attendance"] == 20
        assert "investment" not in WEIGHTS[number]


@pytest.mark.parametrize("bonus,sales,ddi,attendance,expected", [
    (3, 100, 50, 90, 83.0),
    (4, 108, 80, 90, 83.0),
    (6, 100, 50, 100, 84.0),
])
def test_reference_scores_not_payments(bonus, sales, ddi, attendance, expected):
    result = evaluate_store(bonus, sales, ddi, attendance)
    assert result["evaluation_points"] == pytest.approx(expected)
    assert result["attendance_points"] == pytest.approx(attendance * .2)
    assert all("amount" not in k and "payment" not in k for k in result)


def test_b5_does_not_invent_multiplier_threshold():
    assert evaluate_store(5, 115, 80, 98) is None


def test_missing_data_no_false_zero_and_no_score():
    for bonus in (3, 4, 5, 6):
        assert evaluate_store(bonus, None, 40, 100) is None
        assert evaluate_store(bonus, 100, None, 100) is None
        assert evaluate_store(bonus, 100, 40, None) is None


def test_company_sales_weighted_by_real_goals():
    rows = [
        {"store": "A", "sales_pct": 100, "sales_actual": 100, "sales_goal": 100,
         "attendance_reference": 90, "ddi_models": 4, "ddi_improved_models": 2, "ddi_models_pct": 50,
         "initial_ddi": 100, "current_ddi": 90,
         "inventory": {"initial_investment": 150, "current_investment": 120}},
        {"store": "B", "sales_pct": 50, "sales_actual": 150, "sales_goal": 300,
         "attendance_reference": 100, "ddi_models": 6, "ddi_improved_models": 3, "ddi_models_pct": 50,
         "initial_ddi": 120, "current_ddi": 115,
         "inventory": {"initial_investment": 400, "current_investment": 300}},
    ]
    summary = aggregate(rows, True)
    assert summary["sales_pct"] == 62.5
    assert summary["ddi_models_pct"] == 50
    assert summary["inventory"]["capital_variation_mxn"] == 130
    assert summary["inventory"]["initial_ddi"] == 112
    assert aggregate(rows, False)["inventory"]["capital_variation_mxn"] is None


def mock_app(role="admin", comparable=True, tracker=None):
    app = FastAPI()
    samples = [
        {"store": "Centro", "sales_pct": 105, "sales_goal": 100, "sales_actual": 105,
         "attendance_pct": 96, "catalogs": [{"models": 4, "ddi_reduced_models": 3}],
         "inventory": {"initial_ddi": 120, "current_ddi": 100,
                       "initial_investment": 200000, "current_investment": 150000}},
        {"store": "Vallejo", "sales_pct": 95, "sales_goal": 200, "sales_actual": 190,
         "attendance_pct": None, "catalogs": [{"models": 2, "ddi_reduced_models": 1}],
         "inventory": {"initial_ddi": 140, "current_ddi": 130,
                       "initial_investment": 300000, "current_investment": 275000}},
    ]
    @app.get("/api/operation/sales-bonus-v293")
    def fake_base(request: Request, month="", store=""):
        if tracker is not None:
            tracker.append((month, store))
        return {"month": "2026-10", "months": [{"value": "2026-10", "label": "Octubre 2026"}],
                "stores": ["Centro", "Vallejo"],
                "ranking": samples if role == "admin" else samples[:1],
                "selected": {"details": [{"id_art": "store-123"}], "ddi": {"catalogs": []}},
                "source_dates": {"opening_capacity_id": "initial", "current_capacity_id": "current" if comparable else "initial",
                                 "opening_capacity": "2026-10-01", "current_capacity": "2026-10-15"},
                "processing": {"capacity": False, "sales": False}}
    m = SimpleNamespace(app=app, require_user=lambda req: {"role": role, "store": "Centro"})
    install(m)
    route = next(r.endpoint for r in app.routes if getattr(r, "path", None) == "/api/bonuses-v330")
    return route


def test_endpoint_no_simulator_or_payment_and_actual_cuts():
    endpoint = mock_app()
    result = endpoint(request=None, month="2026-10", store="Centro", bonus=3)
    assert result["is_v330"] is True
    assert result["model"]["design"] == "3.2"
    assert result["model"]["cut_comparable"] is True
    assert result["summary"]["ddi_models_pct"] == 75
    assert result["summary"]["inventory"]["capital_variation_mxn"] == 50000
    assert result["summary"]["inventory"]["ddi_reduction_pct"] == pytest.approx(16.67, .01)
    assert result["ranking"][1]["score"] is None  # Missing attendance: not 0.
    assert "base_amount" not in str(result)
    assert "estimated_amount" not in str(result)
    assert "multiplier_needs_authorized_ddi_target" in str(result["model"])


def test_endpoint_waits_for_new_cut_and_restricts_store_role():
    endpoint = mock_app(role="tienda", comparable=False)
    result = endpoint(request=None, store="Vallejo", bonus=6)
    assert result["selected_store"] == "Centro"
    assert result["stores"] == ["Centro", "Vallejo"] or result["stores"] == ["Centro"]
    assert result["summary"]["inventory"]["current_ddi"] is None
    assert result["ranking"][0]["score"] is None
    assert result["ranking"][0]["ddi_models_pct"] is None


def test_bonus_data_is_reused_across_four_models_but_details_are_lazy():
    calls = []
    endpoint = mock_app(tracker=calls)
    for b in (3, 4, 5, 6):
        result = endpoint(request=None, month="2026-10", store="Centro", bonus=b)
        assert result["model"]["design"] in ("3.2", "4.1", "5.2", "6.1")
        assert result["details"] == []  # Basic report must not transport model rows.
    assert len(calls) == 1  # Same real-capacity snapshot for all four bonuses.
    detailed = endpoint(request=None, month="2026-10", store="Centro", bonus=6, include_details=True)
    assert len(calls) == 2
    assert detailed["details"][0]["id_art"] == "store-123"
