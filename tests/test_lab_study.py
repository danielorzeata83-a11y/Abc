import json

import numpy as np
import pandas as pd
import pytest

from sensa.lab_study import DEFAULT_CONFIG, run_study, write_artifacts


def synthetic(n=1100, seed=0):
    rng = np.random.default_rng(seed)
    mu = np.array([0.35, 0.25, 0.05, 0.0, -0.10, 0.02]) / 252
    vol = np.array([0.012, 0.012, 0.012, 0.012, 0.012, 0.012])
    R = rng.normal(mu, vol, size=(n, 6))
    idx = [pd.Timestamp((20000 + i) * 86400, unit="s").strftime("%Y-%m-%d") for i in range(n)]
    prices = pd.DataFrame(100 * np.cumprod(1 + R, axis=0), index=idx, columns=list("ABCDEF"))
    spy = pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.008, n)), index=idx)
    return prices, spy


FAST = {"window": 200, "every": 21, "lam_grid": [3.0, 10.0], "kappa_grid": [0.005], "cvar_lam_grid": [1.0], "cap": 0.5,
        "cvar_iters": 300, "perturbations": 5}
MANIFEST = {"tickers": list("ABCDEF"), "sha256": "x", "rows": 1100, "start": "a", "end": "b", "dropped": [], "source": "synthetic"}


@pytest.fixture(scope="module")
def result():
    prices, spy = synthetic()
    return run_study(prices, MANIFEST, {**DEFAULT_CONFIG, **FAST}, benchmark=spy)


def test_periods_are_chronological_and_the_final_test_is_untouched_by_tuning(result):
    p = result["periods"]
    assert p["eval_start"] < p["validation_end"] < p["end"]
    assert result["validation"]["selected"].keys() >= {"mean_variance", "mv_costs", "extended", "cvar"}
    assert all(g["sharpe"] is None or isinstance(g["sharpe"], float) for g in result["validation"]["grid"])


def test_the_study_compares_all_baselines_on_the_same_test_days(result):
    models = result["test"]["models"]
    assert set(models) >= {"equal_weight", "mean_variance", "mv_costs", "extended", "cvar", "benchmark"}
    days = {m["days"] for m in models.values()}
    assert len(days) == 1
    for name in ("equal_weight", "extended"):
        assert {"ann_return", "sharpe", "max_drawdown", "cvar95", "avg_turnover", "cost_total"} <= models[name].keys()


def test_acceptance_is_reported_honestly_whichever_way_the_comparison_goes(result):
    # with a 200-day window and noisy means the optimiser can legitimately lose to equal weights: the report must say so
    m = result["test"]["models"]
    ids = {a["id"]: a for a in result["acceptance"]}
    assert ids["beats_equal_weight"]["pass"] == (m["extended"]["sharpe"] > m["equal_weight"]["sharpe"])
    assert set(ids) == {"net_return", "beats_equal_weight", "constraints", "subwindows", "stability", "concentration", "reproducible"}
    assert ids["constraints"]["pass"] and ids["reproducible"]["pass"]
    assert all("text" in a and "detail" in a for a in ids.values())


def test_curves_weights_and_answers_are_present_for_the_report(result):
    c = result["curves"]
    assert len(c["dates"]) == result["test"]["models"]["equal_weight"]["days"] and c["models"]["extended"][0] == pytest.approx(1.0, abs=0.05)
    assert abs(sum(result["weights"]["extended"].values()) - 1) < 1e-6 and max(result["weights"]["extended"].values()) <= 0.5 + 1e-6
    assert len(result["answers"]) == 6


def test_same_inputs_give_identical_results():
    prices, spy = synthetic(700, seed=1)
    cfg = {**DEFAULT_CONFIG, **FAST, "window": 150}
    a = run_study(prices, MANIFEST, cfg, benchmark=spy)
    b = run_study(prices, MANIFEST, cfg, benchmark=spy)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_artifacts_are_written_and_the_report_states_the_limits(result, tmp_path):
    out = write_artifacts(str(tmp_path / "run1"), result)
    files = {p.name for p in (tmp_path / "run1").iterdir()}
    assert {"config.json", "data_manifest.json", "metrics.json", "weights.csv", "returns.csv", "report.md", "result.json"} <= files
    md = (tmp_path / "run1" / "report.md").read_text(encoding="utf-8")
    assert "not investment advice" in md.lower() and "Acceptance" in md and out == str(tmp_path / "run1")


def test_too_little_history_for_the_window_is_a_clear_error():
    prices, spy = synthetic(300)
    with pytest.raises(ValueError, match="history"):
        run_study(prices, MANIFEST, {**DEFAULT_CONFIG, **FAST, "window": 250})


def test_warnings_list_dropped_tickers_and_parameters_chosen_at_the_edge_of_the_grid():
    prices, spy = synthetic(900)
    manifest = {**MANIFEST, "dropped": [{"ticker": "ZZZ", "reason": "HTTP 429"}]}
    r = run_study(prices, manifest, {**DEFAULT_CONFIG, **FAST, "window": 150}, benchmark=spy)
    text = " ".join(r["warnings"])
    assert "ZZZ" in text and "HTTP 429" in text
    edge = [g for g in r["validation"]["selected"].values() if g["lam"] in (min(FAST["lam_grid"]), max(FAST["lam_grid"]))]
    assert (len([w for w in r["warnings"] if "edge of the grid" in w]) >= 1) == bool(edge)
    assert "Warnings" in __import__("sensa.lab_study", fromlist=["x"]).report_markdown(r)
