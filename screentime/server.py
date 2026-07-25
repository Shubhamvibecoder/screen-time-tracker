"""Local-only HTTP server: serves the dashboard and a small JSON API."""

import json
import os
import re
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import naming

HOST = "127.0.0.1"
PORT = 7842
# Under PyInstaller the bundle is unpacked to sys._MEIPASS, not next to the exe.
WEB_DIR = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "screentime",
    "web",
)
if not os.path.isdir(WEB_DIR):
    WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MIN_DETAIL_SECONDS = 20
MAX_DETAILS = 8


def build_summary(store, day):
    apps = store.apps_for_day(day)
    out = []
    for row in apps:
        details = []
        raw = store.details_for_day(day, row["exe"])
        if row["browser"]:
            grouped = {}
            for item in raw:
                label = naming.site_of(item["detail"])
                grouped[label] = grouped.get(label, 0.0) + item["seconds"]
            raw = [{"detail": k, "seconds": v} for k, v in grouped.items()]
            raw.sort(key=lambda d: -d["seconds"])
        for item in raw[:MAX_DETAILS]:
            if item["seconds"] >= MIN_DETAIL_SECONDS:
                details.append({"label": item["detail"], "seconds": round(item["seconds"])})
        out.append(
            {
                "exe": row["exe"],
                "name": row["name"],
                "browser": bool(row["browser"]),
                "seconds": round(row["seconds"]),
                "details": details,
            }
        )
    return {
        "day": day,
        "today": date.today().isoformat(),
        "total": round(store.day_total(day)),
        "apps": out,
        "hours": [round(s) for s in store.hours_for_day(day)],
        "span": store.span_for_day(day),
        "week": [
            {"day": d["day"], "seconds": round(d["seconds"])}
            for d in store.recent_days(7, end=date.fromisoformat(day))
        ],
        "tracked": store.tracked_days(),
    }


def make_handler(store, tracker):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ScreenTime"

        def log_message(self, *args):
            pass  # keep the console quiet

        def _send(self, code, body, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, code=200):
            self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

        def _file(self, name, content_type):
            path = os.path.join(WEB_DIR, name)
            if not os.path.isfile(path):
                self._send(404, b"not found", "text/plain")
                return
            with open(path, "rb") as handle:
                self._send(200, handle.read(), content_type)

        def do_GET(self):
            parsed = urlparse(self.path)
            route = parsed.path.rstrip("/") or "/"

            if route in ("/", "/index.html"):
                self._file("index.html", "text/html; charset=utf-8")
            elif route == "/api/summary":
                params = parse_qs(parsed.query)
                day = (params.get("day") or [date.today().isoformat()])[0]
                if not DATE_RE.match(day):
                    self._json({"error": "bad date"}, 400)
                    return
                tracker.flush()
                self._json(build_summary(store, day))
            elif route == "/api/status":
                self._json({"status": tracker.status, "db": store.path})
            else:
                self._send(404, b"not found", "text/plain")

    return Handler


class SingleInstanceServer(ThreadingHTTPServer):
    """Windows honours SO_REUSEADDR on listening sockets, so HTTPServer's default
    would let a second launch bind the same port — two trackers, doubled time.
    Refusing reuse turns the port into the single-instance lock."""

    allow_reuse_address = False
    daemon_threads = True


def serve(store, tracker, port=PORT):
    """Bind first so a second launch fails fast and just opens the browser."""
    return SingleInstanceServer((HOST, port), make_handler(store, tracker))
