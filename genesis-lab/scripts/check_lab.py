"""Checks the lab end to end against the running DEV (8091) and PROD (8092) sites.

The lab has one set of functionality (mu-plugins/lab-core.php) and two child themes: lab-child on the Genesis Framework and lab-classic on a
plain Twenty Twenty-One parent. The theme under test is the one setup.sh wrote to .theme, or --theme <name>.
Offline checks read the files and need no Docker. Live checks fetch the pages, ask WP-CLI about the database and exercise the sync:
PROD must show DEV's content with every address rewritten, and a hostile case study must come out escaped.
The industry filter has its own file checks (scripts/check_filter.py), run from here too, and its own live run in a browser (python scripts/check_filter.py).
    python scripts/check_lab.py            both
    python scripts/check_lab.py --offline  only the file checks
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

import check_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV, PROD = "http://localhost:8091", "http://localhost:8092"
failures: list[str] = []

THEMES = {  # theme name -> (folder, parent, front page hook, footer text, footer marker in the HTML, footer hook)
    "lab-child": ("child-theme", "genesis", "genesis_before_loop", "Lab Child on Genesis", "genesis", "genesis_footer_creds_text"),
    "lab-classic": ("classic-child", "twentytwentyone", "loop_start", "Lab Classic on a plain parent theme", "twenty", "wp_footer"),
}


def pick_theme() -> str:
    if "--theme" in sys.argv:
        return sys.argv[sys.argv.index("--theme") + 1]
    path = os.path.join(ROOT, ".theme")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    return "lab-classic"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail and not ok else ""))
    if not ok:
        failures.append(name)


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def offline(theme: str) -> None:
    folder, parent, hook, footer, _, footer_hook = THEMES[theme]
    core, css, fn = read("mu-plugins/lab-core.php"), read(f"{folder}/style.css"), read(f"{folder}/functions.php")
    check(f"{theme}: style.css names {parent} as the parent", bool(re.search(r"^\s*Template:\s*%s\s*$" % re.escape(parent), css, re.M)))
    if parent == "genesis":
        check(f"{theme}: functions.php loads the Genesis bootstrap", "lib/init.php" in fn)
    post_type = core[core.find("register_post_type('case_study'"):core.find("register_taxonomy(")]  # only the case_study block counts
    check("a case_study post type is registered with REST on", "register_post_type('case_study'" in core and "'show_in_rest' => true" in post_type)
    check("an industry taxonomy is registered", "register_taxonomy('industry'" in core)
    check("ACF JSON is saved and loaded next to the plugin", "acf/settings/save_json" in core and "acf/settings/load_json" in core)
    card = core[core.find("function lab_core_render_card"):core.find("/** How many cards a grid shows")]   # the card renderer on its own, so the filter's escapes cannot cover for it
    content_filter = core[core.find("add_filter('the_content'"):]
    check("each printed value is escaped", card.count("esc_html(") >= 3 and "esc_url(" in card and "esc_html($result)" in content_filter)
    check("no unescaped echo of a field", not re.search(r"echo\s+\$(client|result|post->post_title)\b", core + fn))
    check("the init action, the excerpt filter and the content filter are all registered",
          "add_action('init'" in core and "add_filter('excerpt_length'" in core and "add_filter('the_content'" in core)
    check(f"{theme}: the front page cards are placed with the parent's hook {hook}", f"'{hook}'" in fn and "lab_core_front_cards" in fn)
    check(f"{theme}: the footer credit line is its own", footer in fn)
    check(f"{theme}: the footer credit is placed with the parent's footer hook {footer_hook}", f"add_filter('{footer_hook}'" in fn or f"add_action('{footer_hook}'" in fn)
    check("the theme keeps no case study logic of its own", "register_post_type" not in fn and "get_field" not in fn)
    group = json.loads(read("mu-plugins/lab-core-acf-json/group_case_study.json"))
    names = {f["name"] for f in group["fields"]}
    check("the ACF group holds the two fields the plugin reads", names == {"client_name", "headline_result"})
    check("every ACF field key is unique and prefixed", len({f["key"] for f in group["fields"]}) == len(group["fields"]) and all(f["key"].startswith("field_") for f in group["fields"]))
    check("the ACF group is limited to the case study type", group["location"][0][0]["value"] == "case_study")
    for name, ok in check_filter.offline_checks():   # the industry filter's own file checks, kept in scripts/check_filter.py
        check("filter: " + name, ok)


def get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def wp(site: str, *args: str) -> str:
    cli = "cli-dev" if site == "dev" else "cli-prod"
    try:
        r = subprocess.run(["docker", "compose", "--profile", "tools", "run", "--rm", "-T", cli, "wp", "--path=/var/www/html", *args],
                           cwd=ROOT, capture_output=True, text=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"}, timeout=120)
    except subprocess.TimeoutExpired:
        return ""   # a hung WP-CLI call is an empty answer, and every check that needs one fails
    return (r.stdout or "").strip()


def live(theme: str) -> None:
    _, _, _, footer, marker, _ = THEMES[theme]
    results = ["Duplicate listings fell from one in four to one in twenty.", "No-shows dropped by a third in the first month.",
               "Quote requests doubled after the form went from nine fields to four."]
    for label, base in (("DEV", DEV), ("PROD", PROD)):
        code, html = get(base + "/")
        check(f"{label} front page answers 200", code == 200, str(code))
        check(f"{label} front page shows all three headline results", all(r in html for r in results))
        check(f"{label} front page carries the theme's footer credit", footer in html)
        check(f"{label} front page carries the parent theme's markup", marker in html.lower())
        code, _arc = get(base + "/case-studies/")
        check(f"{label} case study archive answers 200", code == 200, str(code))
    code, html = get(PROD + "/")
    check("PROD pages carry no DEV address", "localhost:8091" not in html)
    check("PROD home option is PROD's own address", wp("prod", "option", "get", "home") == PROD)
    check("PROD keeps its own site name after the sync", wp("prod", "option", "get", "blogname") == "Lab PROD")
    check("PROD runs the same theme as DEV", wp("prod", "theme", "list", "--status=active", "--field=name") == theme)
    check("DEV and PROD hold the same number of case studies",
          wp("dev", "post", "list", "--post_type=case_study", "--format=count") == wp("prod", "post", "list", "--post_type=case_study", "--format=count"))
    slug = wp("prod", "post", "list", "--post_type=case_study", "--field=post_name").splitlines()[0]
    code, single = get(f"{PROD}/case-studies/{slug}/")
    check("a PROD single case study answers 200", code == 200, str(code))
    check("the single page puts the headline result first", bool(re.search(r"case-result", single)))
    # a hostile client name on DEV must come out escaped
    pid = wp("dev", "post", "create", "--post_type=case_study", "--post_title=Hostile <script>alert(1)</script>", "--post_status=publish", "--porcelain").splitlines()[-1]
    wp("dev", "post", "meta", "update", pid, "client_name", "<img src=x onerror=alert(2)>")
    wp("dev", "post", "meta", "update", pid, "headline_result", "<script>alert(3)</script>")
    code, html = get(DEV + "/")
    # the escaped form still contains the words onerror=alert as text, so the test looks for the raw TAGS being gone and the escaped tags being there
    check("a hostile title and fields print escaped on DEV",
          "<script>alert" not in html and "<img src=x" not in html and "&lt;script&gt;" in html and "&lt;img src=x" in html)
    wp("dev", "post", "delete", pid, "--force")
    backups = os.listdir(os.path.join(ROOT, "backups")) if os.path.isdir(os.path.join(ROOT, "backups")) else []
    check("a dated PROD backup was written before the sync", any(f.startswith("prod-") for f in backups))


if __name__ == "__main__":
    chosen = pick_theme()
    if chosen not in THEMES:
        sys.exit("unknown theme %s" % chosen)
    offline(chosen)
    if "--offline" not in sys.argv:
        live(chosen)
    print("\n%d failure(s)" % len(failures))
    sys.exit(1 if failures else 0)
