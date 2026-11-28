# LIFESPAN: permanent
"""End to end check of the manifest to Elementor pipeline against the running lab (bash scripts/setup.sh first).  python tests/live_elementor_pipeline.py

Not part of CI, because it needs WordPress, Elementor and a headless browser. It drives the real route and the real editor and prints PASS or FAIL
for each case: the good manifest is saved as a draft and read back in the editor, the verified draft is promoted, broken trees are caught
and their drafts deleted, and the route turns away what it should (a wrong hash, a page it did not generate, no credentials, bad input).
"""
import copy
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import elementor_draft as ed  # noqa: E402
import manifest_to_elementor as m2e  # noqa: E402

BASE = os.environ.get("LAB_BASE", "http://localhost:8087")
AUTH = ed.credentials()
SAMPLE = os.path.join(ROOT, "elementor", "seller-audit.layout.json")
RESULTS = []


def case(label, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("PASS  " if ok else "FAIL  ") + label + ((" | " + detail) if detail and not ok else ""))


def cli(*args):
    done = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "elementor_draft.py")] + list(args), capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=ROOT)
    return done.returncode, done.stdout + done.stderr


def pages(slug):
    """Pages with this slug in any status, read through the core REST API."""
    req = urllib.request.Request(BASE + "/wp-json/wp/v2/pages?slug=" + slug + "&status=any", headers={"Authorization": AUTH})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n["elements"])


def write_tmp(name, data):
    path = os.path.join(os.environ.get("TEMP") or "/tmp", name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data if isinstance(data, str) else json.dumps(data))
    return path


def main():
    manifest = m2e.load_json(SAMPLE)
    slug = manifest["page"]["slug"]
    good = m2e.build(manifest)

    # 1. the good manifest: a draft, read back in the editor, left as a draft
    code, out = cli("push", SAMPLE)
    case("a good manifest is saved and the editor reads all 28 elements back", code == 0 and "EDITOR CHECK PASSED: 28 elements" in out, out)
    found = pages(slug)
    case("the verified page is still a draft", len(found) == 1 and found[0]["status"] == "draft", json.dumps([p.get("status") for p in found]))

    # 2. promote
    code, out = cli("push", SAMPLE, "--promote")
    case("a verified draft is promoted", code == 0 and "promoted:" in out, out)
    with urllib.request.urlopen(BASE + "/" + slug + "/", timeout=30) as resp:
        html = resp.read().decode("utf-8")
    case("the published page carries the generated heading", "Find out why your Amazon listings are not converting" in html and "elementor-heading-title" in html)

    # 3. trees the editor cannot keep are caught and the draft is deleted
    unknown = copy.deepcopy(good)
    next(n for n in walk(unknown) if n["elType"] == "widget")["widgetType"] = "nonexistent-widget"
    dup = copy.deepcopy(good)
    widgets = [n for n in walk(dup) if n["elType"] == "widget"]
    widgets[1]["id"] = widgets[0]["id"]
    for label, tree, bad_slug in (("an unknown widget type", unknown, "live-check-unknown"), ("a duplicate element id", dup, "live-check-duplicate")):
        code, out = cli("push-tree", write_tmp(bad_slug + ".json", m2e.tree_json(tree)), "--title", "Live check", "--slug", bad_slug)
        case(label + " fails the editor check", code == 1 and "EDITOR CHECK FAILED" in out, out)
        case(label + ": the draft is deleted, nothing is left or promoted", "deleted (200), nothing promoted" in out and pages(bad_slug) == [], out)

    # 4. a manifest that breaks the rules never reaches the site
    raw = copy.deepcopy(manifest)
    raw["page"]["slug"] = "live-check-raw-colour"
    raw["sections"][0]["background"] = "#ff0000"
    code, out = cli("push", write_tmp("live_raw.json", raw))
    case("a raw colour in a manifest is refused before any request", code == 1 and "REFUSED before any request" in out and pages("live-check-raw-colour") == [], out)

    # 5. what the route itself refuses
    def route(method, path, body=None, auth=AUTH):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = auth
        req = urllib.request.Request(BASE + "/wp-json/lab/v1" + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8") or "{}")

    tree_text = m2e.tree_json(good)
    legacy = copy.deepcopy(good)
    legacy[0]["elType"] = "section"
    refusals = [
        ("a legacy section element", ("POST", "/elementor-draft", {"title": "t", "slug": "live-check-a", "data_json": m2e.tree_json(legacy)}), 400),
        ("data that is not JSON", ("POST", "/elementor-draft", {"title": "t", "slug": "live-check-b", "data_json": "not json"}), 400),
        ("data that is not a list", ("POST", "/elementor-draft", {"title": "t", "slug": "live-check-c", "data_json": "{\"a\":1}"}), 400),
        ("data over a megabyte", ("POST", "/elementor-draft", {"title": "t", "slug": "live-check-d", "data_json": "[" + "0," * 600000 + "0]"}), 400),
        ("an empty title", ("POST", "/elementor-draft", {"title": "", "slug": "live-check-e", "data_json": tree_text}), 400),
        ("an empty slug", ("POST", "/elementor-draft", {"title": "t", "slug": "", "data_json": tree_text}), 400),
        ("the slug of a page it did not generate", ("POST", "/elementor-draft", {"title": "t", "slug": "seller-audit", "data_json": tree_text}), 409),
        ("deleting a page it did not generate", ("DELETE", "/elementor-draft/5", None), 404),
        ("promoting a page it did not generate", ("POST", "/elementor-draft/5/promote", {"verified_hash": "0" * 64}), 404),
    ]
    for label, (method, path, body), want in refusals:
        status, _ = route(method, path, body)
        case("the route refuses " + label + " with " + str(want), status == want, "got " + str(status))
    status, _ = route("POST", "/elementor-draft", {"title": "t", "slug": "x", "data_json": tree_text}, auth=None)
    case("the route refuses a request with no credentials with 401", status == 401, "got " + str(status))

    status, body = route("POST", "/elementor-draft", {"title": "Hash check", "slug": "live-check-hash", "data_json": tree_text})
    case("a draft is saved for the hash checks", status == 200, str(body))
    if status == 200:
        pid = body["id"]
        status, body2 = route("POST", "/elementor-draft/%d/promote" % pid, {"verified_hash": "0" * 64})
        case("a wrong hash is refused and nothing is published", status == 409 and pages("live-check-hash")[0]["status"] == "draft", str(body2))
        status, _ = route("POST", "/elementor-draft/%d/promote" % pid, {})
        case("a missing hash is refused", status == 409)
        status, _ = route("POST", "/elementor-draft/%d/promote" % pid, {"verified_hash": m2e.tree_hash(good)})
        case("the right hash promotes it", status == 200 and pages("live-check-hash")[0]["status"] == "publish")
        status, _ = route("DELETE", "/elementor-draft/%d" % pid)
        case("a published page is not deleted by the draft route", status == 409)
        req = urllib.request.Request(BASE + "/wp-json/wp/v2/pages/%d?force=true" % pid, method="DELETE", headers={"Authorization": AUTH})
        urllib.request.urlopen(req, timeout=30).read()
        case("the check page is cleaned up", pages("live-check-hash") == [])

    print("\n%d of %d checks passed" % (sum(RESULTS), len(RESULTS)))
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
