"""Agrega pasii A-E intr-un ValidationReport + redare text/CSV.
Fiecare iesire poarta disclaimerul. NU este consiliere de investitii.
"""

from dataclasses import dataclass, field

import numpy as np

from markov.validation import ic, ensemble, regime
from markov.validation.dataset import build_panel
from markov.validation.vol_forecast import pooled_vol_forecast, VOL_TEAM

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."


@dataclass
class ValidationReport:
    pooled_ic: dict
    families: list
    marginal: dict        # {h: {indicator: ic_marginal}}
    conditional: dict     # {indicator: {h: {regim: ic}}}
    ensemble: dict        # ansamblu equal-weight neconditionat (directional)
    horizons: tuple
    target: str = "return"
    ensemble_regime: dict = field(default_factory=dict)  # ansamblu gated pe meanrev
    ensemble_ic: dict = field(default_factory=dict)      # ansamblu sign-aware (ponderi ∝ IC)
    vol_forecast: dict = field(default_factory=dict)     # [F] doar pentru target='vol'

    def render_text(self):
        tgt = "volatilitate" if self.target == "vol" else "randament"
        L = [DISCLAIMER, "", "=== Validare indicatori (A->E) ===",
             f"(tinta: {tgt} forward)", ""]
        L.append("[A] Pooled IC (mean) pe orizonturi:")
        L.append("  " + "indicator".ljust(16) +
                 "".join(f"h={h}".rjust(9) for h in self.horizons))
        for name in sorted(self.pooled_ic):
            row = "  " + name.ljust(16)
            for h in self.horizons:
                row += f"{self.pooled_ic[name][h]['mean']:+.3f}".rjust(9)
            L.append(row)
        L.append("")
        L.append("[B] Familii (corelate): " +
                 " | ".join("{" + ",".join(f) + "}" for f in self.families))
        L.append("")
        L.append("[C] IC marginal (peste restul echipei) pe orizonturi:")
        L.append("  " + "indicator".ljust(16) +
                 "".join(f"h={h}".rjust(9) for h in self.horizons))
        for name in sorted(self.marginal[self.horizons[0]]):
            row = "  " + name.ljust(16)
            for h in self.horizons:
                val = self.marginal[h].get(name, float("nan"))
                row += f"{val:+.3f}".rjust(9)
            L.append(row)
        L.append("")
        L.append("[D] IC conditionat pe regim Hurst (meanrev | trend) pe orizonturi:")
        for name in sorted(self.conditional):
            L.append(f"  {name}")
            for h in self.horizons:
                regs = self.conditional[name].get(h, {})
                parts = "  ".join(f"{r}={regs[r]:+.3f}" for r in sorted(regs))
                L.append(f"    h={h}: {parts}")
        L.append("")
        L.append("[E] Ansamblu equal-weight (walk-forward, pooled simboluri):")
        e = self.ensemble
        L.append(f"  neconditionat : net_return={e['net_return']:+.3f}"
                 f"  sharpe={e['sharpe']:+.2f}  p_value={e['p_value']:.3f}"
                 f"  n_days={e['n_days']:.0f}")
        if self.ensemble_regime:
            g = self.ensemble_regime
            L.append(f"  gated meanrev : net_return={g['net_return']:+.3f}"
                     f"  sharpe={g['sharpe']:+.2f}  p_value={g['p_value']:.3f}"
                     f"  n_days={g['n_days']:.0f}")
        if self.ensemble_ic:
            w = self.ensemble_ic
            L.append(f"  sign-aware IC : net_return={w['net_return']:+.3f}"
                     f"  sharpe={w['sharpe']:+.2f}  p_value={w['p_value']:.3f}"
                     f"  n_days={w['n_days']:.0f}")
        if self.vol_forecast:
            h = max(self.horizons)
            L.append("")
            L.append(f"[F] Prognoza vol realizat (cauzal, IC@h={h}, parcimonie):")
            L.append("  " + "set indicatori".ljust(22) + "IC".rjust(8) +
                     "IC_hold".rjust(9) + "IC_orient".rjust(11) + "n".rjust(9))
            for label in self.vol_forecast:
                v = self.vol_forecast[label]
                L.append("  " + label.ljust(22) +
                         f"{v['ic']:+.3f}".rjust(8) +
                         f"{v['ic_holdout']:+.3f}".rjust(9) +
                         f"{v.get('ic_oriented', float('nan')):+.3f}".rjust(11) +
                         f"{v['n']}".rjust(9))
        L.append("")
        L.append(DISCLAIMER)
        return "\n".join(L)

    def to_csv(self, path):
        import csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["# " + DISCLAIMER + f" tinta={self.target}"])
            w.writerow(["indicator"] +
                       [f"pooled_ic_h{h}" for h in self.horizons] +
                       [f"marginal_ic_h{h}" for h in self.horizons])
            for name in sorted(self.pooled_ic):
                w.writerow([name] +
                           [self.pooled_ic[name][h]["mean"] for h in self.horizons] +
                           [self.marginal[h].get(name, "") for h in self.horizons])


