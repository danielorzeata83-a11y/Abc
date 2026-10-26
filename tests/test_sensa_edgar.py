import json

import pytest

from markov.data_providers import DataUnavailable
from sensa.edgar import Edgar, parse_form4

FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerName>Acme Corp</issuerName><issuerTradingSymbol>acme</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>0</isDirector><isOfficer>1</isOfficer>
      <officerTitle>CFO</officerTitle></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-10-22</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionPricePerShare><value>12.5</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-10-22</value></transactionDate>
      <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>50</value></transactionShares>
        <transactionPricePerShare><value>0</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""


def test_parse_form4_keeps_only_open_market_buys_and_sells():
    trades = parse_form4(FORM4)
    assert trades == [{"symbol": "ACME", "issuer": "Acme Corp", "owner": "Doe Jane",
                       "role": "CFO", "date": "2026-10-22", "side": "buy",
                       "shares": 1000.0, "price": 12.5, "value": 12500.0}]


def test_parse_form4_labels_sale_and_director_role():
    xml = (FORM4.replace("<code>", "").replace("<transactionCode>P<", "<transactionCode>S<")
           .replace("<isDirector>0", "<isDirector>1").replace("<isOfficer>1", "<isOfficer>0")
           .replace("<officerTitle>CFO</officerTitle>", ""))
    t = parse_form4(xml)[0]
    assert t["side"] == "sell" and t["role"] == "Director"


def test_parse_form4_rejects_dtd_entities():
    with pytest.raises(DataUnavailable):
        parse_form4('<!DOCTYPE x [<!ENTITY a "b">]><ownershipDocument/>')


DIR = "https://www.sec.gov/Archives/edgar/data/111/000111111126000001"
ATOM = f"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>4 - Doe Jane (0000111) (Reporting)</title>
<link rel="alternate" href="{DIR}/0001111111-26-000001-index.htm"/></entry>
<entry><title>4 - Grant Only (0000222) (Reporting)</title>
<link rel="alternate" href="https://www.sec.gov/Archives/edgar/data/222/000222222226000002/0002222222-26-000002-index.htm"/></entry>
</feed>"""
GRANT_ONLY = FORM4.replace("<transactionCode>P<", "<transactionCode>A<")


class FakeSec:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers=None):
        self.calls.append((url, headers or {}))
        if "browse-edgar" in url:
            return ATOM
        if url.endswith("/index.json"):
            return json.dumps({"directory": {"item": [{"name": "primary_doc.xsl"},
                                                       {"name": "form4.xml"}]}})
        if "000111111126000001/form4.xml" in url:
            return FORM4
        return GRANT_ONLY


def test_edgar_recent_returns_open_market_trades_from_latest_filings():
    f = FakeSec()
    trades = Edgar("me@example.com", fetch=f).recent(limit=10)
    assert [t["symbol"] for t in trades] == ["ACME"]       # grant-only filing contributes nothing
    assert all("me@example.com" in h.get("User-Agent", "") for _, h in f.calls)


def test_edgar_symbol_filter():
    e = Edgar("me@example.com", fetch=FakeSec())
    assert e.recent(symbol="zzz") == []
    assert len(e.recent(symbol="acme")) == 1


def test_edgar_requires_contact():
    with pytest.raises(DataUnavailable, match="SEC_CONTACT"):
        Edgar("", fetch=FakeSec()).recent()
