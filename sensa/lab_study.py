"""The portfolio-lab study: the protocol of the methodology documents, end to end.

Chronological split: warm-up window -> validation (tune lambda / kappa per model family) -> final test, run once with
the chosen parameters. Baselines on the same test days: equal weights, plain mean-variance, mean-variance with
turnover costs, the extended model (shrinkage + cap + costs), a CVaR model, and a benchmark (e.g. S&P 500).
Acceptance criteria are fixed in the config *before* the test is run and reported pass / fail with the numbers."""

import json
import math
import os

import numpy as np
import pandas as pd

from sensa.lab_backtest import (equal_weight, make_cvar, make_mean_variance, metrics, walk_forward, _inputs)
from sensa.lab_solvers import solve_portfolio

DEFAULT_CONFIG = {
    "window": 504, "every": 21, "cost_bps": 5.0, "cap": 0.35, "validation_share": 0.7,
    "lam_grid": [0.5, 1.0, 2.0, 5.0, 10.0, 20.0], "kappa_grid": [0.002, 0.01, 0.05], "cvar_lam_grid": [0.25, 0.5, 1.0, 2.0],
    "cvar_alpha": 0.95, "cvar_iters": 1500, "perturbations": 10, "perturbation_noise": 0.10, "seed": 0,
    "criteria": {"min_net_ann_return": 0.0, "min_subwindows_beating": 0.5, "max_weight_instability": 0.5,
                 "max_top2_contribution": 0.7, "min_effective_n": 3.0},
}
NOTICE = ("Research output, not investment advice. Past results do not guarantee future performance; the universe was "
          "chosen with today's knowledge (survivorship bias), costs are a flat proportional model, and the test period is one path.")


def _f(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)


def _model_stats(res, extra=None):
    m = {k: (v if k == "days" else _f(v)) for k, v in metrics(res["returns"]).items()}
    m["avg_turnover"] = _f(np.mean(res["turnover"][1:])) if len(res["turnover"]) > 1 else 0.0
    m["cost_total"] = _f(res["cost_total"])
    m["rebalances"] = len(res["turnover"])
    return {**m, **(extra or {})}


def _families(cfg):
    for lam in cfg["lam_grid"]:
        yield "mean_variance", {"lam": lam, "kappa": 0.0, "shrink": False, "cap": 1.0}
    for lam in cfg["lam_grid"]:
        for kappa in cfg["kappa_grid"]:
            yield "mv_costs", {"lam": lam, "kappa": kappa, "shrink": False, "cap": 1.0}
            yield "extended", {"lam": lam, "kappa": kappa, "shrink": True, "cap": cfg["cap"]}
    for lam in cfg["cvar_lam_grid"]:
        yield "cvar", {"lam": lam, "shrink": True, "cap": cfg["cap"]}


def _strategy(family, p, cfg, log=None):
    if family == "cvar":
        return make_cvar(p["lam"], cfg["cvar_alpha"], p["cap"], p["shrink"], log=log, iters=cfg["cvar_iters"])
    return make_mean_variance(p["lam"], p["kappa"], p["cap"], p["shrink"], log=log)


