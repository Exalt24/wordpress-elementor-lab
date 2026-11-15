"""Breaks a copy of the child theme in known ways and checks that check_lab.py's offline checks notice each break.

A check that passes on a broken theme is a check that protects nothing, so every mutation below must make the run exit non-zero.
    python scripts/mutation_check.py
The real theme is never touched: each mutation runs on a temp copy of the lab.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (name, file inside child-theme, text to find, replacement)
MUTATIONS = [
    ("drop the Genesis bootstrap", "functions.php", "lib/init.php", "lib/nothing.php"),
    ("drop the case_study REST flag", "functions.php", "'show_in_rest' => true", "'show_in_rest' => false"),
    ("unregister the industry taxonomy", "functions.php", "register_taxonomy('industry'", "register_taxonomy('xindustry'"),
    ("stop saving ACF JSON", "functions.php", "acf/settings/save_json", "acf/settings/xsave_json"),
    ("rename a Genesis footer hook", "functions.php", "genesis_footer_creds_text", "genesis_footer_xcreds_text"),
    ("print the client name unescaped", "single-case_study.php", "esc_html(get_field('client_name'))", "get_field('client_name')"),
    ("rename an ACF field the theme reads", "acf-json/group_case_study.json", '"name": "client_name"', '"name": "client_nm"'),
    ("widen the ACF group to every post", "acf-json/group_case_study.json", '"value": "case_study"', '"value": "post"'),
    ("break the Genesis parent in style.css", "style.css", "Template: genesis", "Template: twentytwentyfour"),
]


def run_offline(lab: str) -> int:
    try:
        r = subprocess.run([sys.executable, os.path.join(lab, "scripts", "check_lab.py"), "--offline"],
                           capture_output=True, text=True, cwd=lab, timeout=60)
    except subprocess.TimeoutExpired:
        return 124  # a hung check counts as a failed check, never a pass
    return r.returncode


def main() -> int:
    baseline_dir = tempfile.mkdtemp(prefix="mut-base-")
    failed = []
    try:
        base = os.path.join(baseline_dir, "lab")
        shutil.copytree(ROOT, base, ignore=shutil.ignore_patterns("backups", "vendor", ".git", "*.psd"))
        if run_offline(base) != 0:
            print("BASELINE FAIL: the unbroken theme does not pass the offline checks")
            return 1
        print("PASS baseline: the unbroken theme passes")
        for name, rel, old, new in MUTATIONS:
            work = tempfile.mkdtemp(prefix="mut-")
            try:
                lab = os.path.join(work, "lab")
                shutil.copytree(base, lab)
                path = os.path.join(lab, "child-theme", rel)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                if old not in text:
                    print(f"FAIL {name}: the anchor text is not in {rel}, the mutation did not apply")
                    failed.append(name)
                    continue
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text.replace(old, new, 1))
                if run_offline(lab) != 0:
                    print(f"PASS {name}: the offline checks caught it")
                else:
                    print(f"FAIL {name}: the offline checks passed on a broken theme")
                    failed.append(name)
            finally:
                shutil.rmtree(work, ignore_errors=True)
    finally:
        shutil.rmtree(baseline_dir, ignore_errors=True)
    print(f"\n{len(MUTATIONS) - len(failed)}/{len(MUTATIONS)} mutations caught")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