def run_validation(symbols, data_dir, indicators, horizon_tf="1day",
                   horizons=(1, 5, 21), target="return"):
    """Ruleaza A->E si intoarce un ValidationReport. Pooled pe simboluri.

    target='return' (directie) sau 'vol' (volatilitate realizata forward). A/C/D
    masoara IC fata de tinta aleasa; E ramane mereu directional (edge tranzactionabil).
    """
    if not horizons:
        raise ValueError("horizons trebuie sa contina cel putin un orizont")
    panel = build_panel(symbols, data_dir, indicators, horizon_tf, horizons, target)
    names = list(indicators.keys())
    labels_by_sym = {s: regime.hurst_regime(panel.close[s]) for s in symbols}

    pooled = {}
    for name in names:
        pooled[name] = {}
        for h in horizons:
            ics = [ic.spearman_ic(panel.features[s][name], panel.returns[s][h])
                   for s in symbols]
            pooled[name][h] = ic.pooled_ic(ics)

    concat = {name: np.concatenate([panel.features[s][name] for s in symbols])
              for name in names}
    cnames, corr = ic.correlation_matrix(concat)
    families = ic.cluster_families(cnames, corr, thr=0.7)

    marginal = {}
    for h in horizons:
        fwd = np.concatenate([panel.returns[s][h] for s in symbols])
        marginal[h] = ic.marginal_ic(concat, fwd)

    conditional = {}
    for name in names:
        conditional[name] = {}
        for h in horizons:
            accum = {}
            for s in symbols:
                cic = regime.conditional_ic(panel.features[s][name],
                                            panel.returns[s][h], labels_by_sym[s])
                for r, v in cic.items():
                    accum.setdefault(r, []).append(v)
            conditional[name][h] = {r: ic.pooled_ic(vs)["mean"]
                                    for r, vs in accum.items()}

    uncond, gated, signaware = [], [], []
    for s in symbols:
        uncond.append(ensemble.evaluate_ensemble(panel.features[s], panel.close[s]))
        gated.append(ensemble.evaluate_ensemble(
            panel.features[s], panel.close[s],
            regime_labels=labels_by_sym[s], active_regime="meanrev"))
        signaware.append(ensemble.evaluate_ensemble(
            panel.features[s], panel.close[s], weighting="ic"))
    _avg = lambda ms: {k: float(np.mean([m[k] for m in ms]))
                       for k in ("net_return", "sharpe", "p_value", "n_days")}
    ens, ens_mr, ens_ic = _avg(uncond), _avg(gated), _avg(signaware)

    # [F] Prognoza vol realizat (doar cand tinta e volatilitatea): compara setul
    # complet cu echipa ortogonala (3) si cu un singur estimator -> parcimonie.
    vol_fc = {}
    if target == "vol":
        h_vol = max(horizons)
        sets = {f"ALL ({len(names)})": names,
                "TEAM (3 ortogonal)": list(VOL_TEAM),
                "SINGLE realized_var": ["realized_var"]}
        for label, ns in sets.items():
            vol_fc[label] = pooled_vol_forecast(panel.features, panel.close,
                                                ns, horizon=h_vol)

    return ValidationReport(pooled, families, marginal, conditional, ens,
                            tuple(horizons), target=target, ensemble_regime=ens_mr,
                            ensemble_ic=ens_ic, vol_forecast=vol_fc)