def run_study(prices, manifest, config=None, benchmark=None):
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    cfg["criteria"] = {**DEFAULT_CONFIG["criteria"], **cfg.get("criteria", {})}
    R = prices.pct_change().dropna()
    n = len(R)
    first = cfg["window"]
    if n < first + 4 * cfg["every"] * 2:
        raise ValueError(f"not enough history: {n} return days for a {first}-day estimation window and a validation + test period")
    val_end = first + int(cfg["validation_share"] * (n - first))
    cols = list(R.columns)

    # ---- validation: tune each family on the validation days only
    grid = []
    for fam, p in _families(cfg):
        r = walk_forward(R, _strategy(fam, p, cfg), cfg["window"], cfg["every"], cfg["cost_bps"], start=first, end=val_end)
        grid.append({"family": fam, **{k: v for k, v in p.items()}, "sharpe": _f(metrics(r["returns"])["sharpe"])})
    selected = {}
    for fam in ("mean_variance", "mv_costs", "extended", "cvar"):
        rows = [g for g in grid if g["family"] == fam]
        selected[fam] = max(rows, key=lambda g: -math.inf if g["sharpe"] is None else g["sharpe"])

    # ---- final test: every model once, same days
    runs, logs = {}, {}
    runs["equal_weight"] = walk_forward(R, equal_weight, cfg["window"], cfg["every"], cfg["cost_bps"], start=val_end)
    for fam in ("mean_variance", "mv_costs", "extended", "cvar"):
        logs[fam] = []
        runs[fam] = walk_forward(R, _strategy(fam, selected[fam], cfg, logs[fam]), cfg["window"], cfg["every"], cfg["cost_bps"], start=val_end)
    test_idx = runs["equal_weight"]["returns"].index
    models = {k: _model_stats(v, {"iterations_avg": _f(np.mean(logs[k])) if logs.get(k) else None}) for k, v in runs.items()}
    daily = {k: v["returns"] for k, v in runs.items()}
    if benchmark is not None:
        b = benchmark.pct_change().reindex(test_idx).fillna(0.0)
        daily["benchmark"] = b
        models["benchmark"] = {**{k: (v if k == "days" else _f(v)) for k, v in metrics(b).items()}, "avg_turnover": 0.0, "cost_total": 0.0, "rebalances": 0, "iterations_avg": None}
    else:
        models["benchmark"] = {**models["equal_weight"], "note": "no benchmark supplied"}
        daily["benchmark"] = daily["equal_weight"]

    ext, eq = runs["extended"], runs["equal_weight"]
    rb = ext["rebalance_weights"]
    cap = selected["extended"]["cap"]

    # ---- acceptance criteria (thresholds fixed in the config before the test)
    crit = cfg["criteria"]
    chunks = np.array_split(np.arange(len(test_idx)), 4)
    beat = sum(1 for c in chunks if len(c) and (1 + ext["returns"].iloc[c]).prod() > (1 + eq["returns"].iloc[c]).prod())
    t_last = R.index.get_loc(rb.index[-1])
    train_last = R.iloc[t_last - cfg["window"]:t_last]
    mu_l, S_l = _inputs(train_last, True)
    base = solve_portfolio(mu_l, S_l, selected["extended"]["lam"], w_prev=None, kappa=0.0, cap=cap)["weights"]
    rng = np.random.default_rng(cfg["seed"])
    sd = float(np.std(mu_l)) * cfg["perturbation_noise"]
    dist = [float(np.abs(solve_portfolio(mu_l + rng.normal(0, sd, len(mu_l)), S_l, selected["extended"]["lam"], cap=cap)["weights"] - base).sum())
            for _ in range(cfg["perturbations"])]
    instability = float(np.mean(dist))
    prev = ext["daily_weights"].shift(1)
    prev.iloc[0] = rb.iloc[0].values
    contrib = (prev * R.loc[test_idx]).sum()
    total = float(contrib.sum())
    top2 = float(contrib.sort_values(ascending=False).iloc[:2].sum() / total) if total > 0 else None
    wbar = rb.mean()
    eff_n = float(1 / np.sum(wbar.values ** 2))
    w_ok = bool((rb.values >= -1e-9).all() and np.abs(rb.sum(axis=1) - 1).max() < 1e-6 and rb.values.max() <= cap + 1e-6)
    again = walk_forward(R, _strategy("extended", selected["extended"], cfg), cfg["window"], cfg["every"], cfg["cost_bps"], start=val_end)
    repro = bool(np.allclose(again["returns"].values, ext["returns"].values, rtol=0, atol=1e-12))
    me, mq = models["extended"], models["equal_weight"]
    acceptance = [
        {"id": "net_return", "text": f"Net annual return of the extended model is above {crit['min_net_ann_return']:.0%}",
         "pass": me["ann_return"] is not None and me["ann_return"] > crit["min_net_ann_return"], "detail": f"{me['ann_return']:.2%} a year after costs"},
        {"id": "beats_equal_weight", "text": "Net Sharpe ratio beats equal weights on the same days",
         "pass": me["sharpe"] is not None and mq["sharpe"] is not None and me["sharpe"] > mq["sharpe"],
         "detail": f"extended {me['sharpe'] if me['sharpe'] is None else round(me['sharpe'], 2)} vs equal {mq['sharpe'] if mq['sharpe'] is None else round(mq['sharpe'], 2)}"},
        {"id": "constraints", "text": f"All rebalances are long-only, fully invested and within the {cap:.0%} cap", "pass": w_ok,
         "detail": f"max weight {rb.values.max():.1%}"},
        {"id": "subwindows", "text": f"Beats equal weights in at least {crit['min_subwindows_beating']:.0%} of 4 equal sub-periods of the test",
         "pass": beat / 4 >= crit["min_subwindows_beating"], "detail": f"{beat} of 4 sub-periods"},
        {"id": "stability", "text": f"Weights move by less than {crit['max_weight_instability']:.2f} (L1) when the expected returns are perturbed by {cfg['perturbation_noise']:.0%} of their spread",
         "pass": instability <= crit["max_weight_instability"], "detail": f"average L1 change {instability:.3f} over {cfg['perturbations']} draws"},
        {"id": "concentration", "text": f"Effective number of holdings is at least {crit['min_effective_n']:.0f} and the top two assets give at most {crit['max_top2_contribution']:.0%} of the return",
         "pass": eff_n >= crit["min_effective_n"] and top2 is not None and top2 <= crit["max_top2_contribution"],
         "detail": f"effective N {eff_n:.1f}; top-2 share {'n/a' if top2 is None else format(top2, '.0%')}"},
        {"id": "reproducible", "text": "Re-running with the same data and config gives identical returns", "pass": repro, "detail": f"data sha256 {manifest['sha256'][:12]}"},
    ]

    # ---- the six questions of the case study
    eq_gap = float(np.abs(wbar.values - 1 / len(cols)).sum())
    diag = solve_portfolio(mu_l, np.diag(np.diag(S_l)), selected["extended"]["lam"], cap=cap)["weights"]
    answers = [
        {"question": "How does the optimised portfolio differ from equal weights?", "answer": f"Average weights differ from 1/N by {eq_gap:.2f} (L1); largest average holding {wbar.idxmax()} at {wbar.max():.0%}."},
        {"question": "How much does the covariance matter for the allocation?", "answer": f"Ignoring correlations (diagonal covariance) moves the last allocation by {float(np.abs(diag - base).sum()):.2f} (L1)."},
        {"question": "How do turnover and costs change the result?", "answer": f"Costs paid: plain mean-variance {models['mean_variance']['cost_total']:.2%} of capital, with turnover penalty {models['mv_costs']['cost_total']:.2%}."},
        {"question": "What happens to the weights if the expected returns are perturbed?", "answer": f"They move by {instability:.2f} (L1) on average for a {cfg['perturbation_noise']:.0%} perturbation."},
        {"question": "Does CVaR reduce tail losses out of sample?", "answer": f"Daily 95% CVaR on the test: CVaR model {models['cvar']['cvar95']:.2%} vs mean-variance {models['mean_variance']['cvar95']:.2%}."},
        {"question": "Does the result depend on one or two companies?", "answer": "n/a: the extended model made no net profit." if top2 is None else f"The two largest contributors give {top2:.0%} of the extended model's return."},
    ]
    warnings = [f"{d['ticker']} was left out: {d['reason']}" for d in manifest.get("dropped", [])]
    lam_lo, lam_hi = min(cfg["lam_grid"]), max(cfg["lam_grid"])
    for fam, g in selected.items():
        grid_lams = cfg["cvar_lam_grid"] if fam == "cvar" else cfg["lam_grid"]
        if len(grid_lams) > 1 and g["lam"] in (min(grid_lams), max(grid_lams)):
            warnings.append(f"{fam}: lambda={g['lam']} sits at the edge of the grid {grid_lams}; the best value may lie outside it")
    wealth = {k: [float(x) for x in (1 + v).cumprod().values] for k, v in daily.items()}
    return {
        "notice": NOTICE, "config": cfg, "manifest": manifest, "tickers": cols,
        "periods": {"eval_start": R.index[first], "validation_end": R.index[val_end], "end": R.index[-1], "warmup_days": first,
                    "validation_days": val_end - first, "test_days": len(test_idx)},
        "validation": {"grid": grid, "selected": selected},
        "test": {"models": models},
        "acceptance": acceptance, "answers": answers, "warnings": warnings,
        "weights": {k: {c: float(w) for c, w in zip(cols, v["rebalance_weights"].iloc[-1].values)} for k, v in runs.items()},
        "average_weights": {c: float(w) for c, w in wbar.items()},
        "contributions": {c: float(x) for c, x in contrib.items()},
        "curves": {"dates": list(test_idx), "models": wealth},
        "daily_returns": {k: [float(x) for x in v.values] for k, v in daily.items()},
        "rebalances": {k: {str(d): {c: float(w) for c, w in zip(cols, row)} for d, row in zip(v["rebalance_weights"].index, v["rebalance_weights"].values)}
                       for k, v in runs.items()},
    }


