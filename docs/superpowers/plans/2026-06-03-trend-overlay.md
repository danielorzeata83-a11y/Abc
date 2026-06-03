# Trend Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an educational NVDA chart that overlays the hindsight bottom against real-time SMA 50/200 golden/death crosses and a walk-forward HMM regime, quantifying the lag cost, whipsaws, and drawdown of waiting for confirmation.

**Architecture:** Pure causal primitives in `markov/trend_overlay.py`; a sibling `hmm_walk_forward_states()` in the existing walk-forward module for the per-day regime label; an SVG renderer in `markov/trend_chart.py` reusing `svg_chart` helpers; a thin `trend_cli.py` that wires it into a self-contained HTML file.

**Tech Stack:** Python, numpy, pandas, hmmlearn (already a dependency), pytest. No new dependencies.

**Commit footer:** every commit message ends with a blank line then `https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn`. Author must be `Claude <noreply@anthropic.com>`.

---

## File Structure

- Create: `markov/trend_overlay.py` — pure, causal primitives (sma, crossovers, hindsight bottom, lag cost, whipsaw count, signal drawdown).
- Create: `markov/trend_chart.py` — `render_trend_svg()` SVG renderer.
- Create: `trend_cli.py` — CLI: load ticker → compute layers → write HTML.
- Modify: `markov/hmm_walkforward.py` — add `hmm_walk_forward_states()`.
- Test: `tests/test_trend_overlay.py`, `tests/test_trend_chart.py`, `tests/test_hmm_walkforward_states.py`, `tests/test_trend_cli.py`.

---

## Task 1: SMA primitive

**Files:**
- Create: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for the hindsight-vs-real-time trend overlay primitives."""

import numpy as np
import pytest

from markov.trend_overlay import sma


def test_sma_trailing_average_with_nan_warmup():
    prices = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = sma(prices, window=3)
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert out[2] == pytest.approx(2.0)   # mean(1,2,3)
    assert out[3] == pytest.approx(3.0)   # mean(2,3,4)
    assert out[4] == pytest.approx(4.0)   # mean(3,4,5)


def test_sma_rejects_nonpositive_window():
    with pytest.raises(ValueError):
        sma([1.0, 2.0], window=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'sma'`.

- [ ] **Step 3: Write minimal implementation**

Create `markov/trend_overlay.py`:

```python
"""Hindsight vs real-time trend overlay primitives.

Pure, causal functions for the educational NVDA chart: simple moving averages,
golden/death crossovers (using only past data), the hindsight major bottom, and
the lesson metrics (lag cost of waiting for confirmation, whipsaw count, and the
drawdown the signal sat through). Nothing here is investment advice.
"""

from collections import namedtuple

import numpy as np

Crossover = namedtuple("Crossover", ["idx", "kind"])  # kind: "golden" | "death"


def sma(prices, window):
    """Simple trailing moving average; first `window-1` entries are NaN.

    Causal: out[i] uses only prices[i-window+1 .. i] (no look-ahead).
    """
    if window <= 0:
        raise ValueError("window must be positive")
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    out = np.full(n, np.nan)
    if n < window:
        return out
    c = np.cumsum(np.insert(prices, 0, 0.0))   # c[k] = sum(prices[:k])
    out[window - 1:] = (c[window:] - c[:-window]) / window
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): causal SMA primitive

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 2: Golden/death crossovers

**Files:**
- Modify: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trend_overlay.py`:

```python
from markov.trend_overlay import sma_crossovers, Crossover


def test_crossover_detects_single_golden_cross():
    # fast<slow then fast>slow -> exactly one golden cross, no death.
    # downtrend for the first half, uptrend for the second half.
    prices = list(np.linspace(100, 50, 30)) + list(np.linspace(50, 200, 30))
    xs = sma_crossovers(prices, fast=5, slow=20)
    kinds = [c.kind for c in xs]
    assert "golden" in kinds
    assert "death" not in kinds
    # golden cross happens during the recovery (second half)
    assert all(c.idx > 25 for c in xs if c.kind == "golden")


def test_crossover_none_on_monotonic_series():
    prices = list(np.linspace(10, 100, 60))   # always rising, fast stays above
    assert sma_crossovers(prices, fast=5, slow=20) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'sma_crossovers'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/trend_overlay.py`:

```python
def sma_crossovers(prices, fast=50, slow=200):
    """Golden (fast SMA crosses above slow) / death (below) crossovers.

    Causal: both SMAs use only past data. Returns Crossover(idx, kind) at the
    day the sign of (fast - slow) flips. Days where either SMA is NaN are skipped.
    """
    f = sma(prices, fast)
    s = sma(prices, slow)
    diff = f - s
    out = []
    prev = None
    for i in range(len(diff)):
        if not np.isfinite(diff[i]):
            continue
        above = diff[i] > 0
        if prev is not None and above != prev:
            out.append(Crossover(i, "golden" if above else "death"))
        prev = above
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): golden/death crossover detection

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 3: Hindsight bottom

**Files:**
- Modify: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trend_overlay.py`:

```python
from markov.trend_overlay import hindsight_bottom


def test_hindsight_bottom_is_global_min_index():
    prices = [100.0, 80.0, 50.0, 70.0, 120.0]   # V-shape, min at idx 2
    assert hindsight_bottom(prices) == 2


def test_hindsight_bottom_rejects_empty():
    with pytest.raises(ValueError):
        hindsight_bottom([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'hindsight_bottom'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/trend_overlay.py`:

```python
def hindsight_bottom(prices):
    """Index of the major bottom (global minimum).

    The clean, parameter-free 'from here up it was bull' marker -- only
    knowable in hindsight. That is the whole point of the overlay.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) == 0:
        raise ValueError("empty price series")
    return int(np.nanargmin(prices))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): hindsight bottom marker

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 4: Lag cost

