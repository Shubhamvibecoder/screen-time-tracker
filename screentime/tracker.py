"""The sampling loop: who has focus right now, and for how long."""

import threading
from collections import defaultdict
from datetime import datetime

from . import naming, winapi

SAMPLE_SECONDS = 2.0
FLUSH_SECONDS = 30.0
IDLE_LIMIT_SECONDS = 90.0
MAX_CREDIT = SAMPLE_SECONDS * 3  # guards against sleep / hibernate jumps
TITLE_LIMIT = 180


class Tracker(threading.Thread):
    daemon = True
    name = "screentime-tracker"

    def __init__(self, store, store_titles=True):
        super().__init__()
        self.store = store
        self.store_titles = store_titles
        self.stop_event = threading.Event()
        self._buckets = defaultdict(float)
        self._apps = {}
        self._spans = {}
        self._last_sample = None
        self.status = "starting"

    def stop(self):
        self.stop_event.set()

    def run(self):
        self._last_sample = datetime.now()
        while not self.stop_event.wait(SAMPLE_SECONDS):
            try:
                self._tick()
            except Exception as exc:  # a bad window must never kill tracking
                self.status = "error: %s" % exc
            if self._due_flush():
                self.flush()
        self.flush()

    # ---------------------------------------------------------------- internals

    def _due_flush(self):
        now = datetime.now()
        last = getattr(self, "_last_flush", None)
        if last is None:
            self._last_flush = now
            return False
        if (now - last).total_seconds() >= FLUSH_SECONDS:
            self._last_flush = now
            return True
        return False

    def _tick(self):
        now = datetime.now()
        previous, self._last_sample = self._last_sample, now
        elapsed = min((now - previous).total_seconds(), MAX_CREDIT)
        if elapsed <= 0:
            return

        if winapi.is_locked():
            self.status = "locked"
            return
        if winapi.idle_seconds() > IDLE_LIMIT_SECONDS:
            self.status = "idle"
            return

        active = winapi.active_window()
        if not active:
            self.status = "no window"
            return

        path, title = active
        exe = naming.exe_key(path)
        if exe in {"lockapp.exe", "logonui.exe"}:
            self.status = "locked"
            return

        name = naming.app_name(path, title)
        browser = naming.is_browser(path)
        detail = ""
        if self.store_titles and title and title.lower() not in naming.NOISE_TITLES:
            detail = (naming.clean_title(title) if browser else title)[:TITLE_LIMIT]

        self._apps[exe] = (name, browser)
        day = now.strftime("%Y-%m-%d")
        self._buckets[(day, now.hour, exe, detail)] += elapsed
        stamp = now.strftime("%H:%M")
        first, last = self._spans.get(day, (stamp, stamp))
        self._spans[day] = (min(first, stamp), max(last, stamp))
        self.status = "tracking %s" % name

    def flush(self):
        if not self._buckets:
            return
        buckets, apps, spans = self._buckets, self._apps, self._spans
        self._buckets, self._apps, self._spans = defaultdict(float), {}, {}
        self.store.flush(buckets, apps, spans)
