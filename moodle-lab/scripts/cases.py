"""The three classic Tier 1 cases on the lab Moodle, each reproduced, diagnosed, fixed and checked as the student sees it.

    python scripts/cases.py            runs every case against the running lab and writes docs/moodle-cases-run.txt
    python scripts/cases.py --shots    also saves before and after screenshots (headless browser, logged in as the student) under docs/cases/

A: a student cannot see a course (A1 not enrolled, A2 the course is hidden)
B: a student is locked out after failed logins
C: an assignment shows as unavailable (C1 an access restriction date, C2 the activity is hidden)

Accounts, courses and enrolments are made through Moodle's own web service REST API. The few steps that API cannot do (create an assignment,
set an access restriction, clear a lockout) run lab.php, which calls Moodle's own PHP functions inside the container. Every name and person is invented.
"""
import json
import os
import secrets
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import triage  # noqa: E402
from moodle_client import BASE, LAB_DIR, LabShell, StudentSession, WebService, page_text  # noqa: E402

ROLE_STUDENT, ROLE_TEACHER = 5, 3   # Moodle's default role ids: student 5, editing teacher 3
DAY = 86400


class Lab:
    def __init__(self):
        self.shell = LabShell()
        # A site admin cannot get a token from the token endpoint (Moodle refuses it by design), so the admin's lab token is made the way
        # Site administration > Server > Manage tokens makes it.
        self.ws = WebService(self.shell.run("make-token", "admin")["token"])

    def provision(self, tag):
        """One course, one teacher and one student, all invented. The student is NOT enrolled yet; a case decides that."""
        password = "Aa1!" + secrets.token_urlsafe(10)
        names = {"student": f"student.{tag}", "teacher": f"teacher.{tag}"}
        created = self.ws.call("core_user_create_users", users=[
            {"username": names[role], "password": password, "firstname": role.title(), "lastname": tag.upper(),
             "email": f"{names[role]}@example.com", "auth": "manual"} for role in ("student", "teacher")])
        ids = {u["username"]: u["id"] for u in created}
        course = self.ws.call("core_course_create_courses", courses=[
            {"fullname": f"Harbour Skills {tag.upper()}", "shortname": f"HS-{tag.upper()}", "categoryid": 1, "visible": 1}])[0]
        self.enrol(ids[names["teacher"]], course["id"], ROLE_TEACHER)
        return {"tag": tag, "course_id": course["id"], "course_name": f"Harbour Skills {tag.upper()}", "password": password,
                "student": names["student"], "student_id": ids[names["student"]], "teacher_id": ids[names["teacher"]]}

    def enrol(self, user_id, course_id, role=ROLE_STUDENT):
        self.ws.call("enrol_manual_enrol_users", enrolments=[{"roleid": role, "userid": user_id, "courseid": course_id}])

    def student(self, p):
        session = StudentSession()
        if not session.login(p["student"], p["password"]):
            raise RuntimeError("the student could not log in")
        return session

    def enrolled_ids(self, course_id):
        return [u["id"] for u in self.ws.call("core_enrol_get_enrolled_users", courseid=course_id)]

    def course(self, course_id):
        return self.ws.call("core_course_get_courses", options={"ids": [course_id]})[0]

    def module(self, course_id, cmid):
        """The activity as the teacher side sees it, with its access restriction. None when it is not in the course."""
        for section in self.ws.call("core_course_get_contents", courseid=course_id):
            for module in section["modules"]:
                if module["id"] == cmid:
                    return module
        return None


# Fixes. Each one is its own function so a test can check it did something and a mutation can break it.

def fix_enrol(lab, p):
    lab.enrol(p["student_id"], p["course_id"])


def fix_unhide_course(lab, p):
    lab.ws.call("core_course_update_courses", courses=[{"id": p["course_id"], "visible": 1}])


def fix_unlock(lab, p):
    return lab.shell.run("unlock", p["student"])


def fix_restriction(lab, cmid, now):
    return lab.shell.run("set-availability-from", cmid, now - DAY)


def fix_show_activity(lab, cmid):
    lab.ws.call("core_course_edit_module", action="show", id=cmid)


