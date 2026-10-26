import pytest

from markov.data_providers import DataUnavailable
from sensa.politicians import parse_index, parse_ptr

# Text as extracted from real House Periodic Transaction Reports (names and figures from the public filings).
FIELDS = """P        T           R     
Clerk of the House of Representatives • Legislative Resource Center • B81 Cannon Building • Washington, DC 20515
F     I          
Name: Cleo Fields
Status: Member
State/District: LA06
T           
ID Owner Asset Transaction
Type
Date Notification
Date
Amount Cap.
Gains >
$200?
NVIDIA Corporation - Common Stock
(NVDA) [ST]
P 10/01/2026 10/01/2026 $1,001 - $15,000
F      S     : New
S          O : Morgan Stanley - E*TRADE #2
NVIDIA Corporation - Common Stock
(NVDA) [ST]
P 10/01/2026 10/01/2026 $1,001 - $15,000
F      S     : New
S          O : Morgan Stanley - E*TRADE IRA
Taiwan Semiconductor
Manufacturing Company Ltd. (TSM)
[ST]
P 10/09/2026 10/09/2026 $1,001 - $15,000
F      S     : New
S          O : Morgan Stanley - E*TRADE #2
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
I          V       D      
Morgan Stanley - E*TRADE #2
I       P      O        
 Yes  No
C
I CERTIFY that the statements I have made on the attached Periodic Transaction Report are true.
Digitally Signed: Cleo Fields , 10/22/2026
"""

YAKYM = """Name: Hon. Rudy C. Yakym III
Status: Member
State/District: IN02
Gains >
$200?
Treasury Bill (6-Week, Matures
12/3/2026) [GS]
P 10/20/2026 10/20/2026 $15,001 -
$50,000
F      S     : New
S          O : Schwab (formerly TD Ameritrade)
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""

MIXED = """Name: Hon. Jane Q. Public
Status: Member
State/District: CA48
$200?
SP Apple Inc. - Common Stock (AAPL)
[ST]
S (partial) 09/30/2026 10/05/2026 $100,001 - $250,000 N
F      S     : New
S          O : Joint brokerage
D          : Sold part of the position
JT Some Private Fund LP [OT]
E 09/01/2026 09/02/2026 Over $1,000,000
F      S     : New
Microsoft Corporation - Common Stock (MSFT) [ST]
P 09/15/2026 09/16/2026 $1,001 -
$15,000
F      S     : New
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""


def test_parse_header_and_three_purchases_of_a_real_report():
    r = parse_ptr(FIELDS)
    assert (r["member"], r["state"], r["district"]) == ("Cleo Fields", "LA", "06")
    assert [(t["ticker"], t["type"], t["amount_low"], t["amount_high"]) for t in r["trades"]] == [
        ("NVDA", "purchase", 1001, 15000), ("NVDA", "purchase", 1001, 15000), ("TSM", "purchase", 1001, 15000)]
    t = r["trades"][2]
    assert t["asset"] == "Taiwan Semiconductor Manufacturing Company Ltd." and t["asset_type"] == "ST"
    assert t["date"] == "2026-10-09" and t["notified"] == "2026-10-09" and t["account"] == "Morgan Stanley - E*TRADE #2"
    assert r["trades"][1]["account"] == "Morgan Stanley - E*TRADE IRA"


def test_amount_split_over_two_lines_and_honorific_removed():
    r = parse_ptr(YAKYM)
    assert r["member"] == "Rudy C. Yakym III" and r["state"] == "IN" and r["district"] == "02"
    t = r["trades"][0]
    assert (t["asset"], t["ticker"], t["asset_type"]) == ("Treasury Bill (6-Week, Matures 12/3/2026)", None, "GS")
    assert (t["amount_low"], t["amount_high"]) == (15001, 50000) and t["date"] == "2026-10-20"


def test_owner_codes_partial_sales_exchanges_open_ended_amounts_and_trailing_flags():
    r = parse_ptr(MIXED)
    a, b, c = r["trades"]
    assert (a["owner"], a["type"], a["ticker"], a["amount_low"], a["amount_high"]) == ("SP", "partial sale", "AAPL", 100001, 250000)
    assert a["account"] == "Joint brokerage" and a["date"] == "2026-09-30" and a["notified"] == "2026-10-05"
    assert (b["owner"], b["type"], b["asset_type"], b["amount_low"], b["amount_high"]) == ("JT", "exchange", "OT", 1000000, None)
    assert (c["owner"], c["ticker"], c["amount_low"], c["amount_high"]) == ("", "MSFT", 1001, 15000)


