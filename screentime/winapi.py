"""Thin ctypes wrappers over the Win32 calls the tracker needs.

No third-party dependencies on purpose: everything here ships with Windows.
"""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
version = ctypes.WinDLL("version", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DESKTOP_READOBJECTS = 0x0001

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.CloseDesktop.argtypes = [wintypes.HANDLE]

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.GetTickCount.restype = wintypes.DWORD


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_seconds():
    """Seconds since the last keyboard or mouse input, system-wide."""
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    delta = (kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return delta / 1000.0


def is_locked():
    """True when the lock screen / another desktop owns input."""
    handle = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    if not handle:
        return True
    user32.CloseDesktop(handle)
    return False


def _window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def _process_path(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def active_window():
    """(exe_path, window_title) of the focused window, or None."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    path = _process_path(pid.value)
    if not path:
        return None
    return path, _window_title(hwnd)


def file_description(path):
    """The app's own display name from its version resource, e.g. 'Google Chrome'."""
    try:
        size = version.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        block = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(path, 0, size, block):
            return None
        ptr = ctypes.c_void_p()
        length = wintypes.UINT()
        if not version.VerQueryValueW(
            block, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(length)
        ):
            return None
        codes = ctypes.cast(ptr, ctypes.POINTER(wintypes.WORD))
        key = "\\StringFileInfo\\%04x%04x\\FileDescription" % (codes[0], codes[1])
        if not version.VerQueryValueW(block, key, ctypes.byref(ptr), ctypes.byref(length)):
            return None
        if not length.value:
            return None
        return ctypes.wstring_at(ptr, length.value).strip("\x00").strip() or None
    except OSError:
        return None