def shot(p, path_on_site, name, out_dir, wrong_pw=False):
    """Saves one screenshot of what the student sees. The password goes through the environment, not the command line."""
    os.makedirs(out_dir, exist_ok=True)
    env = dict(os.environ, LAB_USER=p["student"], LAB_PW=p["password"])
    cmd = ["node", os.path.join(LAB_DIR, "scripts", "student_shot.cjs"), path_on_site, os.path.join(out_dir, name)]
    if wrong_pw:
        cmd.append("--wrong-pw")
    done = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    return (done.stdout.strip() or done.stderr.strip()).replace(LAB_DIR, "moodle-lab").replace("\\", "/")


class Log:
    def __init__(self):
        self.lines = []

    def __call__(self, case, step, text):
        line = f"[{case}] {step}: {text}"
        self.lines.append(line)
        print(line, flush=True)


def notice(words):
    """The message Moodle shows a student who is sent back to the course page from an unavailable activity."""
    end = words.find("Dismiss this notification")
    segment = words[:end] if end > 0 else words
    starts = [segment.rfind(marker) for marker in ("Sorry,", "Available from", "Available until", "Not available")]
    start = max(starts)
    return segment[start:] if start >= 0 else "(no notice found)"


def run_not_enrolled(lab, run, log, shots=None):
    p = lab.provision(f"a1{run}")
    s = lab.student(p)
    before = s.my_courses()
    log("A1", "reproduce", f"student logs in, My courses lists {len(before)} course(s); '{p['course_name']}' is not among them")
    if shots:
        log("A1", "screenshot", shot(p, "/my/courses.php", "a1_before.png", shots))
    cause = triage.diagnose_missing_course(p["student_id"], lab.course(p["course_id"]), lab.enrolled_ids(p["course_id"]))
    log("A1", "diagnose", f"course visible=1, enrolled users {len(lab.enrolled_ids(p['course_id']))} (the teacher only) -> {cause}")
    fix_enrol(lab, p)
    log("A1", "fix", "enrol_manual_enrol_users, role student")
    after = lab.student(p).my_courses()
    log("A1", "verify", f"student's My courses now lists {after}")
    if shots:
        log("A1", "screenshot", shot(p, "/my/courses.php", "a1_after.png", shots))
    return {"before": before, "cause": cause, "after": after, "course": p["course_name"]}


def run_hidden_course(lab, run, log, shots=None):
    p = lab.provision(f"a2{run}")
    lab.enrol(p["student_id"], p["course_id"])
    lab.ws.call("core_course_update_courses", courses=[{"id": p["course_id"], "visible": 0}])
    before = lab.student(p).my_courses()
    log("A2", "reproduce", f"student is enrolled but My courses lists {before}")
    if shots:
        log("A2", "screenshot", shot(p, "/my/courses.php", "a2_before.png", shots))
    cause = triage.diagnose_missing_course(p["student_id"], lab.course(p["course_id"]), lab.enrolled_ids(p["course_id"]))
    log("A2", "diagnose", f"student is in the enrolled users, course visible={lab.course(p['course_id'])['visible']} -> {cause}")
    fix_unhide_course(lab, p)
    log("A2", "fix", "core_course_update_courses visible=1")
    after = lab.student(p).my_courses()
    log("A2", "verify", f"student's My courses now lists {after}")
    if shots:
        log("A2", "screenshot", shot(p, "/my/courses.php", "a2_after.png", shots))
    return {"before": before, "cause": cause, "after": after, "course": p["course_name"]}


def run_lockout(lab, run, log, shots=None):
    p = lab.provision(f"b{run}")
    lab.enrol(p["student_id"], p["course_id"])
    wrong = []
    for _ in range(3):
        s = StudentSession()
        wrong.append(s.login(p["student"], "not-the-password"))
    blocked = StudentSession()
    ok = blocked.login(p["student"], p["password"])
    message = blocked.login_error()
    log("B", "reproduce", f"3 wrong passwords, then the CORRECT password: login accepted={ok}, the login page says: {message}")
    if shots:
        log("B", "screenshot", shot(p, "/login/index.php", "b_before.png", shots))
    status = lab.shell.run("lockout-status", p["student"])
    cause = triage.diagnose_lockout(status, int(time.time()))
    reasons = [e["reason"] for e in status["failed_login_events"]]
    log("B", "diagnose", f"login_lockout={status['locked']}, failed login log reasons (newest first) {reasons}, threshold {status['threshold']} -> {cause}")
    fix = fix_unlock(lab, p)
    log("B", "fix", f"unlock the account (login_unlock_account), locked now {fix['locked']}")
    session = StudentSession()
    ok_after = session.login(p["student"], p["password"])
    courses = session.my_courses() if ok_after else None
    log("B", "verify", f"correct password accepted={ok_after}, My courses {courses}")
    if shots:
        log("B", "screenshot", shot(p, "/my/courses.php", "b_after.png", shots))
    return {"wrong_accepted": wrong, "correct_before": ok, "message": message, "cause": cause, "reasons": reasons, "correct_after": ok_after}


