"""Turning raw exe paths and window titles into names a human recognises."""

import os
import re

from . import winapi

BROWSERS = {
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "opera_gx.exe",
    "vivaldi.exe",
    "arc.exe",
    "chromium.exe",
}

# Where the version resource is missing or unhelpful.
OVERRIDES = {
    "explorer.exe": "File Explorer",
    "windowsterminal.exe": "Terminal",
    "code.exe": "Visual Studio Code",
    "cursor.exe": "Cursor",
    "searchhost.exe": "Windows Search",
    "shellexperiencehost.exe": "Windows Shell",
    "startmenuexperiencehost.exe": "Start Menu",
    "lockapp.exe": "Lock Screen",
    "textinputhost.exe": "Windows Input",
    "opera_gx.exe": "Opera GX",
}

# Suffixes browsers bolt onto every window title.
_BROWSER_SUFFIX = re.compile(
    r"\s*[-–—|]\s*(Google Chrome|Chromium|Microsoft.? Edge|Mozilla Firefox|Firefox"
    r"|Brave|Opera GX|Opera|Vivaldi|Arc)(\s*\(InPrivate\)|\s*\(Private Browsing\))?\s*$",
    re.IGNORECASE,
)
_TAB_COUNT = re.compile(r"\s*(and|und|y)\s+\d+\s+more\s+(pages?|tabs?)", re.IGNORECASE)
# Edge and Chrome append the browser profile: "… - Personal - Microsoft Edge".
_PROFILE = re.compile(
    r"\s*[-–—]\s*(Personal|Work|School|Default|Guest|Profile\s*\d+)\s*$", re.IGNORECASE
)
_NOTIFICATION = re.compile(r"^\(\d+\+?\)\s*")

# Ordered: first keyword found in the title wins.
SITES = [
    ("youtube", "YouTube"),
    ("gmail", "Gmail"),
    ("google docs", "Google Docs"),
    ("google sheets", "Google Sheets"),
    ("google slides", "Google Slides"),
    ("google drive", "Google Drive"),
    ("google meet", "Google Meet"),
    ("google maps", "Google Maps"),
    ("google classroom", "Google Classroom"),
    ("google search", "Google Search"),
    ("whatsapp", "WhatsApp"),
    ("instagram", "Instagram"),
    ("facebook", "Facebook"),
    ("linkedin", "LinkedIn"),
    ("reddit", "Reddit"),
    ("telegram", "Telegram"),
    ("chatgpt", "ChatGPT"),
    ("claude", "Claude"),
    ("gemini", "Gemini"),
    ("perplexity", "Perplexity"),
    ("copilot", "Copilot"),
    ("github", "GitHub"),
    ("gitlab", "GitLab"),
    ("stack overflow", "Stack Overflow"),
    ("stackoverflow", "Stack Overflow"),
    ("leetcode", "LeetCode"),
    ("hackerrank", "HackerRank"),
    ("codeforces", "Codeforces"),
    ("w3schools", "W3Schools"),
    ("geeksforgeeks", "GeeksforGeeks"),
    ("wikipedia", "Wikipedia"),
    ("netflix", "Netflix"),
    ("hotstar", "JioHotstar"),
    ("prime video", "Prime Video"),
    ("spotify", "Spotify"),
    ("twitch", "Twitch"),
    ("amazon", "Amazon"),
    ("flipkart", "Flipkart"),
    ("myntra", "Myntra"),
    ("swiggy", "Swiggy"),
    ("zomato", "Zomato"),
    ("indiamart", "IndiaMART"),
    ("notion", "Notion"),
    ("figma", "Figma"),
    ("canva", "Canva"),
    ("trello", "Trello"),
    ("jira", "Jira"),
    ("slack", "Slack"),
    ("zoom", "Zoom"),
    ("teams", "Microsoft Teams"),
    ("outlook", "Outlook"),
    ("udemy", "Udemy"),
    ("coursera", "Coursera"),
    ("khan academy", "Khan Academy"),
    ("byju", "BYJU'S"),
    ("unacademy", "Unacademy"),
    ("quora", "Quora"),
    ("medium", "Medium"),
    ("substack", "Substack"),
    ("vercel", "Vercel"),
    ("netlify", "Netlify"),
    ("supabase", "Supabase"),
    ("firebase", "Firebase"),
    ("cloudflare", "Cloudflare"),
    ("aws", "AWS"),
    ("azure", "Azure"),
    ("hugging face", "Hugging Face"),
    ("kaggle", "Kaggle"),
    ("colab", "Google Colab"),
    ("upi", "UPI"),
    ("paytm", "Paytm"),
    ("phonepe", "PhonePe"),
    ("razorpay", "Razorpay"),
    ("irctc", "IRCTC"),
    ("weather", "Weather"),
    ("x.com", "X"),
    ("twitter", "X"),
]

# Internal window titles that mean nothing to a person.
NOISE_TITLES = {"program manager", "default ime", "msctfime ui", "windows input experience"}

_name_cache = {}


def exe_key(path):
    return os.path.basename(path).lower()


def app_name(path, title=""):
    """Display name for an exe. UWP apps borrow their window title."""
    key = exe_key(path)
    if key == "applicationframehost.exe":
        return title.strip() or "Windows App"
    if key in _name_cache:
        return _name_cache[key]
    name = OVERRIDES.get(key) or winapi.file_description(path)
    if not name or name.lower().endswith(".exe"):
        name = os.path.splitext(os.path.basename(path))[0].replace("_", " ").strip()
        name = name[:1].upper() + name[1:]
    _name_cache[key] = name
    return name


def is_browser(path):
    return exe_key(path) in BROWSERS


def clean_title(title):
    """Strip browser chrome and notification counters out of a window title."""
    text = _NOTIFICATION.sub("", title.strip())
    text = _BROWSER_SUFFIX.sub("", text)
    text = _PROFILE.sub("", text)
    text = _TAB_COUNT.sub("", text)
    text = _NOTIFICATION.sub("", text.strip())
    return text.strip(" -–—|") or title.strip()


def site_of(title):
    """Best guess at the website behind a browser window title.

    Window titles are all Windows exposes without a browser extension, so this
    is a keyword match, not a real URL. Anything unmatched is grouped as-is.
    """
    text = clean_title(title)
    low = text.lower()
    for needle, label in SITES:
        if needle in low:
            return label
    parts = [p.strip() for p in re.split(r"\s[-–—|]\s", text) if p.strip()]
    if len(parts) > 1:
        tail = parts[-1]
        if 2 <= len(tail) <= 28 and tail.lower() not in {"home", "new tab", "untitled"}:
            return tail
    return text[:40] or "Other pages"