**Files:**
- Modify: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trend_overlay.py`:

```python
from markov.trend_overlay import lag_cost


def test_lag_cost_is_return_from_bottom_to_confirmation():
    prices = [100.0, 50.0, 60.0, 75.0]   # bottom idx 1 (=50), confirm idx 3 (=75)
    assert lag_cost(prices, bottom_idx=1, confirm_idx=3) == pytest.approx(0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'lag_cost'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/trend_overlay.py`:

```python
def lag_cost(prices, bottom_idx, confirm_idx):
    """Return between the real bottom and the day the signal confirmed.

    Positive = how much you would have missed waiting for the golden cross.
    """
    prices = np.asarray(prices, dtype=float)
    return prices[confirm_idx] / prices[bottom_idx] - 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): lag-cost metric

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 5: Whipsaw count

**Files:**
- Modify: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trend_overlay.py`:

```python
from markov.trend_overlay import count_whipsaws


def test_count_whipsaws_counts_quick_reversals():
    xs = [Crossover(10, "golden"), Crossover(15, "death"),   # 5 days  -> whipsaw
          Crossover(100, "golden"), Crossover(160, "death")] # 60 days -> ok
    assert count_whipsaws(xs, min_hold_days=30) == 1


def test_count_whipsaws_zero_when_all_held_long():
    xs = [Crossover(10, "golden"), Crossover(100, "death")]
    assert count_whipsaws(xs, min_hold_days=30) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'count_whipsaws'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/trend_overlay.py`:

```python
def count_whipsaws(crossovers, min_hold_days):
    """Count crossovers reversed within `min_hold_days` of the prior one.

    These are the false signals that flip-flop and chew up a follower.
    """
    n = 0
    for a, b in zip(crossovers, crossovers[1:]):
        if b.idx - a.idx < min_hold_days:
            n += 1
    return n
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): whipsaw counter

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 6: Signal drawdown

**Files:**
- Modify: `markov/trend_overlay.py`
- Test: `tests/test_trend_overlay.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_trend_overlay.py`:

```python
from markov.trend_overlay import signal_drawdown


def test_signal_drawdown_worst_peak_to_trough():
    # entered at idx 0; rises to 120 then falls to 90 -> -25% from the 120 peak
    prices = [100.0, 120.0, 90.0, 110.0]
    assert signal_drawdown(prices, entry_idx=0, exit_idx=3) == pytest.approx(-0.25)


def test_signal_drawdown_zero_when_monotonic_up():
    prices = [100.0, 110.0, 130.0]
    assert signal_drawdown(prices, entry_idx=0, exit_idx=2) == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: FAIL with `ImportError: cannot import name 'signal_drawdown'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/trend_overlay.py`:

```python
def signal_drawdown(prices, entry_idx, exit_idx):
    """Worst peak-to-trough drawdown between entry and exit (inclusive).

    Returns a non-positive number (e.g. -0.25 = -25%) -- the pain you sat
    through after the signal put you in.
    """
    prices = np.asarray(prices, dtype=float)
    seg = prices[entry_idx:exit_idx + 1]
    if len(seg) == 0:
        return 0.0
    peak = np.maximum.accumulate(seg)
    return float((seg / peak - 1.0).min())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_overlay.py -q`
Expected: PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_overlay.py tests/test_trend_overlay.py
git commit -m "feat(trend): signal drawdown metric

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 7: Walk-forward HMM regime labels

**Files:**
- Modify: `markov/hmm_walkforward.py` (add function at end of file)
- Test: `tests/test_hmm_walkforward_states.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_hmm_walkforward_states.py`:

```python
"""Walk-forward HMM per-day regime labels (no look-ahead)."""

