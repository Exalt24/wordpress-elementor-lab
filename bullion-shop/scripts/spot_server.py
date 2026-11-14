# LIFESPAN: permanent
"""A stand-in for a metals price feed. It serves invented gold and silver prices that drift with the clock, so the shop can be built and
measured without a vendor account or key. It is not a market price and says so in every reply.

    python scripts/spot_server.py [port]          (default 8090)

    GET /spot                  {"currency":"GBP","gold":..,"silver":..,"as_of":..,"stand_in":true}   after LATENCY_MS (default 150)
    GET /stats                 {"requests": n}  the number of /spot requests served, so a test can count what a page cost the feed
    GET /control?mode=ok|fail|jump|garbage|slow   changes what /spot does next (fail = 503, jump = gold x3, garbage = not JSON, slow = 5 s)
    GET /control?reset=1       mode ok and the counter back to 0
Standard library only.
"""
import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE = {"gold": 1650.0, "silver": 21.5}   # invented pounds per troy ounce
STATE = {"mode": "ok", "requests": 0}
LOCK = threading.Lock()


def prices(now):
    """Prices drift by up to about 1 percent over a few minutes, the same for every caller at the same second."""
    return {m: round(v * (1 + 0.01 * math.sin(now / 90.0 + (0 if m == "gold" else 2))), 2) for m, v in BASE.items()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path == "/control":
            with LOCK:
                if q.get("reset"):
                    STATE.update(mode="ok", requests=0)
                if q.get("mode"):
                    STATE["mode"] = q["mode"][0]
            return self.reply(200, json.dumps(STATE))
        if url.path == "/stats":
            return self.reply(200, json.dumps({"requests": STATE["requests"], "mode": STATE["mode"]}))
        if url.path != "/spot":
            return self.reply(404, '{"error":"not found"}')
        with LOCK:
            STATE["requests"] += 1
            mode = STATE["mode"]
        latency = 5.0 if mode == "slow" else float(os.environ.get("LATENCY_MS", "150")) / 1000.0
        time.sleep(latency)  # the feed's own response time, which is what the shop has to live with
        if mode == "fail":
            return self.reply(503, '{"error":"feed down"}')
        if mode == "garbage":
            return self.reply(200, "<html>maintenance</html>", "text/html")
        now = time.time()
        p = prices(now)
        if mode == "jump":
            p["gold"] = round(p["gold"] * 3, 2)
        return self.reply(200, json.dumps({"currency": "GBP", "gold": p["gold"], "silver": p["silver"], "as_of": int(now), "stand_in": True}))


def serve(port):
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print("stand-in price feed on port", port, flush=True)
    serve(port).serve_forever()
