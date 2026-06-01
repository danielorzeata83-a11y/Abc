"""Vol-managed market timing edge (Moreira & Muir 2017).

Scale exposure to the market inversely with recent realised volatility,
so the portfolio de-risks into turbulence and adds risk when calm. This
raises the market's risk-adjusted return and reduces drawdowns. It is a
market-DIRECTIONAL edge (it carries beta), unlike the market-neutral
cross-sectional alphas, and so should be combined as a timing sleeve.

Thin wrapper over the tested vol_target_returns engine.
"""

import numpy as np

from markov.voltarget import vol_target_returns


def vol_managed_market(market_returns, target_vol=0.15, window=20,
                       max_leverage=3.0, return_leverage=False):
    """Vol-managed market return stream (and optionally the leverage path)."""
    scaled, lev = vol_target_returns(
        np.asarray(market_returns, dtype=float),
        target_vol=target_vol, window=window, max_leverage=max_leverage,
    )
    if return_leverage:
        return scaled, lev
    return scaled
