# LIFESPAN: permanent
"""Offline tests for the AI answer visibility script. Both engines are tested against a local stand-in server.

    python tests/test_ai_visibility.py
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import ai_visibility as av  # noqa: E402

results = []


def check(name, cond):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name)


class StandIn(BaseHTTPRequestHandler):
    answers = []   # a list consumed in order; "ERR" makes the server answer 500
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        StandIn.seen.append((self.path, self.headers.get("Authorization"), body))
        text = StandIn.answers.pop(0) if StandIn.answers else ""
        if text == "ERR":
            self.send_response(500)
            self.end_headers()
            return
        payload = {"message": {"content": text}} if self.path == "/api/chat" else {"choices": [{"message": {"content": text}}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve():
    srv = HTTPServer(("127.0.0.1", 0), StandIn)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_port


def test_wilson():
    lo, hi = av.wilson(0, 10)
    check("0 of 10 starts at 0 and stays under 0.31", lo == 0.0 and 0.2 < hi < 0.31)
    lo, hi = av.wilson(5, 10)
    check("5 of 10 is centred on 0.5 with the textbook bounds", abs(lo - 0.2366) < 0.001 and abs(hi - 0.7634) < 0.001)
    lo, hi = av.wilson(10, 10)
    check("10 of 10 ends at 1", hi > 0.9999 and 0.72 < lo < 0.73)
    check("no trials is the whole range", av.wilson(0, 0) == (0.0, 1.0))
    check("more trials narrow the interval", (av.wilson(50, 100)[1] - av.wilson(50, 100)[0]) < (av.wilson(5, 10)[1] - av.wilson(5, 10)[0]))


def test_mentioned():
    check("a name is found ignoring case", av.mentioned("Try the ACEP site", "acep"))
    check("a name inside another word is not found", not av.mentioned("the pacepoint", "ACEP") and not av.mentioned("the PACEP site", "ACEP") and not av.mentioned("ACEPS", "ACEP"))
    check("a name with punctuation is found", av.mentioned("Listen to EM:RAP weekly.", "EM:RAP"))
    check("a name at the start and end of the text is found", av.mentioned("ACEP", "acep") and av.mentioned("see acep", "ACEP"))
    check("a regex character in a name is taken literally", av.mentioned("the C++ course", "c++") and not av.mentioned("the cc course", "c+"))
    check("no mention is no mention", not av.mentioned("nothing here", "ACEP"))


def test_engines():
    srv, base = serve()
    StandIn.seen.clear()
    StandIn.answers = ["ACEP and Medscape offer it.", "Try medscape.", "No names at all.", "ERR", "ACEP again"]
    engine = av.OllamaEngine("m1", base)
    res = av.run(["q1", "q2"], engine, ["ACEP", "Medscape", "Other"], repeats=3)
    q1, q2 = res["q1"], res["q2"]
    check("answers are counted per question", q1["answers"] == 3 and q1["counts"] == {"ACEP": 1, "Medscape": 2, "Other": 0})
    check("an engine error is an error and never a miss", q2["answers"] == 2 and q2["errors"] == 1 and q2["counts"]["ACEP"] == 1)
    check("the ollama request names the model, turns streaming off and sends the system prompt", StandIn.seen[0][0] == "/api/chat" and StandIn.seen[0][2]["model"] == "m1" and StandIn.seen[0][2]["stream"] is False and StandIn.seen[0][2]["messages"][0]["content"] == av.SYSTEM)

    StandIn.seen.clear()
    StandIn.answers = ["Use ACEP."]
    out = av.OpenAIEngine("m2", base + "/v1", "sekret").ask("q")
    check("the OpenAI compatible engine sends the key and reads the choice", out == "Use ACEP." and StandIn.seen[0][1] == "Bearer sekret" and StandIn.seen[0][0] == "/v1/chat/completions")
    srv.shutdown()


def test_report():
    results_ = {"q1": {"answers": 3, "errors": 0, "counts": {"A": 3, "B": 0}}, "q2": {"answers": 2, "errors": 1, "counts": {"A": 1, "B": 0}}}
    text = av.report(results_, ["A", "B"], "a test engine", "2000-01-01", 3)
    check("the report totals answers and errors", "5 answers, 1 errors" in text)
    check("the report gives the rate and the interval", "| A | 4 of 5 | 80% |" in text and "| B | 0 of 5 | 0% | 0% to 43% |" in text)
    check("the report names the engine honestly and the per question counts", "a test engine" in text and "| q2 | 2 | 1 | 0 |" in text)
    empty = av.report({"q": {"answers": 0, "errors": 3, "counts": {"A": 0}}}, ["A"], "e", "2000-01-01", 3)
    check("no answers gives n/a and not a rate of zero", "n/a" in empty)


def main():
    test_wilson()
    test_mentioned()
    test_engines()
    test_report()
    ok = all(results)
    print("\n%d checks, %s" % (len(results), "all passed" if ok else "SOME FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