import numpy as np

from markov.states import State
from markov.hmm_walkforward import hmm_walk_forward_states


def test_states_length_and_no_lookahead():
    prices = np.linspace(100.0, 200.0, 60)
    seen = []

    def fake_fit(past):
        seen.append(len(past))                 # records how much history each refit saw

        def labeller(arr):
            return State.BULL if arr[-1] > 0 else State.BEAR
        return labeller, None

    states, start = hmm_walk_forward_states(
        prices, warmup=10, refit_every=5, _fit_fn=fake_fit)

    assert start == 10
    assert len(states) == len(prices) - 1 - 10     # one per return after warmup
    assert all(isinstance(s, State) for s in states)
    # every refit only ever saw past returns (strictly < total returns = 59)
    assert max(seen) < len(prices) - 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hmm_walkforward_states.py -q`
Expected: FAIL with `ImportError: cannot import name 'hmm_walk_forward_states'`.

- [ ] **Step 3: Write minimal implementation**

Append to `markov/hmm_walkforward.py` (after `hmm_walk_forward_positions`):

```python
def hmm_walk_forward_states(prices, warmup=250, refit_every=60,
                            seed=None, _fit_fn=None):
    """Walk-forward regime label per day (no look-ahead).

    Mirrors `hmm_walk_forward_positions` but collects today's State instead of
    a position. Returns (states, start_index) where states[k] is the regime for
    price-day (start_index + k). Refits on past returns only, every
    `refit_every` days.
    """
    prices = np.asarray(prices, dtype=float)
    returns = daily_returns(prices)
    n = len(returns)
    if warmup >= n - 1:
        raise ValueError(f"warmup={warmup} too large for {n} returns")

    fit_fn = _fit_fn if _fit_fn is not None else _default_fit

    states = []
    labeller = None
    for t in range(warmup, n):
        if (t - warmup) % refit_every == 0 or labeller is None:
            if _fit_fn is not None:
                labeller, _ = fit_fn(returns[:t])
            else:
                labeller, _ = fit_fn(returns[:t], seed=seed)
        states.append(labeller(returns[:t]))   # past-only labelling
    return states, warmup
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hmm_walkforward_states.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/hmm_walkforward.py tests/test_hmm_walkforward_states.py
git commit -m "feat(hmm): walk-forward per-day regime labels

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 8: SVG renderer

**Files:**
- Create: `markov/trend_chart.py`
- Test: `tests/test_trend_chart.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_trend_chart.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_chart.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'markov.trend_chart'`.

- [ ] **Step 3: Write minimal implementation**

Create `markov/trend_chart.py`:

