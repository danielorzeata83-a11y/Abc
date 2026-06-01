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
    # Liquid crypto assets (Coin Metrics symbols, lowercase).
    "CRYPTO": [
        "btc", "eth", "ltc", "xrp", "bch", "ada", "doge", "sol",
        "etc", "xlm", "link", "uni", "aave", "mkr",
    ],
    # Wider crypto cross-section (49 Coin Metrics coins) for proper ranking.
    "CRYPTO_WIDE": [
        "btc", "eth", "ltc", "xrp", "bch", "ada", "doge", "sol", "etc",
        "xlm", "link", "uni", "aave", "mkr", "xmr", "eos", "trx", "neo",
        "dash", "zec", "xtz", "atom", "algo", "vet", "bsv", "miota", "dcr",
        "bnb", "matic", "avax", "dot", "fil", "theta", "egld", "xem", "hbar",
        "ksm", "waves", "comp", "yfi", "sushi", "snx", "crv", "bat", "zrx",
        "omg", "knc", "ren", "lrc",
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


def candidate_tickers(spec):
    """Explicit tickers for a spec without needing the data, or None.

    Named universes, comma lists and @files yield an explicit list; "SP500"
    (meaning "everything available") returns None since it can't be
    enumerated without the data.
    """
    if spec.upper() == "SP500":
        return None
    if spec.upper() in NAMED_UNIVERSES:
        return list(NAMED_UNIVERSES[spec.upper()])
    if spec.startswith("@"):
        return _read_file(spec[1:])
    return [s.strip() for s in spec.split(",") if s.strip()]


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
