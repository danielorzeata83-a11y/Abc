import http.client
import json
import threading

from markov.data_providers import DataUnavailable
import sensa_server as srv


class FakeHub:
    def movers(self, symbols, n=5):
        return {"gainers": [{"symbol": symbols[0], "price": 1, "change_pct": 1.0}], "losers": []}

    def analyst(self, s):
        return {"verdict": "Buy"}

    def options(self, s):
        return {"symbol": s, "cp": {}, "chain": []}

    def news(self, symbol=None, limit=12):
        return [{"headline": "h"}]

    def yield_curve(self):
        raise DataUnavailable("treasury blocked")


def _get(path):
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA", "BBB"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.getheader("Content-Type"), r.read()
    finally:
        server.shutdown()
        server.server_close()


def test_index_page_is_html_with_watchlist():
    st, ct, body = _get("/")
    assert st == 200 and ct.startswith("text/html")
    assert b"AAA" in body and b"BBB" in body


def test_movers_endpoint_defaults_to_watchlist():
    st, _, body = _get("/api/movers")
    assert st == 200
    assert json.loads(body)["gainers"][0]["symbol"] == "AAA"


def test_options_endpoint_returns_snapshot():
    st, _, body = _get("/api/options/aaa")
    assert st == 200 and json.loads(body)["symbol"] == "AAA"


def test_bad_symbol_is_rejected_with_400():
    st, _, _ = _get("/api/analyst/AAA%24BAD")
    assert st == 400


def test_provider_outage_maps_to_503_with_message():
    st, _, body = _get("/api/yield-curve")
    assert st == 503 and "treasury blocked" in json.loads(body)["error"]


def test_unknown_path_is_404():
    assert _get("/nope")[0] == 404