```python
"""SVG renderer for the hindsight-vs-real-time trend overlay.

Draws four layers on one chart: the walk-forward HMM regime as background
bands, the price + SMA 50/200 lines, golden/death cross markers, the hindsight
bottom, and a lesson box (lag cost, whipsaws, drawdown). Visualisation only --
nothing here is investment advice.
"""

import numpy as np

from markov.svg_chart import scale_to_px, _x_px, _GREEN, _RED, _GREY
from markov.signal_engine import DISCLAIMER
from markov.states import State

_PRICE, _FAST, _SLOW = "#0969da", "#9a6700", "#8250df"
_BAND = {State.BULL: "#e6f4ea", State.SIDEWAYS: "#f0f0f0", State.BEAR: "#fde8e8"}


def _runs(states):
    """Compress a per-day state list into (start, end_exclusive, state) runs."""
    runs = []
    i, n = 0, len(states)
    while i < n:
        j = i
        while j < n and states[j] == states[i]:
            j += 1
        runs.append((i, j, states[i]))
        i = j
    return runs


def render_trend_svg(dates, close, sma_fast, sma_slow, crossovers,
                     states, state_start, bottom_idx, stats,
                     width=960, height=420, pad=52):
    close = np.asarray(close, dtype=float)
    n = len(close)
    left, right, top, bottom = pad, width - pad, 16, height - pad
    lo, hi = float(np.nanmin(close)), float(np.nanmax(close))
    span = (hi - lo) or 1.0
    vmin, vmax = lo - 0.05 * span, hi + 0.05 * span

    def X(i):
        return round(_x_px(i, n, left, right), 1)

    def Y(v):
        return round(scale_to_px(v, vmin, vmax, top, bottom), 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
             f'height="{height}" viewBox="0 0 {width} {height}" '
             f'font-family="system-ui,sans-serif" font-size="11">']

    # 1) regime background bands (walk-forward HMM, aligned at state_start)
    for a, b, st in _runs(states):
        x0 = X(state_start + a)
        x1 = X(state_start + b - 1)
        parts.append(f'<rect x="{x0}" y="{top}" width="{max(x1 - x0, 1)}" '
                     f'height="{bottom - top}" fill="{_BAND.get(st, "#ffffff")}"/>')

    # axis baseline + min/max labels
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" '
                 f'stroke="{_GREY}" stroke-width="1"/>')
    parts.append(f'<text x="{left}" y="{Y(vmax) - 4}" fill="{_GREY}">{vmax:.0f}</text>')
    parts.append(f'<text x="{left}" y="{bottom + 14}" fill="{_GREY}">{vmin:.0f}</text>')

    def _poly(series, color, dash=""):
        pts = " ".join(f"{X(i)},{Y(series[i])}"
                       for i in range(len(series)) if np.isfinite(series[i]))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        return (f'<polyline points="{pts}" fill="none" stroke="{color}" '
                f'stroke-width="1.5"{d}/>')

    # 2) price + SMA lines
    parts.append(_poly(close, _PRICE))
    parts.append(_poly(np.asarray(sma_fast, dtype=float), _FAST, "5 3"))
    parts.append(_poly(np.asarray(sma_slow, dtype=float), _SLOW, "5 3"))

    # 3) hindsight bottom marker
    bx = X(bottom_idx)
    parts.append(f'<line x1="{bx}" y1="{top}" x2="{bx}" y2="{bottom}" '
                 f'stroke="{_GREEN}" stroke-width="1.5" stroke-dasharray="2 2"/>')
    parts.append(f'<text x="{bx + 3}" y="{top + 12}" fill="{_GREEN}">'
                 f'fund real {close[bottom_idx]:.0f} '
                 f'({str(dates[bottom_idx])[:10]})</text>')

    # 4) crossover markers
    for c in crossovers:
        cx, cy = X(c.idx), Y(close[c.idx])
        col = _GREEN if c.kind == "golden" else _RED
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{col}">'
                     f'<title>{c.kind.upper()} CROSS {str(dates[c.idx])[:10]} '
                     f'@ {close[c.idx]:.2f}</title></circle>')

    # lesson + drawdown box
    lines = [
        f"Golden {stats['fast']}/{stats['slow']} vs fundul real (hindsight):",
        f"cost intarziere: {stats['lag_cost'] * 100:+.0f}% pana la confirmare",
        f"semnale false (whipsaw): {stats['whipsaws']}",
        f"drawdown indurat dupa intrare: {stats['max_drawdown'] * 100:+.0f}%",
        DISCLAIMER,
    ]
    bx0, by0 = left + 6, top + 6
    parts.append(f'<rect x="{bx0}" y="{by0}" width="360" '
                 f'height="{14 * len(lines) + 12}" fill="#ffffff" '
                 f'fill-opacity="0.85" stroke="{_GREY}"/>')
    for k, ln in enumerate(lines):
        parts.append(f'<text x="{bx0 + 8}" y="{by0 + 18 + 14 * k}" '
                     f'fill="#24292f">{ln}</text>')

    parts.append("</svg>")
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_chart.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add markov/trend_chart.py tests/test_trend_chart.py
git commit -m "feat(trend): SVG renderer for the overlay

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 9: CLI wiring

**Files:**
- Create: `trend_cli.py`
- Test: `tests/test_trend_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_trend_cli.py`:

```python
"""The CLI's ticker loader returns a sorted, ticker-filtered close series."""

import numpy as np
import pandas as pd

from trend_cli import load_ticker


def test_load_ticker_filters_and_sorts(tmp_path):
    csv = tmp_path / "panel.csv"
    pd.DataFrame({
        "date": ["2015-01-03", "2015-01-01", "2015-01-02", "2015-01-01"],
        "close": [12.0, 10.0, 11.0, 999.0],
        "Name": ["NVDA", "NVDA", "NVDA", "AAPL"],
    }).to_csv(csv, index=False)

    dates, close = load_ticker(str(csv), "NVDA")

    assert list(close) == [10.0, 11.0, 12.0]          # sorted by date, NVDA only
    assert list(dates) == ["2015-01-01", "2015-01-02", "2015-01-03"]
    assert isinstance(close, np.ndarray)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_trend_cli.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'trend_cli'`.

- [ ] **Step 3: Write minimal implementation**

Create `trend_cli.py`:

```python
"""Render an educational hindsight-vs-real-time trend chart for one ticker.

Overlays SMA fast/slow golden/death crosses and a walk-forward HMM regime on the
price, marks the hindsight bottom, and shows the 'cost of waiting' plus the
drawdown the signal sat through. Visualisation only -- NOT investment advice.

    python trend_cli.py --ticker NVDA --data data/sp500.csv
"""

