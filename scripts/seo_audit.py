"""A small technical SEO audit for one page: the things a website specialist checks first.

    python scripts/seo_audit.py http://localhost:8087/seller-audit/            # human report, exit 1 if any check fails
    python scripts/seo_audit.py <url> --json                                   # machine-readable

Checks: status and redirect chain, title length, meta description length, exactly one h1, heading order, image alt text, canonical,
language attribute, viewport, Open Graph basics, valid JSON-LD, internal and external link status, response time and page weight.
Standard library only, so it runs anywhere Python does.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.meta = {}          # name or property -> content
        self.headings = []      # (level, text)
        self._heading = None
        self.images = []        # (src, alt or None)
        self.links = []         # href
        self.canonical = None
        self.lang = None
        self.jsonld = []
        self._in_jsonld = False
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key.lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = [int(tag[1]), ""]
        elif tag == "img":
            self.images.append((a.get("src", ""), a.get("alt")))
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading:
            self.headings.append((self._heading[0], self._heading[1].strip()))
            self._heading = None
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld.append(self._buf)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._heading is not None:
            self._heading[1] += data
        if self._in_jsonld:
            self._buf += data


def fetch(url, method="GET", timeout=20):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "seo-audit/1.0"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read() if method == "GET" else b""
            return r.status, body, time.time() - started, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, b"", time.time() - started, url
    except Exception:
        return 0, b"", time.time() - started, url


def audit(url):
    results = []  # (name, ok, detail)

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    status, body, took, final = fetch(url)
    check("page loads with 200", status == 200, f"status {status}")
    check("no redirect chain", final.rstrip("/") == url.rstrip("/"), f"final url {final}")
    html = body.decode("utf-8", errors="replace")
    p = Page()
    p.feed(html)

    check("title present and 30-65 characters", 30 <= len(p.title.strip()) <= 65, f"{len(p.title.strip())} characters: {p.title.strip()[:70]!r}")
    desc = p.meta.get("description", "")
    check("meta description present and 70-160 characters", 70 <= len(desc) <= 160, f"{len(desc)} characters")
    h1s = [t for lv, t in p.headings if lv == 1]
    check("exactly one h1", len(h1s) == 1, f"{len(h1s)} found")
    order_ok, last = True, 0
    for lv, _ in p.headings:
        if last and lv > last + 1:
            order_ok = False
        last = lv
    check("heading levels do not skip", order_ok, " > ".join(f"h{lv}" for lv, _ in p.headings))
    missing_alt = [s for s, alt in p.images if alt is None]
    check("every image has an alt attribute", not missing_alt, f"{len(p.images)} images, {len(missing_alt)} without alt")
    check("canonical link present", bool(p.canonical), p.canonical or "missing")
    check("html lang attribute present", bool(p.lang), p.lang or "missing")
    check("viewport meta present", "viewport" in p.meta, p.meta.get("viewport", "missing"))
    og = [k for k in ("og:title", "og:description", "og:type", "og:url") if k in p.meta]
    check("Open Graph title, description, type and url present", len(og) == 4, f"has {og}")
    schema_ok, schema_detail = bool(p.jsonld), "no JSON-LD block"
    for block in p.jsonld:
        try:
            data = json.loads(block)
            schema_ok, schema_detail = True, f"valid JSON-LD, @type {data.get('@type') if isinstance(data, dict) else 'list'}"
        except ValueError as e:
            schema_ok, schema_detail = False, f"JSON-LD does not parse: {e}"
    check("structured data (JSON-LD) present and valid", schema_ok, schema_detail)

    base = urllib.parse.urlparse(url)
    seen, bad = set(), []
    for href in p.links:
        full = urllib.parse.urljoin(url, href)
        if full.startswith("mailto:") or full.startswith("tel:") or full.split("#")[0] in seen or not full.startswith("http"):
            continue
        seen.add(full.split("#")[0])
        code, _, _, _ = fetch(full.split("#")[0], method="GET", timeout=10)
        if code == 0 or code >= 400:
            bad.append((full, code))
    check("no broken links", not bad, f"{len(seen)} http links checked, broken: {bad}" if bad else f"{len(seen)} http links checked")
    check("server responds in under 1.5 s", took < 1.5, f"{took:.2f}s")
    check("HTML under 200 KB", len(body) < 200_000, f"{len(body) / 1024:.0f} KB")
    return results


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    out = audit(args[0])
    if "--json" in sys.argv:
        print(json.dumps([{"check": n, "pass": ok, "detail": d} for n, ok, d in out], indent=2))
    else:
        for n, ok, d in out:
            print(("PASS  " if ok else "FAIL  ") + n + (f"   ({d})" if d else ""))
        failed = [n for n, ok, _ in out if not ok]
        print(f"\n{len(out) - len(failed)}/{len(out)} checks pass" + (f", {len(failed)} to fix" if failed else ""))
    sys.exit(0 if all(ok for _, ok, _ in out) else 1)