def test_insiders_endpoint_with_optional_symbol():
    class H(FakeHub):
        def insiders(self, symbol=None, limit=10):
            return [{"symbol": symbol or "ANY"}]
    server = srv.make_server(H(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        for path, want in (("/api/insiders", "ANY"), ("/api/insiders/aaa", "AAA")):
            c.request("GET", path)
            r = c.getresponse()
            assert r.status == 200 and json.loads(r.read())[0]["symbol"] == want
    finally:
        server.shutdown()
        server.server_close()


def test_sectors_endpoint():
    class H(FakeHub):
        def sectors(self):
            return [{"symbol": "XLK", "sector": "Technology", "change_pct": 1.0}]
    server = srv.make_server(H(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/sectors")
        r = c.getresponse()
        assert r.status == 200 and json.loads(r.read())[0]["symbol"] == "XLK"
    finally:
        server.shutdown()
        server.server_close()


def test_short_volume_endpoint():
    class H(FakeHub):
        def short_volume(self, s):
            return {"symbol": s, "short_ratio": 0.5}
    server = srv.make_server(H(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/short-volume/aaa")
        r = c.getresponse()
        assert r.status == 200 and json.loads(r.read())["short_ratio"] == 0.5
    finally:
        server.shutdown()
        server.server_close()


def test_page_inline_script_is_syntactically_valid_javascript(tmp_path):
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node not installed")
    script = re.search(r"<script>(.*)</script>", srv.render_index(["AAA"]), re.S).group(1)
    f = tmp_path / "page.js"
    f.write_text(script)
    r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_client_disconnect_while_writing_is_ignored_not_raised():
    class Gone:
        def __init__(self, exc):
            self.exc = exc

        def write(self, data):
            raise self.exc

    for exc in (ConnectionAbortedError(), BrokenPipeError(), ConnectionResetError()):
        srv.write_quietly(Gone(exc), b"x")        # must not raise


def test_other_write_errors_still_propagate():
    class Broken:
        def write(self, data):
            raise ValueError("real bug")

    import pytest
    with pytest.raises(ValueError):
        srv.write_quietly(Broken(), b"x")


def _get_raw(hub, path):
    server = srv.make_server(hub, "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.getheader("Content-Type"), r.read()
    finally:
        server.shutdown()
        server.server_close()


def test_bars_endpoint_passes_symbol_and_timeframe():
    class H(FakeHub):
        def candles(self, s, tf):
            return [{"time": 1, "open": 1, "high": 2, "low": 0, "close": 1.5, "volume": 1, "s": s, "tf": tf}]
    st, _, body = _get_raw(H(), "/api/bars/aaa?tf=4h")
    assert st == 200 and json.loads(body)[0]["s"] == "AAA" and json.loads(body)[0]["tf"] == "4h"


def test_bars_bad_timeframe_is_400_and_missing_cache_is_503():
    class H(FakeHub):
        def candles(self, s, tf):
            if tf == "1h":
                raise DataUnavailable("no intraday cache for AAA")
            raise ValueError("bad tf")
    assert _get_raw(H(), "/api/bars/AAA?tf=7m")[0] == 400
    st, _, body = _get_raw(H(), "/api/bars/AAA?tf=1h")
    assert st == 503 and "no intraday cache" in json.loads(body)["error"]


def test_vendored_chart_library_is_served():
    st, ct, body = _get_raw(FakeHub(), "/static/lightweight-charts.js")
    assert st == 200 and "javascript" in ct and len(body) > 10000


class MgrHub(FakeHub):
    def manager(self, cik):
        return {"cik": cik, "name": "Test Capital LP", "stats": {}, "top": [], "allocation": [], "activity": {}}

    def manager_filings(self, cik, offset=0, limit=20):
        return {"total": 1, "rows": [{"quarter": "Q2 2026", "off": offset, "lim": limit}]}


def test_manager_page_is_html_with_shared_navigation_for_any_slug():
    st, ct, body = _get_raw(MgrHub(), "/institutional-investor/manager/0001609098-darsana-capital-partners-lp")
    assert st == 200 and ct.startswith("text/html")
    assert b"Smart Money" in body and b"0001609098" in body


def test_manager_page_rejects_non_numeric_cik():
    assert _get_raw(MgrHub(), "/institutional-investor/manager/abc-foo")[0] == 404


def test_manager_api_endpoints_with_paging_parameters():
    st, _, body = _get_raw(MgrHub(), "/api/manager/1609098")
    assert st == 200 and json.loads(body)["name"] == "Test Capital LP"
    st, _, body = _get_raw(MgrHub(), "/api/manager/1609098/filings?offset=20&limit=20")
    assert st == 200 and json.loads(body)["rows"][0]["off"] == 20


def test_manager_api_clamps_bad_paging_and_rejects_bad_cik():
    st, _, body = _get_raw(MgrHub(), "/api/manager/1609098/filings?offset=-5&limit=99999")
    assert st == 200 and json.loads(body)["rows"][0]["off"] == 0 and json.loads(body)["rows"][0]["lim"] <= 50
    assert _get_raw(MgrHub(), "/api/manager/12ab")[0] == 400


def test_institutional_landing_page_lists_example_managers():
    st, _, body = _get_raw(MgrHub(), "/institutional-investor")
    assert st == 200 and b"Berkshire" in body


def test_every_page_script_is_syntactically_valid_javascript(tmp_path):
    import re
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node not installed")
    pages = [srv.render_index(["AAA"]), srv.render_manager("0001609098"), srv.render_institutional(), srv.render_alerts(),
             srv.render_smart_money(), srv.render_managers("a"), srv.render_latest_filings(),
             srv.render_filing("000000000126000007"), srv.render_insiders(), srv.render_dark_pool(),
             srv.render_political(), srv.render_investors("PEBO")]
    for n, html in enumerate(pages):
        for m, script in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
            f = tmp_path / f"p{n}_{m}.js"
            f.write_text(script)
            r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
            assert r.returncode == 0, (n, r.stderr)


class FakeWatcher:
    def __init__(self):
        self.followed, self.checked = [], 0

    def following(self):
        return [{"cik": c, "name": "N"} for c in self.followed]

    def events(self):
        return [{"id": "e1", "name": "Test Capital LP", "counts": {"new": 1, "exited": 0, "increased": 0, "reduced": 0},
                 "changes": [], "quarter": "Q2 2026", "form": "13F-HR", "filed": "2026-08-14",
                 "accession": "A", "cik": "0000000001", "amended": False, "notified": True,
                 "detected_at": "t"}]

    def follow(self, cik, baseline=True):
        if cik == "999":
            raise DataUnavailable("sec down")
        self.followed.append(f"{int(cik):010d}")

    def unfollow(self, cik):
        self.followed = [c for c in self.followed if c != f"{int(cik):010d}"]

    def check(self):
        self.checked += 1
        return []


def _req(method, path, body=None, headers=None, watcher=None):
    w = watcher or FakeWatcher()
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], watcher=w)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        h = {"Content-Type": "application/json"} if method == "POST" else {}
        h.update(headers or {})
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
        r = c.getresponse()
        return r.status, r.read(), w
    finally:
        server.shutdown()
        server.server_close()


def test_watch_list_endpoint_returns_following_and_events():
    st, body, _ = _req("GET", "/api/watch")
    d = json.loads(body)
    assert st == 200 and d["following"] == [] and d["events"][0]["name"] == "Test Capital LP"


def test_follow_and_unfollow_via_post_normalise_the_cik():
    st, body, w = _req("POST", "/api/watch/follow", {"cik": "1609098"})
    assert st == 200 and w.followed == ["0001609098"]
    w2 = FakeWatcher()
    w2.followed = ["0001609098"]
    st, _, w2 = _req("POST", "/api/watch/unfollow", {"cik": "1609098"}, watcher=w2)
    assert st == 200 and w2.followed == []


def test_follow_rejects_bad_cik_and_reports_sec_outage():
    assert _req("POST", "/api/watch/follow", {"cik": "12ab"})[0] == 400
    assert _req("POST", "/api/watch/follow", {})[0] == 400
    st, body, _ = _req("POST", "/api/watch/follow", {"cik": "999"})
    assert st == 503 and "sec down" in json.loads(body)["error"]


def test_post_requires_json_content_type_and_local_host_header():
    # a cross-site HTML form can only send form content types -> must be refused
    st, _, w = _req("POST", "/api/watch/follow", {"cik": "1"}, headers={"Content-Type": "text/plain"})
    assert st == 415 and w.followed == []
    st, _, w = _req("POST", "/api/watch/follow", {"cik": "1"}, headers={"Host": "evil.example.com"})
    assert st == 403 and w.followed == []         # DNS-rebinding guard


def test_check_now_endpoint_runs_the_watcher_once():
    st, body, w = _req("POST", "/api/watch/check", {})
    assert st == 200 and w.checked == 1 and json.loads(body) == {"new_events": 0}


def test_watch_endpoints_are_404_when_no_watcher_is_configured():
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/watch")
        assert c.getresponse().status == 503
    finally:
        server.shutdown()
        server.server_close()


def test_alerts_page_renders_for_the_shared_nav():
    st, ct, body = _get_raw(FakeHub(), "/smart-money/alerts")
    assert st == 200 and b"Alerts" in body and b"Smart Money" in body


class FakeSmart:
    def __init__(self):
        self.started = []

    def overview(self):
        return {"quarter": "Q2 2026", "funds": [], "stocks": []}

    def status(self):
        return {"state": "idle", "message": "", "period": "2026-06-30", "quarter": "Q2 2026", "built_at": "t"}

    def start(self, force=False):
        self.started.append(force)
        return len(self.started) == 1


def _smart_req(method, path, body=None, headers=None, smart=None):
    sm = smart or FakeSmart()
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], smart=sm)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        h = {"Content-Type": "application/json"} if method == "POST" else {}
        h.update(headers or {})
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
        r = c.getresponse()
        return r.status, r.read(), sm
    finally:
        server.shutdown()
        server.server_close()


def test_smart_money_page_and_api_endpoints():
    st, body, _ = _smart_req("GET", "/smart-money")
    assert st == 200 and b"Most held" in body and b"Top funds" in body
    st, body, _ = _smart_req("GET", "/api/smart-money/overview")
    assert st == 200 and json.loads(body)["quarter"] == "Q2 2026"
    st, body, _ = _smart_req("GET", "/api/smart-money/status")
    assert st == 200 and json.loads(body)["state"] == "idle"


def test_smart_money_refresh_starts_once_and_is_guarded_like_other_posts():
    st, body, sm = _smart_req("POST", "/api/smart-money/refresh", {"force": True})
    assert st == 200 and json.loads(body) == {"started": True} and sm.started == [True]
    st, body, sm = _smart_req("POST", "/api/smart-money/refresh", {}, headers={"Content-Type": "text/plain"})
    assert st == 415 and sm.started == []
    st, _, sm = _smart_req("POST", "/api/smart-money/refresh", {}, headers={"Host": "evil.example.com"})
    assert st == 403 and sm.started == []


def test_smart_money_endpoints_report_503_when_not_configured():
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/smart-money/overview")
        assert c.getresponse().status == 503
    finally:
        server.shutdown()
        server.server_close()


def test_smart_money_overview_missing_build_is_503_with_the_hint():
    class Empty(FakeSmart):
        def overview(self):
            raise DataUnavailable("No Smart Money overview yet. Press Update")
    st, body, _ = _smart_req("GET", "/api/smart-money/overview", smart=Empty())
    assert st == 503 and "Press Update" in json.loads(body)["error"]


class RouteHub(FakeHub):
    def latest_filings(self, limit=50):
        return [{"cik": "0000000001", "name": "E6 Portfolios", "form": "13F-HR", "filed": "2026-10-26",
                 "accession": "0000000001-26-000007", "quarter": "Q3 2026", "period": "2026-09-30",
                 "entries": 71, "value": 297e6, "lim": limit}]

    def filing(self, accession):
        if accession == "999999999999999999":
            raise DataUnavailable("filing not found: open it from the manager page")
        return {"name": "Test Capital LP", "accession": accession, "holdings": [], "exited": [], "stats": {}}


class RouteSmart(FakeSmart):
    def managers(self):
        return [{"cik": "0000000001", "name": "Alpha Fund", "state": "NY", "aum": 10.0, "entries": 4, "quarter": "Q2 2026",
                 "accession": "a", "filed": "2026-08-14", "form": "13F-HR"},
                {"cik": "0000000002", "name": "Beta Fund", "state": "CA", "aum": 20.0, "entries": 6, "quarter": "Q2 2026",
                 "accession": "b", "filed": "2026-08-14", "form": "13F-HR"}]


def _route(path, smart=None, hub=None):
    server = srv.make_server(hub or RouteHub(), "127.0.0.1", 0, ["AAA"], smart=smart or RouteSmart())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.getheader("Content-Type"), r.read()
    finally:
        server.shutdown()
        server.server_close()


def test_new_institutional_pages_render_html():
    for path, needle in (("/institutional-investor/managers/a", b"13F filers"),
                         ("/institutional-investor/managers/0", b"13F filers"),
                         ("/institutional-investor/latest-filings", b"Latest 13F filings"),
                         ("/institutional-investor/000000000126000007", b"000000000126000007")):
        st, ct, body = _route(path)
        assert st == 200 and ct.startswith("text/html") and needle in body, path


def test_new_institutional_pages_reject_bad_identifiers():
    for path in ("/institutional-investor/managers/ab", "/institutional-investor/managers/%3Cx%3E",
                 "/institutional-investor/12345", "/institutional-investor/00012345678901234567x"):
        assert _route(path)[0] == 404, path


def test_managers_api_pages_and_searches_the_saved_list():
    st, _, body = _route("/api/managers?letter=a")
    d = json.loads(body)
    assert st == 200 and d["total"] == 1 and d["rows"][0]["name"] == "Alpha Fund"
    d = json.loads(_route("/api/managers?q=fund&limit=1&offset=1")[2])
    assert d["total"] == 2 and [r["name"] for r in d["rows"]] == ["Beta Fund"]
    assert _route("/api/managers?letter=a&offset=abc")[0] == 400


def test_latest_filings_and_filing_api():
    st, _, body = _route("/api/latest-filings?limit=500")
    assert st == 200 and json.loads(body)[0]["lim"] <= 100
    st, _, body = _route("/api/filing/000000000126000007")
    assert st == 200 and json.loads(body)["name"] == "Test Capital LP"
    st, _, body = _route("/api/filing/999999999999999999")
    assert st == 404 and "not found" in json.loads(body)["error"]
    assert _route("/api/filing/12")[0] == 400


def test_managers_api_is_503_without_a_built_list():
    class Empty(RouteSmart):
        def managers(self):
            raise DataUnavailable("No manager list yet. Press Update")
    st, body = _route("/api/managers?letter=a", smart=Empty())[0], _route("/api/managers?letter=a", smart=Empty())[2]
    assert st == 503 and "Press Update" in json.loads(body)["error"]


def test_institutional_landing_links_latest_filings_and_every_letter():
    body = _route("/institutional-investor")[2]
    assert b"/institutional-investor/latest-filings" in body
    assert b"/institutional-investor/managers/a" in body and b"/institutional-investor/managers/z" in body
    assert b"/institutional-investor/managers/0" in body


class FakeInsiders:
    def __init__(self):
        self.calls, self.started = [], []

    def overview(self, days=30, include_plans=True):
        self.calls.append((days, include_plans))
        return {"quarter": "Q3 2026", "as_of": "2026-09-30", "days": days, "top_buys": [], "top_sells": [], "clusters": []}

    def symbol(self, sym, limit=200):
        return {"symbol": sym.upper(), "trades": []}

    def status(self):
        return {"state": "idle", "message": "", "quarter": "Q3 2026", "built_at": "t", "as_of": "2026-09-30"}

    def start(self, force=False):
        self.started.append(force)
        return True


def _ins(method, path, body=None, headers=None, insiders=None):
    ins = insiders or FakeInsiders()
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], insiders=ins)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        h = {"Content-Type": "application/json"} if method == "POST" else {}
        h.update(headers or {})
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
        r = c.getresponse()
        return r.status, r.read(), ins
    finally:
        server.shutdown()
        server.server_close()


def test_insider_page_and_aggregate_api_with_window_and_plan_options():
    st, body, _ = _ins("GET", "/inside-trade")
    assert st == 200 and b"Insider" in body and b"Cluster" in body
    st, body, ins = _ins("GET", "/api/insider-trades?days=7&plans=0")
    assert st == 200 and json.loads(body)["days"] == 7 and ins.calls == [(7, False)]
    _, _, ins = _ins("GET", "/api/insider-trades")
    assert ins.calls == [(30, True)]
    _, _, ins = _ins("GET", "/api/insider-trades?days=99999")
    assert ins.calls == [(365, True)]                                  # clamped
    assert _ins("GET", "/api/insider-trades?days=abc")[0] == 400


def test_insider_symbol_status_and_refresh_endpoints():
    st, body, _ = _ins("GET", "/api/insider-trades/acme")
    assert st == 200 and json.loads(body)["symbol"] == "ACME"
    assert _ins("GET", "/api/insider-trades/bad%24")[0] == 400
    assert json.loads(_ins("GET", "/api/insider-trades/status")[1])["quarter"] == "Q3 2026"
    st, body, ins = _ins("POST", "/api/insider-trades/refresh", {"force": True})
    assert st == 200 and json.loads(body) == {"started": True} and ins.started == [True]
    assert _ins("POST", "/api/insider-trades/refresh", {}, headers={"Content-Type": "text/plain"})[0] == 415


def test_insider_endpoints_503_when_not_configured_or_not_built():
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"])
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/insider-trades")
        assert c.getresponse().status == 503
    finally:
        server.shutdown()
        server.server_close()

    class Empty(FakeInsiders):
        def overview(self, days=30, include_plans=True):
            raise DataUnavailable("No insider data yet. Press Update")
    st, body, _ = _ins("GET", "/api/insider-trades", insiders=Empty())
    assert st == 503 and "Press Update" in json.loads(body)["error"]


class FakeDark:
    def overview(self, top=50):
        return {"week": "2026-10-05", "prev_week": "2026-09-28", "top": [], "venues": [], "history": [], "lim": top}

    def symbol(self, sym):
        if sym.upper() == "NONE":
            raise DataUnavailable("FINRA is unreachable")
        return {"symbol": sym.upper(), "week": "2026-10-05", "venues": []}


def _dark(path, dark="default"):
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], darkpool=FakeDark() if dark == "default" else dark)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.read()
    finally:
        server.shutdown()
        server.server_close()