import argparse
import os as _os

import numpy as np
import pandas as pd

from markov.trend_overlay import (sma, sma_crossovers, hindsight_bottom,
                                  lag_cost, count_whipsaws, signal_drawdown)
from markov.hmm_walkforward import hmm_walk_forward_states
from markov.trend_chart import render_trend_svg


def _DATA(name):
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", name)


def load_ticker(path, ticker):
    """Return (dates, close) for `ticker`, sorted by date."""
    raw = pd.read_csv(path)
    df = raw[raw["Name"] == ticker].sort_values("date")
    if df.empty:
        raise SystemExit(f"{ticker} not found in {path}")
    return df["date"].to_numpy(), df["close"].to_numpy(dtype=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="NVDA")
    ap.add_argument("--data", default=_DATA("sp500.csv"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--fast", type=int, default=50)
    ap.add_argument("--slow", type=int, default=200)
    args = ap.parse_args()

    dates, close = load_ticker(args.data, args.ticker)

    fast = sma(close, args.fast)
    slow = sma(close, args.slow)
    crossovers = sma_crossovers(close, args.fast, args.slow)
    bottom = hindsight_bottom(close)
    states, start = hmm_walk_forward_states(close)

    goldens = [c for c in crossovers if c.kind == "golden"]
    first_golden = goldens[0].idx if goldens else bottom
    entry = next((c.idx for c in goldens if c.idx >= bottom), first_golden)
    deaths = [c.idx for c in crossovers if c.kind == "death" and c.idx > entry]
    exit_idx = deaths[0] if deaths else len(close) - 1

    stats = {
        "lag_cost": lag_cost(close, bottom, first_golden),
        "whipsaws": count_whipsaws(crossovers, min_hold_days=30),
        "max_drawdown": signal_drawdown(close, entry, exit_idx),
        "fast": args.fast, "slow": args.slow,
    }

    svg = render_trend_svg(dates, close, fast, slow, crossovers,
                           states, start, bottom, stats)
    out = args.out or f"trend_{args.ticker}.html"
    html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{args.ticker} trend overlay</title></head><body>"
            f"<h1>{args.ticker}: hindsight vs real-time</h1>{svg}</body></html>")
    with open(out, "w") as f:
        f.write(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_trend_cli.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add trend_cli.py tests/test_trend_cli.py
git commit -m "feat(trend): CLI wiring -> self-contained HTML

https://claude.ai/code/session_01Kyh13tRkmoXXqpcL1tYkqn"
```

---

## Task 10: Full-suite + real-data smoke verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite**

Run: `python -m pytest -q`
Expected: PASS (all tests green, including the new trend tests).

- [ ] **Step 2: Real-data smoke run on NVDA**

Run: `python trend_cli.py --ticker NVDA --data data/sp500.csv --out /tmp/trend_NVDA.html`
Expected: prints `Wrote /tmp/trend_NVDA.html` with no traceback (HMM walk-forward over ~1250 days may take 20-60s).

- [ ] **Step 3: Sanity-check the output**

Run: `grep -c "<polyline" /tmp/trend_NVDA.html && grep -o "cost intarziere: [+-][0-9]*%" /tmp/trend_NVDA.html`
Expected: `3` polylines and a printed lag-cost line (e.g. `cost intarziere: +35%`).

- [ ] **Step 4: Push the branch**

```bash
for i in 1 2 3 4; do git push -u origin claude/upbeat-fermi-L3dat && break || sleep $((2**i)); done
```

---

## Self-Review Notes

- **Spec coverage:** hindsight bottom (T3), SMA + golden/death (T1,T2), walk-forward HMM bands (T7,T8), lag cost (T4), whipsaws (T5), drawdown (T6), renderer with all layers + disclaimer (T8), CLI (T9). All spec sections mapped.
- **Type consistency:** `Crossover(idx, kind)` namedtuple used identically across T2/T5/T8/T9; `hmm_walk_forward_states -> (states, start)` matches T8/T9 usage; `render_trend_svg(... state_start ...)` signature matches the T9 call (positional `start`).
- **No placeholders:** every code/test step contains full code; commands have expected output.
