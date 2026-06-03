"""The trend overlay SVG must contain all four layers + the disclaimer."""

import numpy as np

from markov.states import State
from markov.trend_overlay import sma, sma_crossovers, Crossover
from markov.trend_chart import render_trend_svg, DISCLAIMER


def _inputs():
    close = np.array(list(np.linspace(100, 50, 30)) + list(np.linspace(50, 200, 30)))
    dates = [f"2015-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(len(close))]
    fast = sma(close, 5)
    slow = sma(close, 20)
    crossovers = sma_crossovers(close, 5, 20) or [Crossover(40, "golden")]
    states = [State.BEAR] * 20 + [State.BULL] * (len(close) - 1 - 20)
    stats = {"lag_cost": 0.42, "whipsaws": 1, "max_drawdown": -0.18,
             "fast": 5, "slow": 20}
    return dates, close, fast, slow, crossovers, states, stats


def test_render_contains_all_layers_and_disclaimer():
    dates, close, fast, slow, crossovers, states, stats = _inputs()
    svg = render_trend_svg(dates, close, fast, slow, crossovers,
                           states, state_start=1, bottom_idx=29, stats=stats)
    assert svg.startswith("<svg")
    assert svg.count("<polyline") >= 3          # price + 2 SMAs
    assert "<rect" in svg                         # regime bands + lesson box
    assert "CROSS" in svg                         # crossover marker title
    assert "fund real" in svg                     # hindsight bottom label
    assert DISCLAIMER in svg
