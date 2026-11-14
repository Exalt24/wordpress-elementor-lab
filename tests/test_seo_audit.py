"""Offline tests for the audit's HTML checks: each one feeds a small page that has exactly one defect and expects exactly that check to fail.
The network function is replaced, so nothing here touches a server.   python tests/test_seo_audit.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import seo_audit  # noqa: E402

GOOD = """<!doctype html><html lang="en"><head><title>A good page title that is long enough ok</title>
<meta name="description" content="A description that is long enough to be useful to a searcher, between seventy and one hundred sixty characters.">
<meta name="viewport" content="width=device-width"><link rel="canonical" href="http://t/p/">
<meta property="og:title" content="t"><meta property="og:description" content="d"><meta property="og:type" content="website"><meta property="og:url" content="http://t/p/">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Service","name":"x"}</script></head>
<body><h1>One</h1><h2>Two</h2><img src="a.png" alt="a"><a href="mailto:x@y.z">mail</a></body></html>"""


def run(html, url="http://t/p/"):
    seo_audit.fetch = lambda u, method="GET", timeout=20: (200, html.encode(), 0.05, url)
    return {name: ok for name, ok, _ in seo_audit.audit(url)}


def expect_only(name_fragment, html):
    results = run(html)
    failed = [n for n, ok in results.items() if not ok]
    good = len(failed) == 1 and name_fragment in failed[0]
    print(("PASS  " if good else "FAIL  ") + f"only '{name_fragment}' fails" + ("" if good else f"   <- failed: {failed}"))
    return good


def base_href_resolves_links():
    """A page with <base href> must have its relative links checked against the base, the way a browser follows them (OpenCart does this)."""
    asked = []
    page = GOOD.replace("<h1>One</h1>", '<h1>One</h1><a href="index.php?route=a">x</a>').replace("<head>", '<head><base href="http://t/shop/"/>')

    def fake(u, method="GET", timeout=20):
        asked.append(u)
        return (200 if u in ("http://t/p/", "http://t/shop/index.php?route=a") else 404), page.encode(), 0.05, u

    seo_audit.fetch = fake
    results = {name: ok for name, ok, _ in seo_audit.audit("http://t/p/")}
    good = results["no broken links"] and "http://t/shop/index.php?route=a" in asked and "http://t/p/index.php?route=a" not in asked
    print(("PASS  " if good else "FAIL  ") + "a relative link is checked against the page's base href")
    return good


def main():
    ok = True
    base = run(GOOD)
    all_pass = all(base.values())
    print(("PASS  " if all_pass else "FAIL  ") + "a clean page passes every check" + ("" if all_pass else f"   <- {[n for n, v in base.items() if not v]}"))
    ok &= all_pass
    ok &= expect_only("exactly one h1", GOOD.replace("<h1>One</h1>", "<h1>One</h1><h1>Again</h1>"))
    ok &= expect_only("heading levels", GOOD.replace("<h2>Two</h2>", "<h3>Skipped</h3>"))
    ok &= expect_only("alt attribute", GOOD.replace('alt="a"', ""))
    ok &= expect_only("meta description", GOOD.replace('name="description"', 'name="x-none"'))
    ok &= expect_only("canonical", GOOD.replace('rel="canonical"', 'rel="x"'))
    ok &= expect_only("lang attribute", GOOD.replace(' lang="en"', ""))
    ok &= expect_only("structured data", GOOD.replace('"@type":"Service","name":"x"}', '"@type":"Service","name":'))
    ok &= expect_only("Open Graph", GOOD.replace('property="og:url"', 'property="x:url"'))
    ok &= base_href_resolves_links()
    print("\nall tests passed" if ok else "\nSOME FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
