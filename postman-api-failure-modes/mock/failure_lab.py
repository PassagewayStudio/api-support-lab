#!/usr/bin/env python3
"""Tiny local API that produces failures GitHub cannot produce on demand.

Endpoints (all JSON):
  POST /v1/subscriptions          -> 201 first time per Idempotency-Key-less "name",
                                     409 if the same name is created again
  GET  /v1/limited                -> 200 for the first 3 calls per window, then 429
                                     with Retry-After: 2
  GET  /v1/slow?delay=3           -> 200 after `delay` seconds (default 3)
  POST /v1/reset                  -> clears state (use before each run)

Standard library only. Run:  python3 failure_lab.py [port]
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"names": set(), "window_start": 0.0, "count": 0}
LIMIT = 3
WINDOW_SECONDS = 2


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, headers=None):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", f"req_{int(time.time() * 1000)}")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        return json.loads(raw) if raw else {}

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/v1/reset":
            STATE["names"].clear()
            STATE["window_start"], STATE["count"] = 0.0, 0
            return self._send(200, {"reset": True})
        if path == "/v1/subscriptions":
            try:
                body = self._json_body()
            except json.JSONDecodeError:
                return self._send(400, {"error": "malformed_json"})
            name = body.get("name")
            if not name:
                return self._send(400, {"error": "name_required"})
            if name in STATE["names"]:
                return self._send(409, {"error": "already_exists", "name": name})
            STATE["names"].add(name)
            return self._send(201, {"id": f"sub_{len(STATE['names'])}", "name": name})
        self._send(404, {"error": "not_found"})

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/v1/limited":
            now = time.time()
            if now - STATE["window_start"] > WINDOW_SECONDS:
                STATE["window_start"], STATE["count"] = now, 0
            STATE["count"] += 1
            if STATE["count"] > LIMIT:
                return self._send(
                    429, {"error": "rate_limited"}, {"Retry-After": str(WINDOW_SECONDS)}
                )
            return self._send(200, {"ok": True, "calls_in_window": STATE["count"]})
        if path == "/v1/slow":
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            time.sleep(float(params.get("delay", 3)))
            return self._send(200, {"ok": True, "slow": True})
        self._send(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[failure_lab] " + fmt % args + "\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    print(f"failure_lab listening on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
