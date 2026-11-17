"""Small Moodle clients for the support lab, standard library only.

WebService talks to Moodle's own REST web service API with a token. StudentSession logs in through the normal login page and asks for what
a student actually sees: the My courses list (the AJAX call the page itself makes) and any page by address. LabShell runs lab.php in the
container for the few things the web service API cannot do.
"""
import http.cookiejar
import json
import os
import re
import subprocess
from html.parser import HTMLParser
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("MOODLE_LAB_URL", "http://localhost:8093")
LAB_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def flatten(params, prefix=""):
    """Moodle's REST encoding for nested values: users[0][username]=x."""
    flat = {}
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten(value, name))
        elif isinstance(value, (list, tuple)):
            flat.update(flatten({str(i): v for i, v in enumerate(value)}, name))
        else:
            flat[name] = value
    return flat


def _post(url, fields, opener=None, timeout=60):
    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(url, data=data)
    open_fn = opener.open if opener else urllib.request.urlopen
    with open_fn(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


class WebServiceError(Exception):
    pass


class WebService:
    def __init__(self, token):
        self.token = token

    def call(self, function, **params):
        fields = {"wstoken": self.token, "wsfunction": function, "moodlewsrestformat": "json"}
        fields.update(flatten(params))
        body = json.loads(_post(f"{BASE}/webservice/rest/server.php", fields))
        if isinstance(body, dict) and "exception" in body:
            raise WebServiceError(f"{function}: {body.get('errorcode')}: {body.get('message')}")
        return body


class StudentSession:
    """A browser-like login. The cookie jar keeps the Moodle session; nothing is cached between calls."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def get(self, path):
        """Returns (final url, page text). An error status still returns its page, because a Moodle error page is the finding."""
        try:
            with self.opener.open(f"{BASE}{path}", timeout=60) as response:
                return response.geturl(), response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            return err.geturl(), err.read().decode("utf-8", "replace")

    def login(self, username, password):
        """Posts the login form like the browser does. Returns True when Moodle lets the session in."""
        _, page = self.get("/login/index.php")
        match = re.search(r'name="logintoken" value="([^"]+)"', page)
        fields = {"username": username, "password": password, "logintoken": match.group(1) if match else ""}
        try:
            with self.opener.open(urllib.request.Request(f"{BASE}/login/index.php", data=urllib.parse.urlencode(fields).encode()), timeout=60) as r:
                final, text = r.geturl(), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            final, text = err.geturl(), err.read().decode("utf-8", "replace")
        self.last_login_page = text
        return "/login/index.php" not in final and 'id="loginerrormessage"' not in text

    def login_error(self):
        """The red message Moodle printed on the login page after the last failed login, as plain text."""
        page = getattr(self, "last_login_page", "")
        start = page.find('id="loginerrormessage"')
        if start < 0:
            return ""
        end = page.find("</div>", start)
        start = max(page.rfind("<", 0, start), 0)
        text = page_text(page[start:end if end > 0 else start + 600])
        sentences = []
        for sentence in text.split(". "):   # Moodle prints the message twice, once for screen readers
            sentence = sentence.strip().rstrip(".")
            if sentence and sentence not in sentences:
                sentences.append(sentence)
        return ". ".join(sentences) + "."


    def my_courses(self):
        """Full names of the courses on the student's My courses page, from the same AJAX call the page makes."""
        _, page = self.get("/my/courses.php")
        key = re.search(r'"sesskey":"([^"]+)"', page)
        if not key:
            return None
        call = [{"index": 0, "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                 "args": {"classification": "all", "limit": 0, "offset": 0, "sort": "fullname"}}]
        request = urllib.request.Request(f"{BASE}/lib/ajax/service.php?sesskey={key.group(1)}&info=core_course_get_enrolled_courses_by_timeline_classification",
                                         data=json.dumps(call).encode(), headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=60) as response:
            body = json.loads(response.read().decode())
        if body[0].get("error"):
            return None
        return [c["fullname"] for c in body[0]["data"]["courses"]]


class _Words(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.words = []

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style") and self.skip > 0

    def handle_data(self, data):
        if not self.skip:
            self.words.append(data)


def page_text(html):
    """The visible words of a page, tags dropped, for a plain text check."""
    parser = _Words()
    parser.feed(html)
    parser.close()
    return " ".join(" ".join(parser.words).split())


class LabShell:
    """Runs lab.php inside the container and returns its one line of JSON."""

    def run(self, *args):
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        cmd = ["docker", "compose", "--env-file", os.path.join(LAB_DIR, "build", ".env"), "exec", "-T", "-u", "daemon", "moodle", "php", "/lab/lab.php", *map(str, args)]
        done = subprocess.run(cmd, cwd=LAB_DIR, capture_output=True, text=True, timeout=120, env=env)
        if done.returncode != 0:
            raise RuntimeError(f"lab.php {args[0]} failed: {done.stderr.strip()[:300]}")
        lines = [ln for ln in done.stdout.splitlines() if ln.startswith("{")]
        return json.loads(lines[-1])


def moodle_up():
    """True when the lab Moodle answers its login page. Tests that need the container skip when this is False."""
    try:
        with urllib.request.urlopen(f"{BASE}/login/index.php", timeout=5) as response:
            return response.status == 200
    except Exception:
        return False