def student_assignment_page(lab, p, cmid):
    """What the student gets at the activity's own address: the final address and the visible words."""
    url, html = lab.student(p).get(f"/mod/assign/view.php?id={cmid}")
    return url, page_text(html)


def run_restricted_assignment(lab, run, log, shots=None):
    p = lab.provision(f"c1{run}")
    lab.enrol(p["student_id"], p["course_id"])
    now = int(time.time())
    seeded = lab.shell.run("seed-assign", p["course_id"], "Harbour Report 1", now + 365 * DAY)
    cmid = seeded["cmid"]
    _, words = student_assignment_page(lab, p, cmid)
    seen_before = "Submission status" in words
    log("C1", "reproduce", f"student opens the assignment: submission page shown={seen_before}; Moodle sends the student to the course page with: {notice(words)}")
    if shots:
        log("C1", "screenshot", shot(p, f"/mod/assign/view.php?id={cmid}", "c1_before.png", shots))
    cause, detail = triage.diagnose_activity(lab.module(p["course_id"], cmid), now)
    log("C1", "diagnose", f"activity visible, Restrict access holds a date condition 'from' {time.strftime('%d %B %Y', time.gmtime(detail))} -> {cause}")
    fix_restriction(lab, cmid, now)
    log("C1", "fix", "the Restrict access date moved to yesterday")
    _, words_after = student_assignment_page(lab, p, cmid)
    seen_after = "Submission status" in words_after
    log("C1", "verify", f"student opens it again: submission page shown={seen_after}")
    if shots:
        log("C1", "screenshot", shot(p, f"/mod/assign/view.php?id={cmid}", "c1_after.png", shots))
    return {"seen_before": seen_before, "cause": cause, "seen_after": seen_after, "cmid": cmid}


def run_hidden_assignment(lab, run, log, shots=None):
    p = lab.provision(f"c2{run}")
    lab.enrol(p["student_id"], p["course_id"])
    now = int(time.time())
    seeded = lab.shell.run("seed-assign", p["course_id"], "Harbour Report 2", 0, 1)
    cmid = seeded["cmid"]
    _, words = student_assignment_page(lab, p, cmid)
    seen_before = "Submission status" in words
    log("C2", "reproduce", f"student opens the assignment: submission page shown={seen_before}; Moodle sends the student to the course page with: {notice(words)}")
    if shots:
        log("C2", "screenshot", shot(p, f"/mod/assign/view.php?id={cmid}", "c2_before.png", shots))
    cause, _ = triage.diagnose_activity(lab.module(p["course_id"], cmid), now)
    log("C2", "diagnose", f"teacher view of the course: activity visible=0 -> {cause}")
    fix_show_activity(lab, cmid)
    log("C2", "fix", "core_course_edit_module action=show")
    _, words_after = student_assignment_page(lab, p, cmid)
    seen_after = "Submission status" in words_after
    log("C2", "verify", f"student opens it again: submission page shown={seen_after}")
    if shots:
        log("C2", "screenshot", shot(p, f"/mod/assign/view.php?id={cmid}", "c2_after.png", shots))
    return {"seen_before": seen_before, "cause": cause, "seen_after": seen_after, "cmid": cmid}


CASES = [run_not_enrolled, run_hidden_course, run_lockout, run_restricted_assignment, run_hidden_assignment]


def main():
    shots = os.path.join(LAB_DIR, "docs", "cases") if "--shots" in sys.argv else None
    lab = Lab()
    run = secrets.token_hex(2)
    log = Log()
    log("lab", "start", f"{BASE}, run {run}")
    results = {}
    for case in CASES:
        results[case.__name__] = case(lab, run, log, shots)
    os.makedirs(os.path.join(LAB_DIR, "docs"), exist_ok=True)
    out = os.path.join(LAB_DIR, "docs", "moodle-cases-run.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n\n" + json.dumps(results, indent=1) + "\n")
    print("written", out)


if __name__ == "__main__":
    main()
