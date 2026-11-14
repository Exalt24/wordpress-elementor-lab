# LIFESPAN: permanent
"""Drives the running shop through the price feed's bad days and checks what a visitor, a search engine and a feed reader would see.

    python scripts/live_checks.py http://localhost:8089 http://localhost:8090

Needs the lab running with the defaults (price counts as fresh for 10 seconds, the last good price may be shown stale for 40). Takes about two minutes.
Steps: a cached page makes at most one feed call per ten seconds; a dead feed shows the last good price marked stale; past the limit there is no price,
no add to cart button, no Offer markup and no feed line; a recovered feed is fresh again; a feed that triples the gold price, answers with garbage or
answers after five seconds never reaches a customer. Standard library only. Exits 1 when any check fails.
"""
import json
import re
import sys
import time
import urllib.request

TTL, STALE = 10, 40
PRODUCT = "/product/gold-bar-1oz/"
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + name + ("   [" + str(detail) + "]" if detail else ""), flush=True)


def get(url, timeout=30):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace"), time.perf_counter() - t0
    except Exception as e:  # a failed fetch is reported by the check that needed it
        return "", time.perf_counter() - t0


def main():
    shop, feed = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
    control = lambda q: json.load(urllib.request.urlopen(feed + "/control?" + q, timeout=10))
    stats = lambda: json.load(urllib.request.urlopen(feed + "/stats", timeout=10))["requests"]
    rest = lambda: json.loads(get(shop + "/wp-json/bullion/v1/spot")[0] or "{}")
    product = lambda: get(shop + PRODUCT)[0]

    control("reset=1")
    time.sleep(TTL + 1)  # let any earlier reading expire so the count below starts clean
    before = stats()
    for _ in range(6):
        get(shop + "/shop/")
    check("six shop page loads inside ten seconds cost the feed at most one call", stats() - before <= 1, "%d calls" % (stats() - before))
    home = get(shop + "/")[0]
    check("the home page carries FAQPage and Organization markup, and the questions are printed on the page",
          '"@type":"FAQPage"' in home and '"@type":"Organization"' in home and "What happens if the price feed stops?" in home)
    html = product()
    good = rest()
    check("a fresh product page shows a live price marked fresh", 'data-state="fresh"' in html and "Live price as of" in html and "single_add_to_cart_button" in html)
    base_gold = good["prices"]["gold"]

    control("mode=fail")
    time.sleep(TTL + 1)
    html, secs = get(shop + PRODUCT)
    r = rest()
    check("a dead feed: the page still shows the last good price, marked stale", 'data-state="stale"' in html and r["state"] == "stale" and r["prices"]["gold"] == base_gold, r.get("state"))
    check("a dead feed: the page still answers quickly (the feed timeout is 2 seconds)", secs < 4, "%.1f s" % secs)

    deadline = time.time() + STALE + 30
    while time.time() < deadline and rest().get("state") != "unavailable":
        time.sleep(2)
    html = product()
    r = rest()
    feed_xml = get(shop + "/?bullion_feed=merchant")[0]
    check("past the limit: the REST route reports unavailable with no prices", r.get("state") == "unavailable" and r.get("prices") is None, r)
    check("past the limit: the product page says the price is unavailable", "Price unavailable" in html)
    check("past the limit: there is no add to cart button", "single_add_to_cart_button" not in html)
    check("past the limit: the JSON-LD has no Offer", '"offers"' not in html)
    check("past the limit: the Merchant Center feed leaves the product out", "GOLD-BAR-1OZ" not in feed_xml)

    control("mode=ok")
    html = product()
    check("a recovered feed is fresh again, with the button and the Offer back", 'data-state="fresh"' in html and "single_add_to_cart_button" in html and '"offers"' in html)
    gold_now = rest()["prices"]["gold"]

    for mode, label in (("jump", "triples the gold price"), ("garbage", "answers with a maintenance page"), ("slow", "answers after five seconds")):
        control("mode=" + mode)
        time.sleep(TTL + 1)
        html, secs = get(shop + PRODUCT)
        r = rest()
        ok = r.get("state") == "stale" and abs(r["prices"]["gold"] - gold_now) / gold_now < 0.05 and secs < 4.5
        check("a feed that %s never reaches a customer: the last good price stays, marked stale" % label, ok, "%s, gold %s, %.1f s" % (r.get("state"), r.get("prices", {}) and r["prices"]["gold"], secs))
        control("mode=ok")
        time.sleep(TTL + 1)
        gold_now = rest()["prices"]["gold"]

    control("reset=1")
    print("\n%d of %d checks pass" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
