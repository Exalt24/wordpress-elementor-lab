"""Deliberate breakage check for the Moodle support lab.

    python moodle-lab/tests/mutation_check.py          the diagnosis and client breaks, against the offline tests (what CI runs)
    python moodle-lab/tests/mutation_check.py --live   also breaks each fix once and runs its live case against the running container

Copies the lab to a temporary folder, breaks one thing at a time and runs the matching tests there. A break counts as caught only when a test
goes red. The unbroken copy must pass first, and each break must match exactly one place in its file.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TRIAGE, CLIENT, CASES = "scripts/triage.py", "scripts/moodle_client.py", "scripts/cases.py"

# (file, name, text to break, replacement, tests to run: "offline" or "live <case>")
OFFLINE = [
    (TRIAGE, "enrolment check removed", "if user_id not in enrolled_user_ids:", "if False:"),
    (TRIAGE, "hidden course check removed", 'if not course["visible"]:', "if False:"),
    (TRIAGE, "lock flag ignored", 'if status["locked"]:', "if False:"),
    (TRIAGE, "any failed login reason counts", 'e["reason"] == AUTH_LOGIN_FAILED', "True"),
    (TRIAGE, "lockout window ignored", 'now - e["time"] <= status["window"]', "True"),
    (TRIAGE, "lockout code mixed up with the wrong password code", "AUTH_LOGIN_LOCKOUT = 4", "AUTH_LOGIN_LOCKOUT = 3"),
    (TRIAGE, "hidden activity check removed", 'if not module.get("visible"):', "if False:"),
    (TRIAGE, "future date never a cause", 'condition["t"] > now', "False"),
    (TRIAGE, "passed until date never a cause", 'condition["t"] <= now', "False"),
    (CLIENT, "nested values flattened wrongly", 'name = f"{prefix}[{key}]" if prefix else str(key)', "name = str(key)"),
    (CLIENT, "scripts counted as page text", 'self.skip += tag in ("script", "style")', "self.skip += 0"),
]
LIVE = [
    (CASES, "student never enrolled", 'def fix_enrol(lab, p):\n    lab.enrol(p["student_id"], p["course_id"])', "def fix_enrol(lab, p):\n    pass", "A1"),
    (CASES, "course made hidden instead of visible", '{"id": p["course_id"], "visible": 1}', '{"id": p["course_id"], "visible": 0}', "A2"),
    (CASES, "lockout read instead of cleared", 'return lab.shell.run("unlock", p["student"])', 'return lab.shell.run("lockout-status", p["student"])', "B"),
    (CASES, "restriction moved to tomorrow", "now - DAY", "now + DAY", "C1"),
    (CASES, "activity hidden instead of shown", 'action="show"', 'action="hide"', "C2"),
]


def tests_pass(folder, selector):
    args = ["offline"] if selector == "offline" else ["live", selector]
    done = subprocess.run([sys.executable, "-I", os.path.join(folder, "tests", "test_moodle_cases.py"), *args], cwd=folder,
                          capture_output=True, text=True, encoding="utf-8", timeout=600)
    return done.returncode == 0


def main():
    live = "--live" in sys.argv
    base = tempfile.mkdtemp(prefix="moodlemut_")
    try:
        clean = os.path.join(base, "clean")
        shutil.copytree(ROOT, clean, ignore=shutil.ignore_patterns("__pycache__", "docs"))
        if not tests_pass(clean, "offline"):
            print("FAIL  the unbroken copy does not pass its offline tests")
            return 1
        mutants = [(f, n, o, r, "offline") for f, n, o, r in OFFLINE]
        if live:
            for f, n, o, r, case in LIVE:
                if not tests_pass(clean, case):
                    print("FAIL  the unbroken copy does not pass live case " + case)
                    return 1
            mutants += [(f, n, o, r, case) for f, n, o, r, case in LIVE]
        caught = 0
        for i, (rel, name, old, new, selector) in enumerate(mutants):
            folder = os.path.join(base, "m%d" % i)
            shutil.copytree(clean, folder)
            path = os.path.join(folder, rel)
            with open(path, encoding="utf-8") as f:
                src = f.read()
            if src.count(old) != 1:
                print("FAIL  %s: the text to break matches %d places, not 1" % (name, src.count(old)))
                return 1
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(src.replace(old, new))
            red = not tests_pass(folder, selector)
            caught += red
            shutil.rmtree(folder, ignore_errors=True)
            print(("CAUGHT  " if red else "SURVIVED  ") + name + ("" if selector == "offline" else "   (live case %s)" % selector), flush=True)
        print("\n%d of %d breaks caught" % (caught, len(mutants)))
        return 0 if caught == len(mutants) else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
