"""SQLite storage. One local file, aggregated per day / hour / app / window title."""

import os
import sqlite3
import threading
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    day     TEXT NOT NULL,
    hour    INTEGER NOT NULL,
    exe     TEXT NOT NULL,
    detail  TEXT NOT NULL,
    seconds REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (day, hour, exe, detail)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS apps (
    exe     TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    browser INTEGER NOT NULL DEFAULT 0
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS spans (
    day   TEXT PRIMARY KEY,
    first TEXT NOT NULL,
    last  TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS usage_day ON usage(day);
"""


def default_path():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(root, "ScreenTime")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "screentime.db")


class Store:
    def __init__(self, path=None):
        self.path = path or default_path()
        self._lock = threading.Lock()
        self._local = threading.local()
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    # ------------------------------------------------------------------ writes

    def flush(self, buckets, apps, spans):
        """buckets: {(day, hour, exe, detail): seconds}, apps: {exe: (name, browser)}."""
        if not buckets:
            return
        with self._lock:
            conn = self._conn()
            with conn:
                conn.executemany(
                    "INSERT INTO apps(exe, name, browser) VALUES(?,?,?) "
                    "ON CONFLICT(exe) DO UPDATE SET name=excluded.name, browser=excluded.browser",
                    [(exe, name, int(browser)) for exe, (name, browser) in apps.items()],
                )
                conn.executemany(
                    "INSERT INTO usage(day, hour, exe, detail, seconds) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(day, hour, exe, detail) DO UPDATE SET "
                    "seconds = usage.seconds + excluded.seconds",
                    [(d, h, e, t, s) for (d, h, e, t), s in buckets.items()],
                )
                conn.executemany(
                    "INSERT INTO spans(day, first, last) VALUES(?,?,?) "
                    "ON CONFLICT(day) DO UPDATE SET "
                    "first = MIN(spans.first, excluded.first), "
                    "last  = MAX(spans.last,  excluded.last)",
                    [(day, first, last) for day, (first, last) in spans.items()],
                )

    # ------------------------------------------------------------------- reads

    def day_total(self, day):
        row = self._conn().execute(
            "SELECT COALESCE(SUM(seconds), 0) AS total FROM usage WHERE day = ?", (day,)
        ).fetchone()
        return row["total"]

    def apps_for_day(self, day):
        rows = self._conn().execute(
            "SELECT u.exe, COALESCE(a.name, u.exe) AS name, COALESCE(a.browser, 0) AS browser,"
            "       SUM(u.seconds) AS seconds "
            "FROM usage u LEFT JOIN apps a ON a.exe = u.exe "
            "WHERE u.day = ? GROUP BY u.exe ORDER BY seconds DESC",
            (day,),
        ).fetchall()
        return [dict(r) for r in rows]

    def details_for_day(self, day, exe):
        rows = self._conn().execute(
            "SELECT detail, SUM(seconds) AS seconds FROM usage "
            "WHERE day = ? AND exe = ? AND detail <> '' "
            "GROUP BY detail ORDER BY seconds DESC",
            (day, exe),
        ).fetchall()
        return [dict(r) for r in rows]

    def hours_for_day(self, day):
        buckets = [0.0] * 24
        for row in self._conn().execute(
            "SELECT hour, SUM(seconds) AS seconds FROM usage WHERE day = ? GROUP BY hour",
            (day,),
        ):
            if 0 <= row["hour"] < 24:
                buckets[row["hour"]] = row["seconds"]
        return buckets

    def span_for_day(self, day):
        row = self._conn().execute(
            "SELECT first, last FROM spans WHERE day = ?", (day,)
        ).fetchone()
        return dict(row) if row else None

    def recent_days(self, days=7, end=None):
        end = end or date.today()
        wanted = [(end - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
        marks = ",".join("?" * len(wanted))
        found = {
            r["day"]: r["seconds"]
            for r in self._conn().execute(
                f"SELECT day, SUM(seconds) AS seconds FROM usage WHERE day IN ({marks}) GROUP BY day",
                wanted,
            )
        }
        return [{"day": d, "seconds": found.get(d, 0.0)} for d in wanted]

    def tracked_days(self):
        row = self._conn().execute(
            "SELECT COUNT(DISTINCT day) AS n, MIN(day) AS since FROM usage"
        ).fetchone()
        return {"days": row["n"] or 0, "since": row["since"]}
