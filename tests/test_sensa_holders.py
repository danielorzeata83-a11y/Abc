import sqlite3
import zipfile

import pytest

from markov.data_providers import DataUnavailable
from sensa.holders import build_holders_db, holders_for_cusip, cusips_by_issuer

SUB_H = ["ACCESSION_NUMBER", "FILING_DATE", "SUBMISSIONTYPE", "CIK", "PERIODOFREPORT"]
COV_H = ["ACCESSION_NUMBER", "ISAMENDMENT", "AMENDMENTTYPE", "FILINGMANAGER_NAME", "FILINGMANAGER_STATEORCOUNTRY", "REPORTTYPE"]
SUM_H = ["ACCESSION_NUMBER", "TABLEENTRYTOTAL", "TABLEVALUETOTAL"]
INF_H = ["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "VALUE", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL"]


def make_zip(path, period_iso, funds):
    """funds: {cik: (accession, name, aum, [(issuer, cusip, value, shares[, putcall[, type]])])}"""
    mon = {"03": "MAR", "06": "JUN", "09": "SEP", "12": "DEC"}[period_iso[5:7]]
    per = f"{period_iso[8:]}-{mon}-{period_iso[:4]}"
    sub, cov, summ, inf = ([] for _ in range(4))
    for cik, (acc, name, aum, rows) in funds.items():
        sub.append([acc, "14-AUG-2026", "13F-HR", cik, per])
        cov.append([acc, "", "", name, "NY", "13F HOLDINGS REPORT"])
        summ.append([acc, str(len(rows)), str(aum)])
        for r in rows:
            issuer, cusip, value, shares = r[:4]
            inf.append([acc, issuer, cusip, str(value), str(shares), r[5] if len(r) > 5 else "SH", r[4] if len(r) > 4 else ""])
    t = lambda head, rows: "\t".join(head) + "\n" + "".join("\t".join(x) + "\n" for x in rows)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("SUBMISSION.tsv", t(SUB_H, sub))
        z.writestr("COVERPAGE.tsv", t(COV_H, cov))
        z.writestr("SUMMARYPAGE.tsv", t(SUM_H, summ))
        z.writestr("INFOTABLE.tsv", t(INF_H, inf))


@pytest.fixture
def db(tmp_path):
    cur, prev = str(tmp_path / "q2.zip"), str(tmp_path / "q1.zip")
    make_zip(cur, "2026-06-30", {
        "0000000001": ("A1", "Alpha Fund", 9000, [("PEOPLES BANCORP INC", "709789101", 100, 10),
                                                    ("PEOPLES BANCORP INC", "709789101", 50, 5),            # second line, same filer
                                                    ("PEOPLES BANCORP INC", "709789101", 7, 700, "Call"),   # call option on the same stock
                                                    ("PEOPLES BANCORP INC", "709789101", 3, 300, "Put"),
                                                    ("SOME BOND", "111111111", 9, 9, "", "PRN")]),
        "0000000002": ("A2", "Beta Capital", 500, [("PEOPLES BANCORP INC", "709789101", 400, 40), ("OTHER CO", "222222222", 5, 5)]),
        "0000000003": ("A3", "Gamma LLC", 300, [("PEOPLES BANCORP INC", "709789101", 60, 6)]),
        "0000000004": ("A4", "Delta Exited", 200, [("OTHER CO", "222222222", 20, 2)])})        # filed this quarter, sold PEBO
    make_zip(prev, "2026-03-31", {
        "0000000001": ("B1", "Alpha Fund", 8000, [("PEOPLES BANCORP INC", "709789101", 90, 12)]),
        "0000000002": ("B2", "Beta Capital", 600, [("PEOPLES BANCORP INC", "709789101", 380, 40)]),
        "0000000004": ("B4", "Delta Exited", 200, [("PEOPLES BANCORP INC", "709789101", 20, 2)])})
    path = str(tmp_path / "holders.db")
    build_holders_db(cur, prev, "2026-06-30", "2026-03-31", path)
    return path


def test_build_creates_one_row_per_filer_security_and_kind_with_lines_merged(db):
    con = sqlite3.connect(db)
    rows = con.execute("SELECT cik,kind,shares,value FROM h WHERE q=0 AND cusip='709789101' ORDER BY cik,kind").fetchall()
    assert rows == [("0000000001", "CALL", 700.0, 7.0), ("0000000001", "PUT", 300.0, 3.0), ("0000000001", "SH", 15.0, 150.0),
                    ("0000000002", "SH", 40.0, 400.0), ("0000000003", "SH", 6.0, 60.0)]
    assert con.execute("SELECT count(*) FROM h WHERE cusip='111111111'").fetchone()[0] == 0          # bond principal is not a share holding
    assert con.execute("SELECT value FROM meta WHERE key='period'").fetchone()[0] == "2026-06-30"


def test_holders_for_cusip_merges_current_previous_options_and_filer_details(db):
    h = {r["cik"]: r for r in holders_for_cusip(db, "709789101")}
    assert set(h) == {"0000000001", "0000000002", "0000000003"}                  # the filer that sold out is not a current holder
    a = h["0000000001"]
    assert (a["name"], a["accession"], a["shares"], a["stock_value"], a["prev_shares"], a["prev_stock_value"]) == ("Alpha Fund", "A1", 15.0, 150.0, 12.0, 90.0)
    assert (a["call_value"], a["put_value"], a["call_shares"], a["put_shares"], a["option_positions"]) == (7.0, 3.0, 700.0, 300.0, 2)
    assert h["0000000002"]["prev_shares"] == 40.0 and h["0000000003"]["prev_shares"] is None      # Gamma is new this quarter
    assert h["0000000003"]["filed"] == "2026-08-14" and h["0000000003"]["aum"] == 300.0


def test_holders_for_unknown_cusip_is_empty_and_sold_out_count_is_available(db):
    assert holders_for_cusip(db, "000000000") == []
    from sensa.holders import sold_out_count
    assert sold_out_count(db, "709789101") == 1                                        # Delta Exited held it last quarter only


def test_cusips_by_issuer_prefix_ranks_candidates_by_value(db):
    assert cusips_by_issuer(db, "PEOPLES BANCORP") == [("709789101", "PEOPLES BANCORP INC")]
    assert cusips_by_issuer(db, "NOPE") == []
    assert cusips_by_issuer(db, "peoples%") == []                                      # LIKE wildcards in user input are not honoured


def test_a_failed_build_never_replaces_a_good_database(tmp_path, db):
    bad = str(tmp_path / "bad.zip")
    open(bad, "wb").write(b"not a zip")
    with pytest.raises(DataUnavailable):
        build_holders_db(bad, bad, "2026-06-30", "2026-03-31", db)
    assert sqlite3.connect(db).execute("SELECT count(*) FROM h").fetchone()[0] > 0


def test_holders_db_missing_file_explains_what_to_do(tmp_path):
    with pytest.raises(DataUnavailable, match="Update"):
        holders_for_cusip(str(tmp_path / "none.db"), "709789101")
