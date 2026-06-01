"""Custom universe resolution.

A universe is the set of tickers the cross-sectional edges rank against.
resolve_universe accepts:
  - a named universe: "TECH", "SP500"
  - a comma list:     "AAPL,NVDA,MSFT"
  - a file path:      "@tickers.txt" (one ticker per line, # comments)
and intersects it with the tickers actually present in the data, keeping a
stable order. "SP500" means "everything available".
"""

# Big-cap tech names (those that appear in the bundled 2013-2018 panel).
NAMED_UNIVERSES = {
    "TECH": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "FB", "INTC",
        "CSCO", "ORCL", "IBM", "ADBE", "CRM", "QCOM", "TXN", "AVGO",
        "AMD", "MU", "ADI", "AMAT", "LRCX", "NFLX", "ADSK", "INTU",
    ],
}


def _read_file(path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line.upper())
    return out


def resolve_universe(spec, available):
    """Resolve a universe spec against the available tickers (stable order)."""
    available = list(available)
    avail_set = set(available)

    if spec.upper() == "SP500":
        return [t for t in available]
    if spec.upper() in NAMED_UNIVERSES:
        wanted = NAMED_UNIVERSES[spec.upper()]
    elif spec.startswith("@"):
        wanted = _read_file(spec[1:])
    else:
        wanted = [s.strip().upper() for s in spec.split(",") if s.strip()]

    resolved = [t for t in wanted if t in avail_set]
    if not resolved:
        raise ValueError(
            f"universe {spec!r} resolved to no available tickers "
            f"(have {len(available)})"
        )
    return resolved
