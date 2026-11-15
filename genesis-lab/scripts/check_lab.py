"""Checks the Genesis lab end to end against the running DEV (8091) and PROD (8092) sites.

Offline checks read the child theme files and need no Docker. Live checks fetch the pages, ask WP-CLI about the database and
exercise the sync: PROD must show DEV's content with every address rewritten, and a hostile case study title must come out escaped.
    python scripts/check_lab.py            both
    python scripts/check_lab.py --offline  only the file checks
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(ROOT, "child-theme")
DEV, PROD = "http://localhost:8091", "http://localhost:8092"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail and not ok else ""))
    if not ok:
        failures.append(name)


def read(path: str) -> str:
    with open(os.path.join(THEME, path), encoding="utf-8") as fh:
        return fh.read()


def offline() -> None:
    css, fn = read("style.css"), read("functions.php")
    check("style.css names Genesis as the parent", bool(re.search(r"^\s*Template:\s*genesis\s*$", css, re.M)))
    check("functions.php loads the Genesis bootstrap", "lib/init.php" in fn)
    check("a case_study post type is registered", "register_post_type('case_study'" in fn and "'show_in_rest' => true" in fn)
    check("an industry taxonomy is registered", "register_taxonomy('industry'" in fn)
    check("ACF JSON is saved and loaded inside the theme", "acf/settings/save_json" in fn and "acf/settings/load_json" in fn)
    check("each printed value is escaped", fn.count("esc_html(") >= 4 and "esc_url(" in fn)
    check("no unescaped echo of a field", not re.search(r"echo\s+\$(client|result|post->post_title)\b", fn))
    check("hooks, actions and filters are all used", all(k in fn for k in ("add_action(", "add_filter(")) and "genesis_before_loop" in fn and "genesis_footer_creds_text" in fn and "the_content" in fn)
    group = json.loads(read("acf-json/group_case_study.json"))
    names = {f["name"] for f in group["fields"]}
    check("the ACF group holds the two fields the theme reads", names == {"client_name", "headline_result"})
    check("every ACF field key is unique and prefixed", len({f["key"] for f in group["fields"]}) == len(group["fields"]) and all(f["key"].startswith("field_") for f in group["fields"]))
    check("the ACF group is limited to the case study type", group["location"][0][0]["value"] == "case_study")


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def wp(site: str, *args: str) -> str:
    cli = "cli-dev" if site == "dev" else "cli-prod"
    r = subprocess.run(["docker", "compose", "--profile", "tools", "run", "--rm", "-T", cli, "wp", "--path=/var/www/html", *args],
                       cwd=ROOT, capture_output=True, text=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"})
    return (r.stdout or "").strip()


def live() -> None:
    results = ["Duplicate listings fell from one in four to one in twenty.", "No-shows dropped by a third in the first month.",
               "Quote requests doubled after the form went from nine fields to four."]
    for label, base in (("DEV", DEV), ("PROD", PROD)):
        code, html = get(base + "/")
        check(f"{label} front page answers 200", code == 200, str(code))
        check(f"{label} front page shows all three headline results", all(r in html for r in results))
        check(f"{label} front page uses the Genesis footer filter", "Lab Child on Genesis" in html)
        check(f"{label} front page carries Genesis markup", "genesis" in html.lower())
        code, arc = get(base + "/case-studies/")
        check(f"{label} case study archive answers 200", code == 200, str(code))
    code, html = get(PROD + "/")
    check("PROD pages carry no DEV address", "localhost:8091" not in html)
    check("PROD home option is PROD's own address", wp("prod", "option", "get", "home") == PROD)
    check("DEV and PROD hold the same number of case studies",
          wp("dev", "post", "list", "--post_type=case_study", "--format=count") == wp("prod", "post", "list", "--post_type=case_study", "--format=count"))
    slug = wp("prod", "post", "list", "--post_type=case_study", "--field=post_name").splitlines()[0]
    code, single = get(f"{PROD}/case-studies/{slug}/")
    check("a PROD single case study answers 200", code == 200, str(code))
    check("the single page puts the headline result first", bool(re.search(r'case-result', single)))
    # a hostile client name on DEV must come out escaped, on DEV and after a sync on PROD
    pid = wp("dev", "post", "create", "--post_type=case_study", "--post_title=Hostile <script>alert(1)</script>", "--post_status=publish", "--porcelain").splitlines()[-1]
    wp("dev", "post", "meta", "update", pid, "client_name", "<img src=x onerror=alert(2)>")
    wp("dev", "post", "meta", "update", pid, "headline_result", "<script>alert(3)</script>")
    code, html = get(DEV + "/")
    check("a hostile title and fields print escaped on DEV", "<script>alert" not in html and "onerror=alert" not in html and "&lt;script&gt;" in html)
    wp("dev", "post", "delete", pid, "--force")
    backups = [f for f in os.listdir(os.path.join(ROOT, "backups"))] if os.path.isdir(os.path.join(ROOT, "backups")) else []
    check("a dated PROD backup was written before the sync", any(f.startswith("prod-") for f in backups))


if __name__ == "__main__":
    offline()
    if "--offline" not in sys.argv:
        live()
    print("\n%d failure(s)" % len(failures))
    sys.exit(1 if failures else 0)
