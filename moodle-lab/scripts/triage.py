"""The diagnosis step of each Tier 1 case, as plain functions with no Moodle in them.

Each one takes facts read from Moodle (an admin view of the course, the lockout status, an activity as the teacher sees it) and names the
cause. The fix is a separate step in cases.py, so a wrong diagnosis and a fix that does nothing fail different tests.
"""
import json

# Moodle's login result codes (lib/moodlelib.php): AUTH_LOGIN_FAILED is a wrong password, AUTH_LOGIN_LOCKOUT is a refusal because of the lock.
AUTH_LOGIN_FAILED = 3
AUTH_LOGIN_LOCKOUT = 4


def diagnose_missing_course(user_id, course, enrolled_user_ids):
    """Why a student cannot see a course. The enrolment is checked first, because a hidden course the student is not even in is two faults."""
    if user_id not in enrolled_user_ids:
        return "NOT_ENROLLED"
    if not course["visible"]:
        return "COURSE_HIDDEN"
    return "NO_CAUSE_FOUND"


def diagnose_lockout(status, now):
    """Why a student with the right password is refused. status is the lockout-status document from lab.php."""
    if status["locked"]:
        return "LOCKED_OUT"
    recent = [e for e in status["failed_login_events"] if e["reason"] == AUTH_LOGIN_FAILED and now - e["time"] <= status["window"]]
    if recent:
        return "WRONG_PASSWORDS_BELOW_LIMIT"
    return "NO_FAILED_LOGINS_LOGGED"


def diagnose_activity(module, now):
    """Why an activity shows as unavailable. module is one entry of core_course_get_contents as the teacher sees it.

    Returns (cause, detail). A hidden activity is checked before the access restriction, because the restriction does not matter while it is hidden.
    """
    if not module.get("visible"):
        return "HIDDEN", None
    availability = json.loads(module.get("availability") or "null") or {}
    for condition in availability.get("c", []):
        if condition.get("type") != "date":
            continue
        if condition.get("d") == ">=" and condition["t"] > now:
            return "DATE_NOT_REACHED", condition["t"]
        if condition.get("d") == "<" and condition["t"] <= now:
            return "DATE_PASSED", condition["t"]
    return "NO_CAUSE_FOUND", None
