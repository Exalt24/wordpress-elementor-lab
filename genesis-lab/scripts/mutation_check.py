"""Breaks a copy of the lab in known ways and checks that check_lab.py's offline checks notice each break.

A check that passes on a broken lab is a check that protects nothing, so every mutation below must make the run exit non-zero. The same
checks run for both themes, so each theme gets its own set of theme mutations.
    python scripts/mutation_check.py
The real lab is never touched: each mutation runs on a temp copy.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CORE = "mu-plugins/lab-core.php"
ACF = "mu-plugins/lab-core-acf-json/group_case_study.json"
# (name, theme the check runs for, file inside the lab, text to find, replacement)
MUTATIONS = [
    ("drop the case_study REST flag", "lab-classic", CORE, "'show_in_rest' => true,\n        'menu_icon'", "'show_in_rest' => false,\n        'menu_icon'"),
    ("unregister the industry taxonomy", "lab-classic", CORE, "register_taxonomy('industry'", "register_taxonomy('xindustry'"),
    ("stop saving ACF JSON", "lab-classic", CORE, "acf/settings/save_json", "acf/settings/xsave_json"),
    ("print the headline result unescaped", "lab-classic", CORE, "esc_html($result) . '</p>' . $content", "$result . '</p>' . $content"),
    ("drop the content filter", "lab-classic", CORE, "add_filter('the_content'", "add_filter('xthe_content'"),
    ("rename an ACF field the plugin reads", "lab-classic", ACF, '"name": "client_name"', '"name": "client_nm"'),
    ("widen the ACF group to every post", "lab-classic", ACF, '"value": "case_study"', '"value": "post"'),
    ("classic: break the parent in style.css", "lab-classic", "classic-child/style.css", "Template:     twentytwentyone", "Template:     twentytwentyfour"),
    ("classic: rename the loop hook", "lab-classic", "classic-child/functions.php", "add_action('loop_start'", "add_action('xloop_start'"),
    ("classic: put case study logic back in the theme", "lab-classic", "classic-child/functions.php", "/** The footer credit line. */", "register_post_type('x', []);"),
    ("genesis: drop the bootstrap", "lab-child", "child-theme/functions.php", "lib/init.php", "lib/nothing.php"),
    ("genesis: rename the footer hook", "lab-child", "child-theme/functions.php", "genesis_footer_creds_text", "genesis_footer_xcreds_text"),
    ("genesis: break the parent in style.css", "lab-child", "child-theme/style.css", "Template:     genesis", "Template:     twentytwentyfour"),
]


def run_offline(lab: str, theme: str) -> int:
    try:
        r = subprocess.run([sys.executable, os.path.join(lab, "scripts", "check_lab.py"), "--offline", "--theme", theme],
                           capture_output=True, text=True, cwd=lab, timeout=60)
    except subprocess.TimeoutExpired:
        return 124  # a hung check counts as a failed check, never a pass
    return r.returncode


def main() -> int:
    baseline_dir = tempfile.mkdtemp(prefix="mut-base-")
    failed = []
    try:
        base = os.path.join(baseline_dir, "lab")
        shutil.copytree(ROOT, base, ignore=shutil.ignore_patterns("backups", "vendor", ".git", "*.psd", ".theme"))
        for theme in ("lab-classic", "lab-child"):
            if run_offline(base, theme) != 0:
                print(f"BASELINE FAIL: the unbroken lab does not pass the offline checks for {theme}")
                return 1
            print(f"PASS baseline: the unbroken lab passes for {theme}")
        for name, theme, rel, old, new in MUTATIONS:
            work = tempfile.mkdtemp(prefix="mut-")
            try:
                lab = os.path.join(work, "lab")
                shutil.copytree(base, lab)
                path = os.path.join(lab, rel)
                with open(path, encoding="utf-8", newline="") as fh:
                    text = fh.read().replace("\r\n", "\n")
                if old not in text:
                    print(f"FAIL {name}: the anchor text is not in {rel}, the mutation did not apply")
                    failed.append(name)
                    continue
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text.replace(old, new, 1))
                if run_offline(lab, theme) != 0:
                    print(f"PASS {name}: the offline checks caught it")
                else:
                    print(f"FAIL {name}: the offline checks passed on a broken lab")
                    failed.append(name)
            finally:
                shutil.rmtree(work, ignore_errors=True)
    finally:
        shutil.rmtree(baseline_dir, ignore_errors=True)
    print(f"\n{len(MUTATIONS) - len(failed)}/{len(MUTATIONS)} mutations caught")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
