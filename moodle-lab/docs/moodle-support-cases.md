# Moodle support cases

Three problems a Tier 1 support rep gets on a learning management system every week, reproduced on a real Moodle 5.0 in Docker, diagnosed from what Moodle shows an admin, fixed, and checked by logging in as the student. Every course, teacher, student and assignment is invented and the data lives only in the container.

The run log is [moodle-cases-run.txt](moodle-cases-run.txt). The screenshots are in [cases/](cases/).

## How it is set up

| Part | What it does |
|---|---|
| `docker-compose.yml` | Moodle 5.0.2 and MariaDB 11.8.3 (both pinned), Moodle on `http://localhost:8093` |
| `scripts/setup.sh` | Makes fresh passwords into `build/` (ignored by git), starts the stack, waits for Moodle to install itself, turns the web services on and sets the lockout rule |
| `scripts/cases.py` | Creates the course, the teacher and the student through Moodle's own web service REST API, then runs each case: reproduce, diagnose, fix, verify |
| `scripts/triage.py` | The diagnosis step as plain functions, so a wrong diagnosis is its own test failure |
| `scripts/lab.php` | The few things the web service API cannot do (create an assignment, set an access restriction, clear a lockout, make the admin's token). It calls Moodle's own PHP functions inside the container, the same ones the admin pages call |
| `scripts/student_shot.cjs` | Logs in as the student in a headless browser and saves what the student sees |

The student is checked in two ways: a login and the My courses list through plain HTTP (the same AJAX call the My courses page makes), and a real browser for the screenshots.

## Ticket A1: "I cannot see my course"

**Reported:** a student says the course is not on their dashboard.

**Reproduce:** log in as the student. My courses lists nothing.

**Diagnose:** open the course as an admin. The course is visible, and the enrolled users list holds one person, the teacher. The student was never enrolled.

**Fix:** enrol the student with the manual enrolment method, role Student.

**Verify:** log in as the student again. My courses now lists the course.

## Ticket A2: "I am enrolled but the course is gone"

**Reported:** a student who was in the course last week sees nothing.

**Reproduce:** log in as the student. My courses is empty.

**Diagnose:** the student is in the enrolled users list, so enrolment is fine. The course visibility is Hide. A hidden course is invisible to students even when they are enrolled, and the teacher still sees it.

**Fix:** set the course visibility to Show.

**Verify:** the student's My courses lists the course.

## Ticket B: "I typed the right password and it still says locked"

**Reported:** a student cannot log in and says the password is correct.

**Reproduce:** three wrong passwords, then the correct one. The login page says the account is locked. The lockout rule on this site is three failed logins.

**Diagnose:** the account has the lockout flag set. The log shows three failed logins with the wrong password code, then refusals with a different code, the lockout code. Counting failed logins alone would say the password is simply wrong; the flag is what to read.

**Fix:** unlock the account (the Unlock action on the user list in Site administration). If the student also forgot the password, set a new one at the same time.

**Verify:** the student logs in with the correct password and My courses loads.

## Ticket C1: "My assignment says it is not available"

**Reported:** a student clicks an assignment and lands back on the course page.

**Reproduce:** the student opens the assignment's own address and is sent to the course page with a notice, "Available from" a date a year away.

**Diagnose:** the activity is visible, but Restrict access holds a date condition. Someone typed the wrong year.

**Fix:** move the date to yesterday.

**Verify:** the student opens the assignment and gets its submission page.

## Ticket C2: "The assignment my teacher mentioned is not there"

**Reported:** a student cannot find an assignment the teacher talked about, or gets a notice that it is hidden.

**Reproduce:** the student opens the assignment and is sent to the course page with "Sorry, this activity is currently hidden".

**Diagnose:** the teacher's view of the course shows the activity with visibility Hide. A hidden activity ignores its access restrictions, so it is checked first.

**Fix:** set the activity to Show.

**Verify:** the student opens the assignment and gets its submission page.

## What was hard

- The token endpoint refuses site admins by design, so the admin's token for the lab is made the way Site administration, Server, Manage tokens makes it (`make-token` in `lab.php`).
- With no mail server in the lab, enrolling a student failed with "Message was not sent", because Moodle tries to email the welcome message. Switching the email output off for the lab fixed it.
- The failed login log keeps the user in the event's own user field and the reason in a JSON blob. A refusal because the account is locked has its own reason code, so a diagnosis that counts every failed login in the window gets this ticket wrong, and one test covers it.
- Moodle prints the login error twice, once for screen readers, so the lab de-duplicates the sentence before it reports it.
- The Bitnami Moodle and MariaDB images moved to a frozen legacy repository (`bitnamilegacy`) in 2025. They are pinned and still work, but they will never get a security update, which is fine for a throwaway lab and not for anything real.

## Limits

- A local Moodle 5.0 on invented data. It is a lab, not a client's site.
- No Blackboard, Canvas or D2L, and no single sign-on, LTI tool or grade passback.
- The lab sets its own lockout rule (three failures) and has no mail server, so the unlock link and the welcome messages are never sent.
- Creating the assignments, the access restriction, the unlock and the admin token go through Moodle's PHP functions in a command line helper, because the web service API has no call for them.

## What the runs printed

One machine, 2026-11-18, Moodle 5.0.2 on MariaDB 11.8.3 in Docker.

- `python scripts/cases.py --shots`: 5 cases, 5 diagnoses, 5 fixes, 5 student checks that passed, 10 screenshots read ([moodle-cases-run.txt](moodle-cases-run.txt)).
- `python tests/test_moodle_cases.py`: 17 offline checks and 17 live checks, 34 of 34 passed ([test-run-captured.txt](test-run-captured.txt)).
- `python tests/mutation_check.py --live`: 16 of 16 deliberate breaks caught, 11 in the diagnosis and client code and 5 that break a fix, each failing its live case ([mutation-run-captured.txt](mutation-run-captured.txt)). CI runs the 17 offline checks and the 11 offline breaks; the live part needs the container.
