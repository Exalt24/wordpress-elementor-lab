# LIFESPAN: permanent
"""Checks the Product and Offer markup on a product page against what the page itself shows.

    python scripts/schema_check.py http://localhost:8089/product/gold-bar-1oz/

Checks: one Product node, name and sku, an Offer with a price and a currency, an availability URL, a price valid until a moment that has not passed and is
close (a live price must not claim it is valid until the end of the year), and the offered price equal to a price printed on the page. Standard library only.
"""
import datetime
import json
import re
import sys
import urllib.request

MAX_VALID_SECONDS = 3600


def fetch(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def nodes(html):
    found = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        found += [n for n in items if isinstance(n, dict)]
    return found


def visible_prices(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text).replace("&pound;", "£")
    return {m.replace(",", "") for m in re.findall(r"£\s*([0-9][0-9,]*\.[0-9]{2})", text)}


def audit(html, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    results = []

    def add(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    found = nodes(html)
    add("the JSON-LD parses", found is not None)
    products = [n for n in (found or []) if n.get("@type") == "Product"]
    add("exactly one Product node", len(products) == 1, "%d found" % len(products))
    p = products[0] if len(products) == 1 else {}
    add("name and sku present", bool(p.get("name")) and bool(p.get("sku")))
    offer = p.get("offers") or {}
    if isinstance(offer, list):
        offer = offer[0] if offer else {}
    add("an Offer with a price and a currency", bool(offer.get("price")) and bool(offer.get("priceCurrency")), str(offer.get("price")))
    add("availability is a schema.org URL", str(offer.get("availability", "")).startswith("https://schema.org/"), str(offer.get("availability")))
    until = offer.get("priceValidUntil")
    try:
        when = datetime.datetime.fromisoformat(str(until).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        secs = (when - now).total_seconds()
        add("priceValidUntil is close, so a live price does not claim to last", -120 < secs <= MAX_VALID_SECONDS, "%d seconds from now" % secs)
    except (TypeError, ValueError):
        add("priceValidUntil is close, so a live price does not claim to last", False, "missing or not a date")
    add("the offered price is a price printed on the page", str(offer.get("price")) in visible_prices(html), "offer %s, page %s" % (offer.get("price"), sorted(visible_prices(html))[:4]))
    return results


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    results = audit(fetch(sys.argv[1]))
    for name, ok, detail in results:
        print(("PASS  " if ok else "FAIL  ") + name + ("   [" + detail + "]" if detail else ""))
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n%d of %d checks pass" % (passed, len(results)))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
