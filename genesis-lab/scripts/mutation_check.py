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
JS = "mu-plugins/lab-core-assets/cases-filter.js"
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
    # the industry filter: the ajax handler in lab-core.php and its jQuery script
    ("filter: remove the nonce check", "lab-classic", CORE, "!check_ajax_referer(", "!xcheck_ajax_referer("),
    ("filter: answer a bad nonce with 200 instead of 403", "lab-classic", CORE, "Reload it and try again.'], 403);", "Reload it and try again.'], 200);"),
    ("filter: remove the sanitize call", "lab-classic", CORE, "sanitize_title(wp_unslash($raw))", "wp_unslash($raw)"),
    ("filter: print the empty-state message unescaped", "lab-classic", CORE, "esc_html($slug === ''", "($slug === ''"),
    ("filter: echo the slug in the JSON unescaped", "lab-classic", CORE, "'industry' => esc_html($slug)", "'industry' => $slug"),
    ("filter: query an unchecked slug (no term_exists guard)", "lab-classic", CORE, "($raw === '' || ($slug !== '' && term_exists($slug, 'industry')))", "(true)"),
    ("filter: a slug that sanitizes to nothing returns every case study", "lab-classic", CORE, "($raw === '' || ", "($slug === '' || "),
    ("filter: drop the explicit published status (drafts leak through admin-ajax)", "lab-classic", CORE, "'post_status' => 'publish', ", ""),
    ("filter: drop the tax_query", "lab-classic", CORE, "'tax_query'", "'xtax_query'"),
    ("filter: unhook the signed out visitors", "lab-classic", CORE, "add_action('wp_ajax_nopriv_lab_core_filter_cases'", "add_action('wp_ajax_nopriv_xlab_core_filter_cases'"),
    ("filter: stop passing the nonce to the script", "lab-classic", CORE, "'nonce' => wp_create_nonce('lab_core_filter'),", "'nonce' => '',"),
    ("filter: drop jquery from the script dependencies", "lab-classic", CORE, "cases-filter.js', ['jquery']", "cases-filter.js', []"),
    ("filter: put an inline script blob in PHP", "lab-classic", CORE, "wp_reset_postdata();\n    echo '</div>';", "wp_reset_postdata();\n    echo '</div><script>var x = 1;</script>';"),
    ("filter: show the bar without JavaScript (no hidden attribute)", "lab-classic", CORE, 'by industry" hidden>', 'by industry">'),
    ("filter: use a span where a button belongs", "lab-classic", CORE, "echo '<button type=\"button\" class=\"case-filter-button\" aria-pressed=\"false\"", "echo '<span class=\"case-filter-button\" aria-pressed=\"false\""),
    ("filter js: reload the page instead of asking the server", "lab-classic", JS, "return $.ajax({", "return window.location.reload({"),
    ("filter js: stop updating aria-pressed", "lab-classic", JS, "$button.attr('aria-pressed', 'true');", "$button.attr('xaria-pressed', 'true');"),
    ("filter js: drop the failure handler", "lab-classic", JS, "xhr.fail(function", "xhr.xfail(function"),
    ("filter js: drop the loading state", "lab-classic", JS, "$grid.attr('aria-busy', 'true');", "$grid.attr('aria-busy', 'false');"),
    ("filter js: leave the bar hidden", "lab-classic", JS, "$bar.prop('hidden', false);", "$bar.prop('hidden', true);"),
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