def test_dark_pool_page_and_api():
    st, body = _dark("/dark-pool")
    assert st == 200 and b"Dark pool" in body and b"weekly" in body
    st, body = _dark("/api/dark-pool?top=999")
    assert st == 200 and json.loads(body)["lim"] <= 200
    assert json.loads(_dark("/api/dark-pool/nvda")[1])["symbol"] == "NVDA"
    assert _dark("/api/dark-pool/bad%24")[0] == 400
    assert _dark("/api/dark-pool?top=abc")[0] == 400
    st, body = _dark("/api/dark-pool/none")
    assert st == 503 and "FINRA" in json.loads(body)["error"]


def test_dark_pool_is_503_when_not_configured():
    assert _dark("/api/dark-pool", dark=None)[0] == 503


class FakePol:
    def __init__(self):
        self.calls, self.started = [], []

    def overview(self, days=90, side=None, ticker=None, member=None, limit=100):
        self.calls.append((days, side, ticker, member, limit))
        return {"as_of": "2026-10-22", "days": days, "latest": [], "top_bought": [], "top_sold": [], "members": [], "trades": 0, "reports": 0}

    def status(self):
        return {"state": "idle", "message": "", "built_at": "t", "as_of": "2026-10-22", "reports": 2, "failed": 1}

    def start(self, force=False):
        self.started.append(force)
        return True


