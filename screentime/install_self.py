"""First-run setup for the packaged .exe.

Someone double-clicks ScreenTime.exe in their Downloads folder. That copy must
not become the permanent install — they will delete it. So on first run the exe
copies itself to %LOCALAPPDATA%\\ScreenTime, points the shortcuts there, and
hands over to that copy.
"""

import ctypes
import os
import shutil
import subprocess
import sys
from ctypes import wintypes

CSIDL_DESKTOPDIRECTORY = 0x0010
CSIDL_STARTUP = 0x0007
CREATE_NO_WINDOW = 0x08000000
MAX_PATH = 260

APP_NAME = "ScreenTime"
DESKTOP_LINK = "Screen Time.lnk"
STARTUP_LINK = "ScreenTime.lnk"


def _known_folder(csidl):
    """Resolves via the shell, so a OneDrive-redirected Desktop is handled."""
    buf = ctypes.create_unicode_buffer(MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf)
    return buf.value


def desktop_dir():
    return _known_folder(CSIDL_DESKTOPDIRECTORY)


def startup_dir():
    return _known_folder(CSIDL_STARTUP) or os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )


def install_dir():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(root, APP_NAME)


def installed_exe():
    return os.path.join(install_dir(), "ScreenTime.exe")


def is_frozen():
    return getattr(sys, "frozen", False)


def _powershell(script):
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            creationflags=CREATE_NO_WINDOW,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def make_shortcut(path, target, arguments="", description=""):
    """WScript.Shell is the only dependency-free way to write a real .lnk."""
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    return _powershell(
        "$s = New-Object -ComObject WScript.Shell; "
        "$l = $s.CreateShortcut(%s); "
        "$l.TargetPath = %s; "
        "$l.Arguments = %s; "
        "$l.WorkingDirectory = %s; "
        "$l.IconLocation = %s; "
        "$l.Description = %s; "
        "$l.Save()"
        % (
            quote(path),
            quote(target),
            quote(arguments),
            quote(os.path.dirname(target)),
            quote(target + ",0"),
            quote(description),
        )
    )


def create_shortcuts(target, show_on_login=False):
    made = []
    desktop = os.path.join(desktop_dir(), DESKTOP_LINK)
    if make_shortcut(desktop, target, "", "Open your screen time dashboard"):
        made.append(desktop)
    startup = os.path.join(startup_dir(), STARTUP_LINK)
    args = "" if show_on_login else "--silent"
    if make_shortcut(startup, target, args, "Track screen time from login"):
        made.append(startup)
    return made


def remove_shortcuts():
    removed = []
    for folder, name in ((desktop_dir(), DESKTOP_LINK), (startup_dir(), STARTUP_LINK)):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            try:
                os.remove(path)
                removed.append(path)
            except OSError:
                pass
    return removed


def needs_install():
    """True when this exe is running from anywhere but its install location."""
    if not is_frozen():
        return False
    here = os.path.normcase(os.path.abspath(sys.executable))
    return here != os.path.normcase(os.path.abspath(installed_exe()))


def install_and_handoff():
    """Copy to the install folder, wire up shortcuts, start that copy, and stop."""
    target = installed_exe()
    os.makedirs(install_dir(), exist_ok=True)
    try:
        shutil.copy2(sys.executable, target)
    except (OSError, shutil.SameFileError):
        target = sys.executable  # running from a read-only spot: carry on in place
    create_shortcuts(target)
    try:
        subprocess.Popen([target], creationflags=CREATE_NO_WINDOW, close_fds=True)
    except OSError:
        return False
    return True
