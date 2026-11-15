"""Checks the industry filter on the front page: the file checks (no Docker) and the live run against DEV (8091).

The filter is a jQuery script (mu-plugins/lab-core-assets/cases-filter.js) that asks an admin-ajax handler in mu-plugins/lab-core.php for one
industry's cards. Both themes get it, because the cards, the script and the handler live in the shared plugin and each theme only calls
lab_core_front_cards() from its own hook. DEV runs the theme that setup.sh wrote to .theme (lab-classic unless THEME=lab-child was used).
    python scripts/check_filter.py            file checks, then the live run in a real browser (needs setup.sh and Node with Playwright)
    python scripts/check_filter.py --offline  only the file checks
check_lab.py runs file_checks() too, so the mutation harness breaks the filter files and sees the same checks go red.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = "http://localhost:8091"
PHP_FILES = ("mu-plugins/lab-core.php", "child-theme/functions.php", "classic-child/functions.php", "child-theme/front-page.php")
CORE, JS = "mu-plugins/lab-core.php", "mu-plugins/lab-core-assets/cases-filter.js"


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def block(text: str, start: str) -> str:
    """The body of the PHP function that begins at `start`, up to its closing brace at column zero."""
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find("\n}\n", i)
    return text[i:j + 3] if j > 0 else text[i:]


def file_checks(core: str, js: str, php_all: str) -> list[tuple[str, bool]]:
    """Every file check as (name, passed), over the text it is given, so a test can hand it a deliberately broken copy."""
    h = block(core, "function lab_core_ajax_filter_cases")
    nonce_call = re.search(r"if \(!check_ajax_referer\(", h)   # the call itself, so a renamed or commented-out copy does not count
    q = block(core, "function lab_core_cases_query")
    bar = block(core, "function lab_core_filter_bar")
    enq = core[core.find("add_action('wp_enqueue_scripts'"):core.find("function lab_core_ajax_filter_cases")] if "add_action('wp_enqueue_scripts'" in core else ""
    return [
        ("handler: the nonce is checked with a real call to check_ajax_referer", nonce_call is not None and "'lab_core_filter', 'nonce', false" in h),
        ("handler: a bad nonce is answered 403 with a JSON error", bool(re.search(r"wp_send_json_error\([^;]*,\s*403\)", h)) and nonce_call is not None),
        ("handler: the nonce check comes before any query", nonce_call is not None and nonce_call.start() < h.find("lab_core_cases_query")),
        ("handler: the slug goes through sanitize_title", "sanitize_title(" in h),
        ("handler: an unknown industry is an empty result (term_exists guards the query)", "$raw === '' ||" in h and "($slug !== '' && term_exists($slug, 'industry'))" in h and "wp_send_json_error" in h and h.count("wp_send_json_error") == 1),
        ("handler: every printed value is escaped", h.count("esc_html(") >= 2 and not re.search(r"echo\s+\$", h)),
        ("handler: the answer is JSON (wp_send_json_success)", "wp_send_json_success(" in h),
        ("handler: reads only POST input, as a string", "$_POST['industry']" in h and "is_string(" in h and "$_GET" not in h and "$_REQUEST" not in h),
        ("handler: hooked for signed in and signed out visitors", "add_action('wp_ajax_lab_core_filter_cases'" in core and "add_action('wp_ajax_nopriv_lab_core_filter_cases'" in core),
        ("query: the industry goes in through a WP_Query tax_query", "new WP_Query(" in q and "'tax_query'" in q and "'taxonomy' => 'industry'" in q),
        ("query: only published case studies, named explicitly (admin-ajax counts as admin and would show drafts)", "'post_status' => 'publish'" in q),
        ("cards: titles and links are escaped where they print", "esc_url(get_permalink" in core and "esc_html(get_the_title" in core),
        ("buttons: real button elements with aria-pressed and a type", bar.count("<button type=\"button\"") == 2 and "aria-pressed" in bar and "<div class=\"case-filter\"" in bar and "<span" not in bar and "<a " not in bar),
        ("buttons: the bar starts hidden so a page without JavaScript shows no dead buttons", re.search(r"case-filter[^']{0,200}\bhidden>", bar) is not None),
        ("page: the full grid is rendered by the server on first load", "id=\"lab-case-grid\"" in core and "lab_core_cases_query()" in block(core, "function lab_core_front_cards")),
        ("enqueue: jquery is a dependency of the script", re.search(r"wp_enqueue_script\('lab-core-filter',[^;]*\['jquery'\]", enq) is not None),
        ("enqueue: the ajax address and the nonce come through wp_localize_script", "wp_localize_script('lab-core-filter', 'labCoreFilter'" in enq and "admin_url('admin-ajax.php')" in enq and "wp_create_nonce('lab_core_filter')" in enq),
        ("enqueue: jQuery is WordPress's own copy, no CDN anywhere", "http://" not in enq and "https://" not in enq and "//code.jquery" not in js),
        ("php: no inline script blob in any PHP file", "<script" not in php_all.lower()),
        ("js: runs inside jQuery(function ($)", "jQuery(function ($)" in js),
        ("js: talks to the server with $.ajax and reads JSON", "$.ajax(" in js and "dataType: 'json'" in js and "cfg.nonce" in js and "cfg.ajaxUrl" in js),
        ("js: no page reload or navigation anywhere", not re.search(r"location\s*(\.\s*(reload|href|assign|replace)|\s*=)|history\.go|submit\(", js)),
        ("js: shows a loading state", "aria-busy', 'true'" in js and "Loading case studies" in js),
        ("js: shows an error message when the request fails", ".fail(" in js and "is-error" in js and "could not be loaded" in js),
        ("js: keeps aria-pressed in step with the grid", "attr('aria-pressed', 'true')" in js and "attr('aria-pressed', 'false')" in js),
        ("js: the bar is shown only by the script", "prop('hidden', false)" in js),
        ("js: the answer is inserted from the server's HTML, never built from the request", "$grid.html(res.data.html)" in js and "industry +" not in js),
    ]


def offline_checks() -> list[tuple[str, bool]]:
    return file_checks(read(CORE), read(JS), "\n".join(read(p) for p in PHP_FILES))


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8")), r.headers


def wp(*args: str) -> str:
    try:
        r = subprocess.run(["docker", "compose", "--profile", "tools", "run", "--rm", "-T", "cli-dev", "wp", "--path=/var/www/html", *args],
                           cwd=ROOT, capture_output=True, text=True, env={**os.environ, "MSYS_NO_PATHCONV": "1"}, timeout=120)
    except subprocess.TimeoutExpired:
        return ""
    return (r.stdout or "").strip()


def live() -> int:
    """Adds two published case studies and one draft to an industry for the run (the sample data has one per industry, so a filter that
    returned 'everything' or 'one' would look right), runs the browser checks, and always deletes them again."""
    made = []
    try:
        for title, status in (("Filter check A (temporary)", "publish"), ("Filter check B (temporary)", "publish"), ("Filter check draft (temporary)", "draft")):
            pid = wp("post", "create", "--post_type=case_study", f"--post_title={title}", f"--post_status={status}", "--porcelain").splitlines()[-1:]
            if pid and pid[0].isdigit():
                made.append(pid[0])
                wp("post", "term", "set", pid[0], "industry", "Healthcare")
        print(f"temporary case studies for the run: {len(made)} made (two published, one draft, all in Healthcare)")
        with tempfile.TemporaryDirectory() as scratch:
            code = browser_run(scratch)
    finally:
        for pid in made:
            wp("post", "delete", pid, "--force")
    # the two screenshots kept in docs/ are taken on the sample data alone, so no temporary title is in them
    r = subprocess.run(["node", os.path.join(ROOT, "scripts", "check_filter.cjs"), DEV, os.path.join(ROOT, "docs"), json.dumps(rest_oracle()), "--shots-only"], text=True, capture_output=True, timeout=120)
    print("screenshots docs/filter-wide.png and docs/filter-phone.png written" if r.returncode == 0 else "SCREENSHOTS FAILED " + r.stderr)
    return code or r.returncode


def rest_oracle() -> dict:
    terms, _ = get_json(DEV + "/wp-json/wp/v2/industry?per_page=100&hide_empty=true")
    _, headers = get_json(DEV + "/wp-json/wp/v2/case_study?per_page=1")
    return {"total": int(headers["X-WP-Total"]), "terms": [{"slug": t["slug"], "name": t["name"], "count": t["count"]} for t in terms if t["count"] > 0]}


def browser_run(out: str) -> int:
    oracle = rest_oracle()
    print(f"oracle from the REST API: {oracle['total']} case studies, industries {[(t['slug'], t['count']) for t in oracle['terms']]}")
    r = subprocess.run(["node", os.path.join(ROOT, "scripts", "check_filter.cjs"), DEV, out, json.dumps(oracle)], text=True, capture_output=True, timeout=240)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    passed = sum(1 for line in r.stdout.splitlines() if line.startswith("PASS "))
    failed = sum(1 for line in r.stdout.splitlines() if line.startswith("FAIL "))
    print(f"\nlive: {passed} passed, {failed} failed")
    return 1 if r.returncode or failed or passed == 0 else 0


if __name__ == "__main__":
    bad = 0
    results = offline_checks()
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)
        bad += 0 if ok else 1
    print(f"\nfile checks: {len(results) - bad} passed, {bad} failed")
    if "--offline" not in sys.argv:
        bad += live()
    sys.exit(1 if bad else 0)