def test_estimated_value_is_the_range_midpoint_or_the_floor_for_open_ended_ranges():
    a, b, c = parse_ptr(MIXED)["trades"]
    assert a["value"] == (100001 + 250000) / 2 and b["value"] == 1000000.0 and c["value"] == (1001 + 15000) / 2


def test_a_report_without_readable_transactions_is_an_error_not_an_empty_success():
    with pytest.raises(DataUnavailable, match="no transactions"):
        parse_ptr("Name: Nobody\nState/District: TX01\n(scanned image, no text)")
    with pytest.raises(DataUnavailable, match="no text"):
        parse_ptr("   \n")


def test_parse_index_lists_only_periodic_transaction_reports_newest_first():
    xml = """<?xml version="1.0"?><FinancialDisclosure>
<Member><Last>Aaron</Last><First>Richard</First><FilingType>W</FilingType><StateDst>MI04</StateDst><Year>2026</Year><FilingDate>4/15/2026</FilingDate><DocID>8068</DocID></Member>
<Member><Last>Fields</Last><First>Cleo</First><FilingType>P</FilingType><StateDst>LA06</StateDst><Year>2026</Year><FilingDate>10/22/2026</FilingDate><DocID>20035669</DocID></Member>
<Member><Last>Yakym</Last><First>Rudy C.</First><FilingType>P</FilingType><StateDst>IN02</StateDst><Year>2026</Year><FilingDate>10/9/2026</FilingDate><DocID>20035000</DocID></Member>
</FinancialDisclosure>"""
    docs = parse_index(xml)
    assert [(d["doc_id"], d["filed"], d["name"], d["state_dst"]) for d in docs] == [
        ("20035669", "2026-10-22", "Cleo Fields", "LA06"), ("20035000", "2026-10-09", "Rudy C. Yakym", "IN02")]


def test_parse_index_refuses_xml_with_entities():
    with pytest.raises(DataUnavailable):
        parse_index('<!DOCTYPE x [<!ENTITY a "b">]><FinancialDisclosure/>')


import json
import zipfile
from datetime import date

from sensa.politicians import PoliticiansService

INDEX = """<?xml version="1.0"?><FinancialDisclosure>
<Member><Last>Fields</Last><First>Cleo</First><FilingType>P</FilingType><StateDst>LA06</StateDst><Year>2026</Year><FilingDate>10/22/2026</FilingDate><DocID>111</DocID></Member>
<Member><Last>Public</Last><First>Jane Q.</First><FilingType>P</FilingType><StateDst>CA48</StateDst><Year>2026</Year><FilingDate>10/05/2026</FilingDate><DocID>222</DocID></Member>
<Member><Last>Scanned</Last><First>Sam</First><FilingType>P</FilingType><StateDst>TX01</StateDst><Year>2026</Year><FilingDate>10/01/2026</FilingDate><DocID>333</DocID></Member>
<Member><Last>Annual</Last><First>Ann</First><FilingType>A</FilingType><StateDst>NY01</StateDst><Year>2026</Year><FilingDate>5/15/2026</FilingDate><DocID>444</DocID></Member>
</FinancialDisclosure>"""
TEXTS = {"111": FIELDS, "222": MIXED, "333": "   "}


def make_service(tmp_path, log=None, extract_log=None, today=date(2026, 10, 26)):
    log = [] if log is None else log

    def download(url, dest):
        log.append(url)
        if url.endswith("2026FD.zip"):
            with zipfile.ZipFile(dest, "w") as z:
                z.writestr("2026FD.xml", INDEX)
        else:
            with open(dest, "wb") as fh:
                fh.write(url.rsplit("/", 1)[1][:-4].encode())          # the "pdf" content is its doc id

    def extract(path):
        doc = open(path, "rb").read().decode()
        if extract_log is not None:
            extract_log.append(doc)
        return TEXTS[doc]
    return PoliticiansService(str(tmp_path), download, extract=extract, today=lambda: today, retry_days=1), log


