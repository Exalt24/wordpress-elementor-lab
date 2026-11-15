"""Offline tests for the industry filter (no Docker, no browser): the PHP handler's text and the jQuery file, with mutation controls.

The filter's safety lives in a few lines: the nonce check and its 403, the slug sanitizing, the unknown-slug guard, the escaping of what is
printed, the jquery dependency and a script that talks to the server instead of reloading. scripts/check_filter.py reads the two files for each
of those. This test runs those checks on the real files (all must pass) and then on copies broken in the known ways from scripts/mutation_check.py
plus three more written here: every break must turn at least one check red, so a check that cannot fail cannot hide.
    python tests/test_cases_filter.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
failures: list[str] = []


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(LAB, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + ((" | " + detail) if detail and not ok else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    cf, mc = load("check_filter"), load("mutation_check")
    core, js = cf.read(cf.CORE), cf.read(cf.JS)
    php_all = "\n".join(cf.read(p) for p in cf.PHP_FILES)

    results = cf.file_checks(core, js, php_all)
    red = [n for n, ok in results if not ok]
    check(f"the real files pass all {len(results)} file checks", not red, "; ".join(red))
    check("the handler block is found and holds the nonce check", "check_ajax_referer" in cf.block(core, "function lab_core_ajax_filter_cases"))
    check("the check names are unique, so a failure names one thing", len({n for n, _ in results}) == len(results))

    # the harness's filter mutations, applied in memory: the filter's own checks must catch each one without help from any other check
    caught = 0
    mine = [m for m in mc.MUTATIONS if m[0].startswith("filter")]
    for name, _theme, rel, old, new in mine:
        text = (core if rel == cf.CORE else js).replace("\r\n", "\n")
        if old not in text:
            check(f"control {name}: the anchor is in the file", False, rel)
            continue
        broken = text.replace(old, new, 1)
        out = cf.file_checks(broken if rel == cf.CORE else core, broken if rel == cf.JS else js, php_all.replace(core, broken) if rel == cf.CORE else php_all)
        names = [n for n, ok in out if not ok]
        check(f"control {name}: {len(names)} check(s) turn red", bool(names))
        caught += 1 if names else 0
    check(f"every one of the {len(mine)} filter mutations is caught by the file checks", caught == len(mine) and len(mine) >= 10, f"{caught}/{len(mine)}")

    extra = [
        ("run the query before the nonce check", core, "if (!check_ajax_referer('lab_core_filter', 'nonce', false)) {",
         "lab_core_cases_query();\n    if (!check_ajax_referer('lab_core_filter', 'nonce', false)) {"),
        ("read the slug from $_REQUEST", core, "$_POST['industry']", "$_REQUEST['industry']"),
        ("a second error path that leaks for an unknown slug", core, "$posts = [];", "$posts = [];\n    if ($slug === 'x') { wp_send_json_error(['message' => $slug], 404); }"),
    ]
    for name, _t, old, new in extra:
        out = cf.file_checks(core.replace(old, new, 1), js, php_all)
        check(f"control {name}: a check turns red", any(not ok for _, ok in out) and old in core)

    print(f"\n{caught}/{len(mine)} filter mutations caught, {len(extra)} extra controls")
    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
