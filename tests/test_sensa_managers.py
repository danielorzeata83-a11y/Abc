from sensa.managers import browse, letter_of


def m(cik, name, aum, entries=10, quarter="Q2 2026"):
    return {"cik": cik, "name": name, "state": "NY", "aum": float(aum), "entries": entries,
            "accession": "a" + cik, "filed": "2026-08-14", "quarter": quarter}


ALL = [m("1", "a16z Capital Management, L.L.C.", 14e9, 19), m("2", "AA Financial Advisors, LLC", 840e6, 251),
       m("3", "Berkshire Hathaway Inc", 300e9, 40), m("4", "123 Capital Partners", 5e6, 3),
       m("5", "(Parentheses) Fund", 1e6, 1), m("6", "aaa Wealth", 2e6, 7)]


def test_letter_of_uses_the_first_letter_and_groups_digits_and_symbols_under_zero():
    assert letter_of("Berkshire Hathaway") == "b" and letter_of("a16z Capital") == "a"
    assert letter_of("  (Parentheses) Fund") == "p"
    assert letter_of("123 Capital") == "0" and letter_of("!!!") == "0" and letter_of("") == "0"


def test_browse_a_letter_gives_totals_sorted_case_insensitively():
    r = browse(ALL, "a")
    assert [x["name"] for x in r["rows"]] == ["a16z Capital Management, L.L.C.", "AA Financial Advisors, LLC", "aaa Wealth"]
    assert r["total"] == 3 and r["aum"] == 14e9 + 840e6 + 2e6
    assert r["avg_entries"] == round((19 + 251 + 7) / 3)


def test_browse_digits_bucket_and_paging():
    assert [x["cik"] for x in browse(ALL, "0")["rows"]] == ["4"]
    page = browse(ALL, "a", offset=1, limit=1)
    assert page["total"] == 3 and [x["cik"] for x in page["rows"]] == ["2"]


def test_browse_search_ignores_the_letter_and_matches_name_parts():
    r = browse(ALL, None, query="capital")
    assert {x["cik"] for x in r["rows"]} == {"1", "4"} and r["total"] == 2


def test_browse_rejects_bad_letters_and_clamps_paging():
    assert browse(ALL, "ab")["rows"] == [] and browse(ALL, "#")["rows"] == []
    assert len(browse(ALL, "a", offset=-5, limit=10 ** 6)["rows"]) <= 200
