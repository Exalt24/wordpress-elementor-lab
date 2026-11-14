"""Offline tests for the bullion shop scripts: the stand-in price feed, the hardening probe and the Product markup check.
Each probe check is fed a fake site with exactly one defect and must fail exactly that check.   python bullion-shop/tests/test_scripts.py
"""
import datetime
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
os.environ["LATENCY_MS"] = "0"
import hardening_check  # noqa: E402
import schema_check  # noqa: E402
import spot_server  # noqa: E402

failed = 0


def check(name, ok, detail=""):
    global failed
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "   <- " + str(detail)))
    failed += 0 if ok else 1


def start(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


# ---- the stand-in feed ----
def feed_tests():
    srv = spot_server.serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    spot_server.STATE.update(mode="ok", requests=0)
    d = get_json(base + "/spot")
    check("feed: /spot returns two positive prices, a currency and the stand-in flag", d["gold"] > 0 and d["silver"] > 0 and d["currency"] == "GBP" and d["stand_in"] is True, d)
    check("feed: the counter counts a request", get_json(base + "/stats")["requests"] == 1)
    check("feed: prices drift by about 1 percent at most", all(abs(spot_server.prices(t)["gold"] - 1650) <= 17 for t in range(0, 4000, 37)))
    check("feed: two callers at the same second get the same prices", spot_server.prices(1700000000) == spot_server.prices(1700000000))
    get_json(base + "/control?mode=jump")
    check("feed: jump mode triples gold", get_json(base + "/spot")["gold"] > 4000)
    get_json(base + "/control?mode=fail")
    try:
        urllib.request.urlopen(base + "/spot", timeout=10)
        code = 200
    except urllib.error.HTTPError as e:
        code = e.code
    check("feed: fail mode answers 503", code == 503, code)
    get_json(base + "/control?mode=garbage")
    with urllib.request.urlopen(base + "/spot", timeout=10) as r:
        body = r.read().decode()
    check("feed: garbage mode answers a page that is not JSON", body.startswith("<html>"))
    get_json(base + "/control?reset=1")
    check("feed: reset restores the mode and the counter", get_json(base + "/stats") == {"requests": 0, "mode": "ok"})
    srv.shutdown()


# ---- the hardening probe against a fake site ----
def fake_site(flags):
    class H(BaseHTTPRequestHandler):
        fails = 0

        def log_message(self, *a):
            pass

        def out(self, code, body=b"", headers=()):
            self.send_response(code)
            for k, v in headers:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        searches = 0

        def do_GET(self):
            if self.path in ("/.env", "/wp-config.php.bak") or "sqlmap" in self.headers.get("User-Agent", ""):
                return self.out(404 if "no_firewall" in flags else 403, b"no")
            if self.path.startswith("/?s="):
                H.searches += 1
                if H.searches > 30 and "no_rate_limit" not in flags:
                    return self.out(429, b"Too many requests")
                return self.out(200, b"<html><body>results</body></html>")
            if self.path.startswith("/wp-admin/theme-editor.php"):
                if "file_editor" in flags:
                    return self.out(200, b'<textarea id="newcontent">')
                return self.out(403, b"Sorry, you are not allowed to edit templates for this site.")
            if self.path.startswith("/wp-json/wp/v2/users"):
                return self.out(200, b'[{"id":1,"slug":"admin"}]') if "users_open" in flags else self.out(404, b'{"code":"rest_no_route"}')
            if self.path.startswith("/?author=1"):
                if "author_body_leak" in flags:
                    return self.out(200, b"<html><body class='author-admin'>")   # no redirect, the archive is served on the spot
                return self.out(301, b"", [("Location", "/author/admin/")]) if ("author_leak" in flags or "author_url_leak" in flags) else self.out(301, b"", [("Location", "/")])
            if self.path.startswith("/author/"):
                return self.out(200, b"<html><body>posts</body>") if "author_url_leak" in flags else self.out(200, b"<html><body class='author-admin'>")
            headers = [(h, "x") for h in hardening_check.REQUIRED_HEADERS if h not in flags]
            if "pingback" in flags:
                headers.append(("X-Pingback", "/xmlrpc.php"))
            body = b'<html><head><meta name="generator" content="WordPress 7"></head></html>' if "generator" in flags else b"<html><head></head><body>home</body></html>"
            self.out(200, body, headers)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(n).decode()
            if self.path.startswith("/xmlrpc.php"):
                return self.out(200, b"<methodResponse>") if "xmlrpc_open" in flags else self.out(403, b"disabled")
            right = "pwd=right" in data
            H.fails += 0 if right else 1
            locked = "no_limits" not in flags and H.fails >= 5
            if right and locked and "lock_message_but_logs_in" in flags:
                return self.out(302, b"Too many failed attempts", [("Set-Cookie", "wordpress_logged_in_abc=1; path=/"), ("Location", "/wp-admin/")])
            if right and not locked:
                return self.out(302, b"", [("Set-Cookie", "wordpress_logged_in_abc=1; path=/"), ("Location", "/wp-admin/")])
            return self.out(200, b"Too many failed attempts" if locked else b"wrong password")

    return start(H)


def probe_tests():
    names = {
        "X-Content-Type-Options": "header X-Content-Type-Options", "X-Frame-Options": "header X-Frame-Options",
        "Referrer-Policy": "header Referrer-Policy", "Permissions-Policy": "header Permissions-Policy",
        "pingback": "no X-Pingback header", "generator": "no generator tag", "xmlrpc_open": "XML-RPC refused",
        "users_open": "users list closed to visitors", "author_leak": "author enumeration closed", "no_limits": "login limits", "no_rate_limit": "site search is rate limited", "no_firewall": "scanner probes refused",
        "file_editor": "dashboard code editor disabled", "author_body_leak": "author enumeration closed", "author_url_leak": "author enumeration closed",
        "lock_message_but_logs_in": "login limits",
    }
    srv, base = fake_site(set())
    results = hardening_check.audit(base, "admin", "right")
    check("probe: a hardened site passes every check", all(ok for _, ok, _ in results) and len(results) == 13, [r for r in results if not r[1]])
    srv.shutdown()
    for flag, label in names.items():
        srv, base = fake_site({flag})
        results = hardening_check.audit(base, "admin", "right")
        bad = [n for n, ok, _ in results if not ok]
        check("probe: with only '%s' wrong, exactly that check fails" % flag, len(bad) == 1 and bad[0].startswith(label), bad)
        srv.shutdown()


# ---- the Product markup check ----
def page(offer_price="1694.23", valid_until=None, visible="1,694.23", extra_offer=None, product=True):
    now = datetime.datetime.now(datetime.timezone.utc)
    valid_until = valid_until or (now + datetime.timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    offer = {"@type": "Offer", "price": offer_price, "priceCurrency": "GBP", "availability": "https://schema.org/InStock", "priceValidUntil": valid_until}
    offer.update(extra_offer or {})
    node = {"@type": "Product", "name": "Bar", "sku": "B1", "offers": offer}
    graph = json.dumps({"@context": "https://schema.org", "@graph": [node] if product else []})
    return '<html><head><script type="application/ld+json">%s</script></head><body><p>&pound;%s</p></body></html>' % (graph, visible)


def schema_tests():
    def only(label, html):
        bad = [n for n, ok, _ in schema_check.audit(html) if not ok]
        check("markup: only '%s' fails" % label, len(bad) == 1 and label in bad[0], bad)

    check("markup: a good page passes every check", all(ok for _, ok, _ in schema_check.audit(page())))
    check("markup: a page with no Product node fails the Product check", "exactly one Product node" in [n for n, ok, _ in schema_check.audit(page(product=False)) if not ok])
    only("the offered price is a price printed on the page", page(visible="1,700.00"))
    only("priceValidUntil is close", page(valid_until="2026-12-31T00:00:00Z"))
    only("an Offer with a price and a currency", page(extra_offer={"priceCurrency": ""}))
    only("availability is a schema.org URL", page(extra_offer={"availability": "in stock"}))
    check("markup: broken JSON-LD is reported, not crashed on", "the JSON-LD parses" in [n for n, ok, _ in schema_check.audit(page().replace('"@graph"', '"@graph" broken')) if not ok])


feed_tests()
probe_tests()
schema_tests()
print("\n" + ("all passed" if failed == 0 else "%d failed" % failed))
sys.exit(1 if failed else 0)
