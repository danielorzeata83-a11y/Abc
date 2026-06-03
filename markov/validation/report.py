"""Agrega pasii A-E intr-un ValidationReport + redare text/CSV.
Fiecare iesire poarta disclaimerul. NU este consiliere de investitii.
"""

from dataclasses import dataclass

import numpy as np

from markov.validation import ic, ensemble, regime
from markov.validation.dataset import build_panel

DISCLAIMER = "NU este consiliere de investitii. Artefact de cercetare."


@dataclass
class ValidationReport:
    pooled_ic: dict
    families: list
    marginal: dict
    conditional: dict
    ensemble: dict
    horizons: tuple

    def render_text(self):
        L = [DISCLAIMER, "", "=== Validare indicatori (A->E) ===", ""]
        L.append("[A] Pooled IC (mean) pe orizonturi:")
        header = "  " + "indicator".ljust(16) + "".join(f"h={h}".rjust(9)
                                                         for h in self.horizons)
        L.append(header)
        for name in sorted(self.pooled_ic):
            row = "  " + name.ljust(16)
            for h in self.horizons:
                row += f"{self.pooled_ic[name][h]['mean']:+.3f}".rjust(9)
            L.append(row)
        L.append("")
        L.append("[B] Familii (corelate): " +
                 " | ".join("{" + ",".join(f) + "}" for f in self.families))
        L.append("")
        h0 = self.horizons[0]
        L.append(f"[C] IC marginal (h={h0}):")
        for name in sorted(self.marginal[h0]):
            L.append(f"  {name.ljust(16)}{self.marginal[h0][name]:+.3f}")
        L.append("")
        L.append("[D] IC conditionat pe regim hurst (primul indicator, h=%d):" % h0)
        for name in sorted(self.conditional):
            parts = " ".join(f"{r}={v:+.3f}" for r, v in self.conditional[name].items())
            L.append(f"  {name.ljust(16)}{parts}")
        L.append("")
        e = self.ensemble
        L.append("[E] Ansamblu equal-weight (walk-forward, pooled simboluri):")
        L.append(f"  net_return={e['net_return']:+.3f}  sharpe={e['sharpe']:+.2f}"
                 f"  p_value={e['p_value']:.3f}  n_days={e['n_days']}")
        L.append("")
        L.append(DISCLAIMER)
        return "\n".join(L)

    def to_csv(self, path):
        import csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["# " + DISCLAIMER])
            w.writerow(["indicator"] + [f"pooled_ic_h{h}" for h in self.horizons] +
                       [f"marginal_ic_h{self.horizons[0]}"])
            for name in sorted(self.pooled_ic):
                w.writerow([name] +
                           [self.pooled_ic[name][h]["mean"] for h in self.horizons] +
                           [self.marginal[self.horizons[0]].get(name, "")])


def run_validation(symbols, data_dir, indicators, horizon_tf="1day",
                   horizons=(1, 5, 21)):
    """Ruleaza A->E si intoarce un ValidationReport. Pooled pe simboluri."""
    panel = build_panel(symbols, data_dir, indicators, horizon_tf, horizons)
    names = list(indicators.keys())

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

    h0 = horizons[0]
    conditional = {}
    for name in names:
        accum = {}
        for s in symbols:
            labels = regime.hurst_regime(panel.close[s])
            cic = regime.conditional_ic(panel.features[s][name],
                                        panel.returns[s][h0], labels)
            for r, v in cic.items():
                accum.setdefault(r, []).append(v)
        conditional[name] = {r: ic.pooled_ic(vs)["mean"] for r, vs in accum.items()}

    metrics = []
    for s in symbols:
        metrics.append(ensemble.evaluate_ensemble(panel.features[s], panel.close[s]))
    ens = {k: float(np.mean([m[k] for m in metrics]))
           for k in ("net_return", "sharpe", "p_value", "n_days")}

    return ValidationReport(pooled, families, marginal, conditional, ens,
                            tuple(horizons))
