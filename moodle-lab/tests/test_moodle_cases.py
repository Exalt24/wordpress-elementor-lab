"""Tests for the Moodle support lab.

    python moodle-lab/tests/test_moodle_cases.py            offline checks, then the live cases when the lab Moodle is running (otherwise they are skipped)
    python moodle-lab/tests/test_moodle_cases.py offline    offline checks only (what CI runs)
    python moodle-lab/tests/test_moodle_cases.py live       live cases only; exits 1 if the container is not running
    python moodle-lab/tests/test_moodle_cases.py live A1    one live case (A1 A2 B C1 C2)

The offline checks feed the diagnosis functions facts with exactly one cause each. The live checks run each case against the real container and
check the result the way the student sees it: a login, the My courses list, the activity's own page.
"""
import json
import os
import secrets
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import cases  # noqa: E402
import moodle_client  # noqa: E402
import triage  # noqa: E402

failed = 0
skipped = 0
NOW = 1_800_000_000


def check(name, ok, detail=""):
    global failed
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else "   <- " + str(detail)))
    failed += 0 if ok else 1


def offline_tests():
    course = {"visible": 1}
    check("A: a student missing from the enrolled users is NOT_ENROLLED", triage.diagnose_missing_course(7, course, [3, 4]) == "NOT_ENROLLED")
    check("A: an enrolled student in a hidden course is COURSE_HIDDEN", triage.diagnose_missing_course(7, {"visible": 0}, [3, 7]) == "COURSE_HIDDEN")
    check("A: not enrolled outranks hidden, the enrolment is fixed first", triage.diagnose_missing_course(7, {"visible": 0}, [3]) == "NOT_ENROLLED")
    check("A: enrolled in a visible course is NO_CAUSE_FOUND", triage.diagnose_missing_course(7, course, [7]) == "NO_CAUSE_FOUND")

    def status(locked=False, events=()):
        return {"locked": locked, "failed_login_events": list(events), "window": 600, "threshold": 3}

    check("B: the lock flag set is LOCKED_OUT", triage.diagnose_lockout(status(locked=True), NOW) == "LOCKED_OUT")
    check("B: recent wrong passwords with no lock are WRONG_PASSWORDS_BELOW_LIMIT",
          triage.diagnose_lockout(status(events=[{"time": NOW - 30, "reason": triage.AUTH_LOGIN_FAILED}]), NOW) == "WRONG_PASSWORDS_BELOW_LIMIT")
    check("B: a wrong password older than the window does not count",
          triage.diagnose_lockout(status(events=[{"time": NOW - 601, "reason": triage.AUTH_LOGIN_FAILED}]), NOW) == "NO_FAILED_LOGINS_LOGGED")
    check("B: a refusal because of the lock is not a wrong password",
          triage.diagnose_lockout(status(events=[{"time": NOW - 30, "reason": triage.AUTH_LOGIN_LOCKOUT}]), NOW) == "NO_FAILED_LOGINS_LOGGED")
    check("B: no failed logins logged is NO_FAILED_LOGINS_LOGGED", triage.diagnose_lockout(status(), NOW) == "NO_FAILED_LOGINS_LOGGED")

    def module(visible=1, availability=None):
        return {"visible": visible, "availability": json.dumps(availability) if availability else None}

    future = {"op": "&", "c": [{"type": "date", "d": ">=", "t": NOW + 1000}], "showc": [True]}
    past_from = {"op": "&", "c": [{"type": "date", "d": ">=", "t": NOW - 1000}], "showc": [True]}
    closed = {"op": "&", "c": [{"type": "date", "d": "<", "t": NOW - 1000}], "showc": [True]}
    check("C: a hidden activity is HIDDEN", triage.diagnose_activity(module(visible=0), NOW) == ("HIDDEN", None))
    check("C: a hidden activity with a date is still HIDDEN first", triage.diagnose_activity(module(visible=0, availability=future), NOW)[0] == "HIDDEN")
    check("C: a date in the future is DATE_NOT_REACHED with that date", triage.diagnose_activity(module(availability=future), NOW) == ("DATE_NOT_REACHED", NOW + 1000))
    check("C: a 'from' date already passed is not a cause", triage.diagnose_activity(module(availability=past_from), NOW) == ("NO_CAUSE_FOUND", None))
    check("C: an 'until' date that passed is DATE_PASSED", triage.diagnose_activity(module(availability=closed), NOW) == ("DATE_PASSED", NOW - 1000))
    check("C: a visible activity with no restriction is NO_CAUSE_FOUND", triage.diagnose_activity(module(), NOW) == ("NO_CAUSE_FOUND", None))

    flat = moodle_client.flatten({"users": [{"username": "a", "preferences": [{"type": "x", "value": "1"}]}], "id": 3})
    check("client: nested values use Moodle's users[0][username] encoding",
          flat == {"users[0][username]": "a", "users[0][preferences][0][type]": "x", "users[0][preferences][0][value]": "1", "id": 3}, flat)
    check("client: page_text drops tags, scripts and styles",
          moodle_client.page_text("<style>p{}</style><h1>Hello <b>there</b></h1><script>var x=1</script><p>Bye</p>") == "Hello there Bye")


