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
