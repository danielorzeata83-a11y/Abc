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
             srv.render_smart_money()]
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
