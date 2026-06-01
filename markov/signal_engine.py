"""Universal signal contract: turn a target position into a buy/sell signal.

This module defines the output side of the SignalEngine (see
docs/SIGNAL_ENGINE_PLAN.md). A continuous target position in [-1, 1] is
mapped to a BUY/SELL/HOLD label with a confidence score, carrying the
per-edge breakdown, the mode used, and a mandatory disclaimer.
"""

from dataclasses import dataclass, field

DISCLAIMER = "Research artifact - not investment advice."


def classify_position(position, threshold=0.15):
    """Map a position in [-1, 1] to (label, confidence).

    |position| <= threshold -> HOLD; above -> BUY (long) / SELL (short).
    Confidence scales the magnitude from the threshold up to 1.0.
    """
    pos = max(-1.0, min(1.0, float(position)))
    mag = abs(pos)
    if mag <= threshold:
        label = "HOLD"
    elif pos > 0:
        label = "BUY"
    else:
        label = "SELL"
    # Confidence: 0 at the threshold, 1 at full position.
    denom = 1.0 - threshold
    confidence = max(0.0, min(1.0, (mag - threshold) / denom)) if denom > 0 else mag
    return label, confidence


@dataclass
class Signal:
    position: float
    label: str
    confidence: float
    mode: str
    breakdown: dict = field(default_factory=dict)
    ticker: str = ""
    asof: str = ""
    low_confidence: bool = False

    @classmethod
    def from_position(cls, position, breakdown, mode, threshold=0.15,
                      ticker="", asof=""):
        pos = max(-1.0, min(1.0, float(position)))
        label, confidence = classify_position(pos, threshold)
        return cls(
            position=pos, label=label, confidence=confidence, mode=mode,
            breakdown=dict(breakdown), ticker=ticker, asof=asof,
            low_confidence=(mode == "time-series"),
        )

    def render(self):
        head = f"{self.ticker or 'ASSET'} - {self.asof or 'latest'}"
        flag = "  [LOW CONFIDENCE: single-asset]" if self.low_confidence else ""
        lines = [
            head,
            f"  Mode: {self.mode}",
            f"  Signal: {self.label} (position {self.position:+.2f}, "
            f"confidence {self.confidence:.2f}){flag}",
        ]
        if self.breakdown:
            parts = " | ".join(f"{k} {v:+.2f}" for k, v in self.breakdown.items())
            lines.append(f"  Breakdown: {parts}")
        lines.append(f"  {DISCLAIMER}")
        return "\n".join(lines)
