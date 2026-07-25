# Screen Time

A screen-time tracker for Windows, like the screen timer on a phone. It records
which app has focus, for how long, and — for browsers — which website, then
shows it as a dashboard.

Everything stays on the machine it runs on: no account, no internet, nothing
sent anywhere, no third-party Python packages.

## Download (easiest)

Grab `ScreenTime.exe` from the
[Releases page](../../releases/latest) and double-click it. Python is bundled
inside, so there is nothing else to install.

Windows will warn "unknown publisher" the first time — *More info* then
*Run anyway*. That warning only disappears with a paid code-signing
certificate.

On first run it copies itself to `%LOCALAPPDATA%\ScreenTime\`, puts a
**Screen Time** icon on your Desktop, and starts tracking at every login. You
can delete the downloaded file afterwards.

## Install from source instead (needs Python 3.11+)

```powershell
git clone https://github.com/Shubhamvibecoder/screen-time-tracker.git
cd screen-time-tracker
.\install.ps1
```

That creates two things:

- **Screen Time** on your Desktop — double-click to open the dashboard.
- A login entry so tracking starts on its own every time you sign in.

Add `-ShowOnLogin` if you want the dashboard to pop open at every login too.
Remove both shortcuts with `.\install.ps1 -Uninstall` (your data is kept).

## Sharing it with other people

Build one self-contained file:

```powershell
.\build.ps1
```

That produces `dist\ScreenTime.exe` (about 10 MB) with Python bundled inside.
Send only that file — Google Drive, WhatsApp, or a GitHub Release.

What the person receiving it does:

1. Download `ScreenTime.exe`
2. Double-click it. Windows may say "unknown publisher" — *More info* then
   *Run anyway*. That warning only stops if you buy a code-signing certificate.
3. Their dashboard opens, a **Screen Time** icon appears on their Desktop, and
   tracking starts at every login from then on.

On first run the exe copies itself to `%LOCALAPPDATA%\ScreenTime\` and points
both shortcuts there, so they can delete the download afterwards. Running it a
second time just opens the dashboard instead of starting a second tracker.
`ScreenTime.exe --uninstall` removes the shortcuts and leaves the data.

## How it works

1. Every 2 seconds it asks Windows which window has focus, and looks up the
   process behind it.
2. If you have not touched the keyboard or mouse for 90 seconds, or the laptop
   is locked, nothing is counted — a tea break does not become screen time.
3. Time is added into buckets of *day / hour / app / window title* and written
   to SQLite every 30 seconds, so a crash costs you at most half a minute.
4. The dashboard reads the same database and refreshes every 20 seconds.

## The dashboard

- Total for the day, and how it compares with your 7-day average.
- The last 7 days as a bar strip — click any day to jump to it.
- A 24-hour strip showing when in the day you were active.
- Every app, ranked by time. Click a row to expand it: browsers break down by
  website, editors by project, File Explorer by folder.
- Arrow keys move between days.

## Websites: what it can and cannot see

Windows only exposes a window's **title**, not its URL. So the website is
inferred from the title — "YouTube - lofi beats - Google Chrome" becomes
YouTube. Around 70 common sites are recognised by name
(`screentime/naming.py`, the `SITES` list — add your own there). Anything
unrecognised is grouped under its own page title instead of a domain.

Getting true URLs would need a browser extension. Titles cover the everyday
question of "where did my afternoon go" without one.

## Privacy

- Data lives in one file: `%LOCALAPPDATA%\ScreenTime\screentime.db`.
- Window titles can be revealing (document names, chat names). Run with
  `--no-titles` to record apps only.
- Delete that file to erase all history. Nothing is sent anywhere; the web
  server binds to `127.0.0.1` and is unreachable from the network.

## Running by hand

```powershell
py app.py            # track + open the dashboard, with a console for errors
py app.py --silent   # track only
py app.py --open     # open the dashboard of an already-running instance
py app.py --port 8000
```

Launching it twice is safe: the second launch sees the port is taken and just
opens the dashboard.

## Layout

| File | Purpose |
| --- | --- |
| `screentime/winapi.py` | ctypes wrappers: focused window, idle time, lock state, app names |
| `screentime/naming.py` | exe → display name, browser titles → website |
| `screentime/storage.py` | SQLite schema, aggregation, queries |
| `screentime/tracker.py` | the 2-second sampling loop |
| `screentime/server.py` | localhost HTTP server + JSON API |
| `screentime/web/index.html` | the dashboard (single file, no dependencies) |
| `app.py` / `ScreenTime.pyw` | entry points (console / windowless) |
| `make_icon.py` | draws `icon.ico` with nothing but zlib |
| `install.ps1` | Desktop + login shortcuts |

Requires Python 3.11 or newer. Standard library only.