def live_case(label, runner, expect):
    global skipped
    lab = cases.Lab()
    log = cases.Log()
    result = runner(lab, secrets.token_hex(2), log)
    expect(result)
    print("      " + "\n      ".join(log.lines))


def live_tests(only=None):
    global skipped
    if not moodle_client.moodle_up():
        skipped += 1
        print("SKIP  live cases: the lab Moodle is not running (bash moodle-lab/scripts/setup.sh)")
        return

    def a1(r):
        check("A1: before the fix the course is not on the student's My courses", r["course"] not in r["before"], r["before"])
        check("A1: diagnosed as NOT_ENROLLED", r["cause"] == "NOT_ENROLLED", r["cause"])
        check("A1: after the fix the student's My courses lists the course", r["course"] in (r["after"] or []), r["after"])

    def a2(r):
        check("A2: an enrolled student does not see a hidden course", r["course"] not in r["before"], r["before"])
        check("A2: diagnosed as COURSE_HIDDEN", r["cause"] == "COURSE_HIDDEN", r["cause"])
        check("A2: after the fix the student's My courses lists the course", r["course"] in (r["after"] or []), r["after"])

    def b(r):
        check("B: three wrong passwords were all refused", r["wrong_accepted"] == [False, False, False], r["wrong_accepted"])
        check("B: the CORRECT password is refused while the account is locked", r["correct_before"] is False, r["correct_before"])
        check("B: diagnosed as LOCKED_OUT from the lockout status", r["cause"] == "LOCKED_OUT", r["cause"])
        check("B: Moodle logged the failed attempts with the wrong password code", triage.AUTH_LOGIN_FAILED in r["reasons"], r["reasons"])
        check("B: after the unlock the correct password is accepted", r["correct_after"] is True, r["correct_after"])

    def c1(r):
        check("C1: before the fix the student does not get the submission page", r["seen_before"] is False)
        check("C1: diagnosed as DATE_NOT_REACHED", r["cause"] == "DATE_NOT_REACHED", r["cause"])
        check("C1: after the fix the student gets the submission page", r["seen_after"] is True)

    def c2(r):
        check("C2: before the fix the student does not get the submission page", r["seen_before"] is False)
        check("C2: diagnosed as HIDDEN", r["cause"] == "HIDDEN", r["cause"])
        check("C2: after the fix the student gets the submission page", r["seen_after"] is True)

    table = {"A1": (cases.run_not_enrolled, a1), "A2": (cases.run_hidden_course, a2), "B": (cases.run_lockout, b),
             "C1": (cases.run_restricted_assignment, c1), "C2": (cases.run_hidden_assignment, c2)}
    for label, (runner, expect) in table.items():
        if only and label != only:
            continue
        live_case(label, runner, expect)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "offline"):
        offline_tests()
    if mode in ("all", "live"):
        live_tests(sys.argv[2] if len(sys.argv) > 2 else None)
        if mode == "live" and skipped:
            return 1
    print("\n" + ("all passed" if failed == 0 else "%d failed" % failed) + ("" if not skipped else " (%d skipped)" % skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
