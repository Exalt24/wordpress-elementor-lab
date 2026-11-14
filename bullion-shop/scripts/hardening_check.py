# LIFESPAN: permanent
"""Probes a running WordPress site for the basic hardening this lab adds, from the outside, the way a scanner would.

    BULLION_ADMIN_PASSWORD=<the lab admin password> python scripts/hardening_check.py http://localhost:8089 [--user admin]

Checks: four security headers, XML-RPC refused, no X-Pingback header, no generator tag, the users REST list closed to visitors, author enumeration closed,
scanner probes refused (a secrets path and an attack tool agent must get a 403), site search rate limited (45 quick searches must meet a 429), the dashboard theme and plugin code editor disabled (it logs in once to look at the editor page as an admin), and login limits (five wrong passwords, then the CORRECT password must still be refused). The login checks read the account's password from the BULLION_ADMIN_PASSWORD environment variable, never from the command line, and need a real account. They leave the probing
address locked for fifteen minutes, so run it on a site you own. Standard library only. Exits 1 when any check fails.
"""
import argparse
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(url, method="GET", data=None, headers=None, follow=True, timeout=20):
    """Returns (status, {lower-case header: value}, body bytes, final url, [Set-Cookie values]). Never raises on an HTTP error status."""
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    try:
        r = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    hdrs = {k.lower(): v for k, v in r.headers.items()}
    return r.status if hasattr(r, "status") else r.code, hdrs, r.read(), r.geturl(), r.headers.get_all("Set-Cookie") or []


REQUIRED_HEADERS = ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy", "Permissions-Policy"]


def login(base, user, password):
    body = urllib.parse.urlencode({"log": user, "pwd": password, "wp-submit": "Log In", "redirect_to": base + "/wp-admin/", "testcookie": "1"}).encode()
    status, hdrs, text, _, cookies = fetch(base + "/wp-login.php", "POST", body,
                                           {"Content-Type": "application/x-www-form-urlencoded", "Cookie": "wordpress_test_cookie=WP%20Cookie%20check"}, follow=False)
    return any(c.startswith("wordpress_logged_in_") for c in cookies), text.decode("utf-8", "replace"), cookies


def audit(base, user=None, password=None):
    base = base.rstrip("/")
    results = []

    def add(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    status, hdrs, body, _, _ = fetch(base + "/")
    for h in REQUIRED_HEADERS:
        add("header " + h, h.lower() in hdrs, hdrs.get(h.lower(), "missing"))
    add("no X-Pingback header", "x-pingback" not in hdrs, hdrs.get("x-pingback", ""))
    add("no generator tag", not re.search(rb'<meta name="generator"', body, re.I), "")
    xml = b'<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName></methodCall>'
    s, _, text, _, _ = fetch(base + "/xmlrpc.php", "POST", xml, {"Content-Type": "text/xml"})
    add("XML-RPC refused", s in (403, 404, 405) and b"methodResponse" not in text, "status %d" % s)
    s, _, text, _, _ = fetch(base + "/wp-json/wp/v2/users")
    add("users list closed to visitors", s in (401, 403, 404) and b'"slug"' not in text, "status %d" % s)
    s, _, text, final, _ = fetch(base + "/?author=1")
    add("author enumeration closed", "/author/" not in final and b"author-" not in text.split(b"<body", 1)[-1][:400], final)
    s1 = fetch(base + "/.env")[0]
    s2 = fetch(base + "/wp-config.php.bak")[0]
    s3 = fetch(base + "/", headers={"User-Agent": "sqlmap/1.7"})[0]
    add("scanner probes refused", s1 == 403 and s2 == 403 and s3 == 403, "/.env %d, /wp-config.php.bak %d, sqlmap agent %d" % (s1, s2, s3))
    codes = []
    for _ in range(45):
        codes.append(fetch(base + "/?s=gold")[0])
        if codes[-1] == 429:
            break
    add("site search is rate limited", 429 in codes, ("a 429 after %d requests" if 429 in codes else "no 429 in %d requests") % len(codes))
    if user and password:
        ok_first, _, cookies = login(base, user, password)
        if ok_first:
            jar = "; ".join(c.split(";")[0] for c in cookies)
            s, _, page, _, _ = fetch(base + "/wp-admin/theme-editor.php", headers={"Cookie": jar})
            add("dashboard code editor disabled", s == 403 and b'id="newcontent"' not in page, "status %d" % s)
        else:
            add("dashboard code editor disabled", False, "could not log in to look")
        wrong = [login(base, user, "wrong-password-%d" % i)[0] for i in range(5)]
        ok_login, text, _ = login(base, user, password)
        add("login limits: the correct password is refused after five failures", not any(wrong) and not ok_login and "Too many failed attempts" in text,
            "logged in" if ok_login else ("refused with the lock message" if "Too many failed attempts" in text else "refused without the lock message"))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--user", help="with BULLION_ADMIN_PASSWORD in the environment, turns on the dashboard editor and login limit checks")
    a = ap.parse_args()
    results = audit(a.url, a.user, os.environ.get("BULLION_ADMIN_PASSWORD"))
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name + ("   [" + detail + "]" if detail else ""))
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n%d of %d checks pass" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
