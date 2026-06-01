"""Trading-feasibility calculator.

Plain arithmetic to sanity-check a trading goal against position size and
costs -- the reality check behind "1000 trades a year for 5-10 EUR each".
No edge is assumed to exist; these are the constraints any edge must beat.
Not investment advice.
"""


def required_gross_move(position, target_net, roundtrip_cost):
    """Gross % move needed so that, after round-trip cost, you net target.

    net = position * (move - roundtrip_cost) = target_net
    -> move = target_net / position + roundtrip_cost
    """
    return target_net / position + roundtrip_cost


def expectancy_eur(position, edge_pct, roundtrip_cost):
    """Net EUR per trade given a gross per-trade edge and round-trip cost."""
    return position * (edge_pct - roundtrip_cost)


def capital_for_goal(annual_goal, trades, net_edge_pct):
    """Working capital per trade needed to reach an annual profit goal.

    annual_profit = trades * net_edge_pct * capital
    -> capital = goal / (trades * net_edge_pct)
    """
    denom = trades * net_edge_pct
    if denom <= 0:
        return float("inf")
    return annual_goal / denom