def _pol(method, path, body=None, headers=None, pol="default"):
    p = FakePol() if pol == "default" else pol
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], politicians=p)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        h = {"Content-Type": "application/json"} if method == "POST" else {}
        h.update(headers or {})
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h)
        r = c.getresponse()
        return r.status, r.read(), p
    finally:
        server.shutdown()
        server.server_close()


def test_political_page_and_api_filters():
    st, body, _ = _pol("GET", "/political-trades")
    assert st == 200 and b"Political" in body and b"House" in body
    _, _, p = _pol("GET", "/api/political-trades?days=30&side=buy&ticker=nvda&member=fields&limit=9999")
    assert p.calls == [(30, "buy", "NVDA", "fields", 300)]
    _, _, p = _pol("GET", "/api/political-trades")
    assert p.calls == [(90, None, None, None, 100)]
    assert _pol("GET", "/api/political-trades?side=hold")[0] == 400
    assert _pol("GET", "/api/political-trades?ticker=bad%24")[0] == 400
    assert _pol("GET", "/api/political-trades?days=x")[0] == 400


def test_political_status_refresh_and_guards():
    assert json.loads(_pol("GET", "/api/political-trades/status")[1])["reports"] == 2
    st, body, p = _pol("POST", "/api/political-trades/refresh", {"force": True})
    assert st == 200 and json.loads(body) == {"started": True} and p.started == [True]
    assert _pol("POST", "/api/political-trades/refresh", {}, headers={"Content-Type": "text/plain"})[0] == 415
    assert _pol("POST", "/api/political-trades/refresh", {}, headers={"Host": "evil.example.com"})[0] == 403


