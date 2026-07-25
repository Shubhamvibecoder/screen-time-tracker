"""ScreenTime entry point.

    py app.py              start tracking and open the dashboard
    py app.py --silent     start tracking only (used at login)
    py app.py --open       just open the dashboard of a running instance
"""

import argparse
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screentime import install_self, server, storage  # noqa: E402
from screentime.tracker import Tracker  # noqa: E402


def dashboard_url(port):
    return "http://%s:%d/" % (server.HOST, port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="screentime", add_help=True)
    parser.add_argument("--silent", action="store_true", help="track without opening the dashboard")
    parser.add_argument("--open", action="store_true", help="only open the dashboard")
    parser.add_argument("--no-titles", action="store_true", help="record apps but not window titles")
    parser.add_argument("--no-install", action="store_true", help="skip first-run setup (.exe only)")
    parser.add_argument("--uninstall", action="store_true", help="remove the shortcuts, keep the data")
    parser.add_argument("--port", type=int, default=server.PORT)
    args = parser.parse_args(argv)

    url = dashboard_url(args.port)
    if args.open:
        webbrowser.open(url)
        return 0

    if args.uninstall:
        install_self.remove_shortcuts()
        return 0

    # Packaged build, first run: settle into a permanent home and restart there.
    if not args.no_install and install_self.needs_install():
        if install_self.install_and_handoff():
            return 0

    store = storage.Store()
    tracker = Tracker(store, store_titles=not args.no_titles)

    try:
        httpd = server.serve(store, tracker, args.port)
    except OSError:
        # Already running: hand the click over to the live instance.
        if not args.silent:
            webbrowser.open(url)
        return 0

    tracker.start()
    if not args.silent:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    print("ScreenTime running — %s\ndata: %s" % (url, store.path))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop()
        tracker.join(timeout=3)
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
