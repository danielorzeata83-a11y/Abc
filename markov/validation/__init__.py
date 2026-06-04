"""Motor de validare a indicatorilor (agnostic). NU este consiliere de investitii."""

from markov.validation import tier1, tier2

# Sursa unica de adevar pentru tier-urile de indicatori time-series (folosita de
# validate_cli si validate_universe_cli). TIER 2b (cross-sectional) e separat.
TIERS = {
    "tier1": tier1.INDICATORS,
    "tier2": tier2.INDICATORS,
    "all": {**tier1.INDICATORS, **tier2.INDICATORS},
}