def write_artifacts(folder, result):
    os.makedirs(folder, exist_ok=True)
    dump = lambda name, obj: open(os.path.join(folder, name), "w", encoding="utf-8").write(json.dumps(obj, indent=1, default=str))
    dump("config.json", result["config"])
    dump("data_manifest.json", result["manifest"])
    dump("metrics.json", {"validation": result["validation"], "test": result["test"], "acceptance": result["acceptance"]})
    dump("result.json", result)
    pd.DataFrame(result["weights"]).to_csv(os.path.join(folder, "weights.csv"))
    pd.DataFrame(result["daily_returns"], index=result["curves"]["dates"]).to_csv(os.path.join(folder, "returns.csv"))
    open(os.path.join(folder, "report.md"), "w", encoding="utf-8").write(report_markdown(result))
    return folder


def report_markdown(r):
    m, p = r["test"]["models"], r["periods"]
    L = [f"# Portfolio lab report", "", f"> {r['notice']}", "",
         f"Universe: {', '.join(r['tickers'])} · data {r['manifest']['start']} to {r['manifest']['end']} · sha256 `{r['manifest']['sha256'][:16]}`", "",
         f"Periods: warm-up {p['warmup_days']} days, validation {p['eval_start']} to {p['validation_end']} ({p['validation_days']} days), "
         f"final test {p['validation_end']} to {p['end']} ({p['test_days']} days).", "", "## Final test (net of costs)", "",
         "| model | annual return | volatility | Sharpe | max drawdown | CVaR 95% (day) | avg turnover | costs |", "|---|---|---|---|---|---|---|---|"]
    pct = lambda x: "-" if x is None else f"{x:.2%}"
    for k, v in m.items():
        L.append(f"| {k} | {pct(v['ann_return'])} | {pct(v['ann_vol'])} | {'-' if v['sharpe'] is None else round(v['sharpe'], 2)} | {pct(v['max_drawdown'])} | {pct(v['cvar95'])} | {pct(v['avg_turnover'])} | {pct(v['cost_total'])} |")
    if r.get("warnings"):
        L += ["", "## Warnings", ""] + [f"- {w}" for w in r["warnings"]]
    L += ["", "## Acceptance criteria (fixed before the test)", ""]
    L += [f"- {'PASS' if a['pass'] else 'FAIL'} - {a['text']} ({a['detail']})" for a in r["acceptance"]]
    L += ["", "## Selected on validation", ""] + [f"- {k}: lambda={v['lam']}" + (f", kappa={v['kappa']}" if "kappa" in v else "") + f", validation Sharpe {v['sharpe']}" for k, v in r["validation"]["selected"].items()]
    L += ["", "## Questions of the case study", ""] + [f"- **{a['question']}** {a['answer']}" for a in r["answers"]]
    L += ["", "## Latest weights", "", "| ticker | " + " | ".join(r["weights"].keys()) + " |", "|---|" + "---|" * len(r["weights"])]
    for t in r["tickers"]:
        L.append(f"| {t} | " + " | ".join(f"{r['weights'][k][t]:.1%}" for k in r["weights"]) + " |")
    return "\n".join(L) + "\n"