def test_political_endpoints_503_when_off_or_not_built():
    assert _pol("GET", "/api/political-trades", pol=None)[0] == 503

    class Empty(FakePol):
        def overview(self, **kw):
            raise DataUnavailable("No congressional trade data yet. Press Update")
    st, body, _ = _pol("GET", "/api/political-trades", pol=Empty())
    assert st == 503 and "Press Update" in json.loads(body)["error"]


class FakeInvestors:
    def __init__(self):
        self.calls = []

    def lookup(self, ticker, **kw):
        from sensa.investors import UnknownTicker
        self.calls.append((ticker, kw))
        if ticker == "ZZZZ":
            raise UnknownTicker("No 13F holders found for ZZZZ")
        if ticker == "DOWN":
            raise DataUnavailable("No investor index yet. Press Update")
        if kw.get("sort_by") == "bad":
            raise ValueError("sortBy must be one of value")
        return {"summary": {"ticker": ticker, "filerCount": 3}, "data": [], "pagination": {"page": kw["page"]}}


def _inv(path, investors="default"):
    inv = FakeInvestors() if investors == "default" else investors
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], investors=inv)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", path)
        r = c.getresponse()
        return r.status, r.read(), inv
    finally:
        server.shutdown()


def test_investors_api_passes_paging_and_sorting_through_with_defaults():
    st, body, inv = _inv("/api/investors/pebo?page=2&limit=50&sortBy=shares&sortOrder=asc")
    assert st == 200 and json.loads(body)["summary"]["ticker"] == "PEBO"
    assert inv.calls[0] == ("PEBO", {"page": 2, "limit": 50, "sort_by": "shares", "sort_order": "asc"})
    _, _, inv = _inv("/api/investors/PEBO")
    assert inv.calls[0][1] == {"page": 1, "limit": 20, "sort_by": "value", "sort_order": "desc"}


