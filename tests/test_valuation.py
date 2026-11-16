import pytest

from sensa.valuation import Valuation

HEAD = "Symbol,Name,Sector,Price,Price/Earnings,Dividend Yield,Earnings/Share,52 Week Low,52 Week High,Market Cap,EBITDA,Price/Sales,Price/Book,SEC Filings\n"


def row(sym, sector, pe, pb, ps, ebitda, cap=1e10, dy=0.02):
    return f"{sym},{sym} Inc,{sector},100,{pe},{dy},5,1,2,{cap},{ebitda},{ps},{pb},x\n"


@pytest.fixture
def val(tmp_path):
    rows = [row("A1", "Tech", 10, 1, 1, 4e9), row("A2", "Tech", 20, 2, 2, 3e9), row("A3", "Tech", 30, 3, 3, 2e9),
            row("A4", "Tech", 40, 4, 4, 1e9), row("A5", "Tech", 50, 5, 5, 5e8), row("B1", "Oil", 8, 1, 1, 1e9)]
    p = tmp_path / "f.csv"
    p.write_text(HEAD + "".join(rows))
    return Valuation(str(p))


def test_screen_counts_quadrants_and_sorts_cheapest_first(val):
    r = val.screen()
    assert r["total"] == 6 and sum(r["counts"].values()) == 6
    vp = [x["value_pct"] for x in r["rows"] if x["value_pct"] is not None]
    assert vp == sorted(vp, reverse=True)
    top = r["rows"][0]
    assert set(top) >= {"ticker", "sector", "pe", "value_pct", "quality_pct", "quadrant", "ebitda_margin_pct"}


def test_screen_filters_by_quadrant_and_limits(val):
    q = val.screen()["rows"][0]["quadrant"]
    r = val.screen(quadrant=q, limit=1)
    assert len(r["rows"]) == 1 and r["rows"][0]["quadrant"] == q


def test_thermometer_ranks_the_cheapest_in_its_sector_high(val):
    cheap, rich = val.thermometer("A1"), val.thermometer("A5")
    assert cheap["score"] > 66 and cheap["label"] == "cheap"
    assert rich["score"] < 33 and rich["label"] == "expensive"
    assert cheap["sector"] == "Tech" and {r["name"] for r in cheap["ratios"]} == {"P/E", "P/B", "P/S"}


def test_thermometer_uses_the_live_pe_when_given(val):
    base = val.thermometer("A3")
    live = val.thermometer("A3", live_pe=5)
    pe = lambda t: next(r for r in t["ratios"] if r["name"] == "P/E")
    assert pe(live)["value"] == 5 and pe(live)["cheaper_than_sector_pct"] > pe(base)["cheaper_than_sector_pct"]


def test_thermometer_for_an_unknown_ticker_with_a_live_pe_compares_with_the_market(val):
    t = val.thermometer("ZZZ", live_pe=9)
    assert t["in_snapshot"] is False and t["sector"] is None and t["score"] > 66


def test_thermometer_for_an_unknown_ticker_without_data_is_none(val):
    assert val.thermometer("ZZZ") is None


def test_missing_file_gives_an_empty_screen(tmp_path):
    v = Valuation(str(tmp_path / "none.csv"))
    assert v.screen()["total"] == 0 and v.thermometer("A1") is None
