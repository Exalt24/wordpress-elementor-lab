# LIFESPAN: permanent
"""Times a few shop pages and counts what each load costs the price feed.

    python scripts/measure_pages.py http://localhost:8089 http://localhost:8090 [--loads 6]

For every page: one warm-up load, then N timed loads. Time to first byte is the time until the server starts answering, which is where a slow price
integration shows. The feed count is the stand-in server's own counter, read before and after, so it is what the feed really saw. Standard library only.
"""
import argparse
import http.client
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request

PAGES = ["/", "/shop/", "/product/gold-bar-1oz/"]


def timed_get(base, path):
    u = urllib.parse.urlparse(base)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=60)
    t0 = time.perf_counter()
    conn.request("GET", path)
    resp = conn.getresponse()
    first_byte = time.perf_counter() - t0
    body = resp.read()
    total = time.perf_counter() - t0
    conn.close()
    return resp.status, first_byte, total, len(body)


def feed_count(feed):
    with urllib.request.urlopen(feed.rstrip("/") + "/stats", timeout=10) as r:
        return json.load(r)["requests"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shop")
    ap.add_argument("feed")
    ap.add_argument("--loads", type=int, default=6)
    a = ap.parse_args()
    print("%-26s %8s %8s %8s %12s" % ("page", "status", "TTFB s", "total s", "feed calls"))
    for path in PAGES:
        timed_get(a.shop, path)
        before = feed_count(a.feed)
        ttfb, total, status = [], [], 200
        for _ in range(a.loads):
            status, f, t, _ = timed_get(a.shop, path)
            ttfb.append(f)
            total.append(t)
        calls = feed_count(a.feed) - before
        print("%-26s %8d %8.2f %8.2f %12s" % (path, status, statistics.median(ttfb), statistics.median(total), "%d in %d loads" % (calls, a.loads)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