def test_investors_api_error_mapping():
    assert _inv("/api/investors/ZZZZ")[0] == 404
    assert _inv("/api/investors/DOWN")[0] == 503
    assert _inv("/api/investors/PEBO?sortBy=bad")[0] == 400
    assert _inv("/api/investors/PEBO?page=abc")[0] == 400
    assert _inv("/api/investors/bad%20ticker")[0] == 400
    st, body, _ = _inv("/api/investors/PEBO", investors=None)
    assert st == 503 and "SEC_CONTACT" in json.loads(body)["error"]


def test_investors_page_is_served_for_a_valid_ticker_only():
    st, body, _ = _inv("/stock/pebo/investors")
    assert st == 200 and b"PEBO" in body and b"/api/investors/" in body
    assert _inv("/stock/bad%3Cscript%3E/investors")[0] == 404


def test_most_held_tickers_and_the_institutional_landing_lead_to_the_investors_page():
    assert "'/stock/'+" in srv.render_smart_money() and "/investors" in srv.render_smart_money()
    html = srv.render_institutional()
    assert 'id="tkf"' in html and "/investors" in html


def test_the_update_loop_checks_immediately_at_launch_and_then_waits():
    import threading
    stop, calls = threading.Event(), []

    class Job:
        def start(self):
            calls.append(1)
            stop.set()                       # the next wait returns at once, ending the loop
    srv._smart_loop(Job(), 24, stop)
    assert calls == [1]


def test_live_status_endpoint_and_when_not_configured():
    class Live:
        def status(self):
            return {"state": "idle", "message": "", "filers": 3, "period": "2026-09-30"}
    server = srv.make_server(FakeHub(), "127.0.0.1", 0, ["AAA"], live=Live())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
        c.request("GET", "/api/live/status")
        r = c.getresponse()
        assert r.status == 200 and json.loads(r.read())["filers"] == 3
    finally:
        server.shutdown()
    assert _inv("/api/live/status", investors=None)[0] == 503


def test_investors_page_shows_which_reports_are_new_and_which_are_carried():
    html = srv.render_investors("PEBO")
    assert "isCurrent" in html and "carriedFilers" in html