def test_check_downloads_the_index_then_each_report_once_and_aggregates(tmp_path):
    svc, log = make_service(tmp_path)
    r = svc.check()
    assert r["new"] == 2 and r["failed"] == 1 and r["trades"] == 6
    pdfs = [u for u in log if u.endswith(".pdf")]
    assert sorted(pdfs) == sorted(f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/{d}.pdf" for d in ("111", "222", "333"))
    assert svc.check() is None                              # nothing new: no more PDFs, failure not retried yet
    assert len([u for u in log if u.endswith(".pdf")]) == 3


def test_failed_reports_are_retried_after_the_retry_window(tmp_path):
    svc, log = make_service(tmp_path)
    svc.check()
    later, _ = make_service(tmp_path, log=log, today=date(2026, 10, 28))
    later.check()
    assert [u for u in log if u.endswith("333.pdf")].__len__() == 2


def test_overview_lists_latest_trades_and_ranks_tickers_and_members(tmp_path):
    svc, _ = make_service(tmp_path)
    svc.check()
    o = svc.overview(days=90)
    assert o["as_of"] == "2026-10-22" and o["reports"] == 2 and o["trades"] == 6
    assert o["latest"][0]["date"] >= o["latest"][-1]["date"] and o["latest"][0]["member"] in ("Cleo Fields", "Jane Q. Public")
    nvda = next(t for t in o["top_bought"] if t["ticker"] == "NVDA")
    assert nvda["members"] == 1 and nvda["trades"] == 2 and nvda["value"] == 2 * (1001 + 15000) / 2
    assert [t["ticker"] for t in o["top_sold"]] == ["AAPL"]
    assert o["members"][0]["member"] == "Cleo Fields" and o["members"][0]["trades"] == 3


def test_overview_filters_by_ticker_member_side_and_window(tmp_path):
    svc, _ = make_service(tmp_path)
    svc.check()
    assert {t["ticker"] for t in svc.overview(ticker="tsm")["latest"]} == {"TSM"}
    assert {t["member"] for t in svc.overview(member="jane")["latest"]} == {"Jane Q. Public"}
    assert all(t["type"] in ("sale", "partial sale") for t in svc.overview(side="sell")["latest"])
    assert svc.overview(days=14)["trades"] == 1           # as of 2026-10-22: only the TSM purchase of October 9 is that recent


def test_overview_before_any_build_says_to_press_update(tmp_path):
    svc, _ = make_service(tmp_path)
    with pytest.raises(DataUnavailable, match="Update"):
        svc.overview()


def test_status_reports_counts_after_a_build(tmp_path):
    svc, _ = make_service(tmp_path)
    svc.start()
    svc.wait(10)
    st = svc.status()
    assert st["state"] == "done" and st["reports"] == 2 and st["failed"] == 1 and st["built_at"]


INLINE = """Name: Hon. Debbie Dingell
Status: Member
State/District: MI06
Gains >
$200?
FHLMC 30 YR GOLD RQ0128 [GS] P 07/14/2026 07/20/2026 $15,001 -
$50,000
F      S     : New
S          O : Morgan Stanley Smith Barney LLC IRA
D          : Mortgage Backed Security; Due Date 06/01/2056; Coupon 5.50% Fixed
SP Apple Inc. - Common Stock (AAPL) [ST] S 07/15/2026 07/20/2026 $1,001 - $15,000
F      S     : New
Alphabet Inc. - Class A
(GOOGL) [ST] P 07/16/2026 07/20/2026 $15,001 - $50,000 Y
F      S     : New
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""


def test_asset_and_transaction_on_the_same_line_are_both_read():
    r = parse_ptr(INLINE)
    assert r["member"] == "Debbie Dingell" and len(r["trades"]) == 3
    a, b, c = r["trades"]
    assert (a["asset"], a["asset_type"], a["type"], a["amount_low"], a["amount_high"], a["date"]) == (
        "FHLMC 30 YR GOLD RQ0128", "GS", "purchase", 15001, 50000, "2026-07-14")
    assert a["account"] == "Morgan Stanley Smith Barney LLC IRA"
    assert (b["owner"], b["ticker"], b["type"], b["amount_low"], b["amount_high"]) == ("SP", "AAPL", "sale", 1001, 15000)
    assert (c["asset"], c["ticker"], c["type"], c["amount_high"]) == ("Alphabet Inc. - Class A", "GOOGL", "purchase", 50000)


def test_a_company_name_ending_in_a_type_letter_is_not_mistaken_for_a_transaction():
    r = parse_ptr("Name: X\nState/District: TX01\n$200?\nBerkshire Hathaway Class S\nInc. (BRK/B) [ST]\nP 01/02/2026 01/03/2026 $1,001 - $15,000\n")
    assert [t["asset"] for t in r["trades"]] == ["Berkshire Hathaway Class S Inc. (BRK/B)"] or r["trades"][0]["asset_type"] == "ST"
    assert len(r["trades"]) == 1


EXACT = """Name: Hon. Debbie Wasserman Schultz
State/District: FL25
$200?
Ichor Holdings - Ordinary Shares
(ICHR) [ST]
S 06/17/2026 07/14/2026 $2,722.50
F      S     : New
D          : Sale from Individual Retirement Account
SP U.S. Treasury Note due 2/28/2029
[GS]
P 12/15/2025 12/16/2025 Spouse/DC Over
$1,000,000
F      S     : New
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""


def test_exact_dollar_amounts_and_spouse_over_a_million_are_read():
    r = parse_ptr(EXACT)
    a, b = r["trades"]
    assert (a["ticker"], a["type"], a["amount_low"], a["amount_high"], a["value"]) == ("ICHR", "sale", 2722.5, None, 2722.5)
    assert (b["owner"], b["asset"], b["type"], b["amount_low"], b["amount_high"]) == ("SP", "U.S. Treasury Note due 2/28/2029", "purchase", 1000000, None)


def test_a_trade_dated_after_its_own_report_is_flagged_and_kept_out_of_the_rankings(tmp_path):
    texts = {"111": FIELDS.replace("10/09/2026 10/09/2026", "12/26/2026 10/09/2026"), "222": MIXED, "333": "   "}
    svc, _ = make_service(tmp_path)
    original = svc.extract

    def extract(path):
        doc = open(path, "rb").read().decode()
        return texts[doc]
    svc.extract = extract
    svc.check()
    o = svc.overview(days=90)
    assert o["suspect"] == 1                                              # the TSM purchase "made" two months after filing
    assert all(t["date"] <= t["filed"] for t in o["latest"])
    assert "TSM" not in {t["ticker"] for t in o["top_bought"]} and o["trades"] == 5


NULS = ("Name: Hon. Michael Rulli\nState/District: OH06\nGains >\n$200?\nAlphabet Inc. - Class C Capital Stock\n(GOOG) [ST]\n"
        "S 10/16/2026 10/16/2026 $50,001 -\n$100,000\nF\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New\n"
        "S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: Merrill Lynch Roth IRA\nWesBanco, Inc. - Common Stock\n(WSBC) [ST]\n"
        "S 10/16/2026 10/16/2026 $1,001 - $15,000\nF\x00\x00\x00\x00\x00 S\x00\x00\x00\x00\x00: New\n"
        "S\x00\x00\x00\x00\x00\x00\x00\x00\x00 O\x00: Merrill Lynch Roth IRA\n"
        "* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.\n")


def test_null_characters_standing_in_for_spaces_do_not_leak_into_asset_names():
    goog, wsbc = parse_ptr(NULS)["trades"]
    assert (goog["asset"], goog["ticker"], goog["account"]) == ("Alphabet Inc. - Class C Capital Stock", "GOOG", "Merrill Lynch Roth IRA")
    assert (wsbc["asset"], wsbc["ticker"], wsbc["amount_low"], wsbc["amount_high"]) == ("WesBanco, Inc. - Common Stock", "WSBC", 1001, 15000)
    assert "\x00" not in goog["asset"] + wsbc["account"]


MULTIPAGE = """Name: Hon. Many Trades
State/District: OK01
ID Owner Asset Transaction
Type
Date Notification
Date
Amount Cap.
Gains >
$200?
Verizon Communications Inc. Common Stock
(VZ) [ST]
P 07/14/2026 07/20/2026 $1,001 - $15,000
F      S     : New
Filing ID #20019182
ID Owner Asset Transaction
Type
Date Notification
Date
Amount Cap.
Gains >
$200?
AbbVie Inc. Common Stock
(ABBV) [ST]
S 07/15/2026 07/20/2026 $1,001 - $15,000
F      S     : New
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""


def test_a_table_header_repeated_on_every_page_does_not_leak_into_assets():
    vz, abbv = parse_ptr(MULTIPAGE)["trades"]
    assert (vz["asset"], vz["ticker"]) == ("Verizon Communications Inc. Common Stock", "VZ")
    assert (abbv["asset"], abbv["ticker"], abbv["type"]) == ("AbbVie Inc. Common Stock", "ABBV", "sale")


WRAPPED_DESC = """Name: Hon. Wrap Desc
State/District: TX01
$200?
Pinterest, Inc. Class A Common Stock
(PINS) [ST]
S 07/14/2026 07/20/2026 $1,001 - $15,000
F      S     : New
D          : I have no role in, nor am informed of, specific investment decisions prior to their execution.
Accordingly, this transaction was planned and executed by a financial advisor and not by me or my staff
under any circumstances whatsoever as stated.
US Treasury Note 01/31/27 [GS]
P 07/15/2026 07/20/2026 $15,001 - $50,000
F      S     : New
* For the complete list of asset type abbreviations, please visit https://fd.house.gov/reference/asset-type-codes.aspx.
"""


def test_a_multi_line_description_does_not_swallow_the_next_assets_name():
    a, b = parse_ptr(WRAPPED_DESC)["trades"]
    assert a["asset"] == "Pinterest, Inc. Class A Common Stock" and a["ticker"] == "PINS"
    assert b["asset"] == "US Treasury Note 01/31/27" and b["asset_type"] == "GS" and len(b["asset"]) < 60
