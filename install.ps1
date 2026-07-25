# Installs ScreenTime: a Desktop icon + a silent tracker at login.
#   .\install.ps1                 desktop icon + track from login
#   .\install.ps1 -ShowOnLogin    also open the dashboard each login
#   .\install.ps1 -Uninstall      remove both shortcuts (data is kept)

param(
    [switch]$ShowOnLogin,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$startup = [Environment]::GetFolderPath("Startup")
$deskLnk = Join-Path $desktop "Screen Time.lnk"
$startLnk = Join-Path $startup "ScreenTime.lnk"

if ($Uninstall) {
    foreach ($lnk in @($deskLnk, $startLnk)) {
        if (Test-Path $lnk) { Remove-Item $lnk -Force; "removed $lnk" }
    }
    "Your data is untouched at $env:LOCALAPPDATA\ScreenTime\screentime.db"
    exit 0
}

# --- locate pythonw.exe (no console window) ---------------------------------
# A real installed Python, never a virtualenv: shortcuts must outlive any venv.
function Test-RealPython($path) {
    if (-not $path) { return $false }
    if (-not (Test-Path $path)) { return $false }
    if ($path -match "\\(venv|\.venv|env)\\") { return $false }
    return -not (Test-Path (Join-Path (Split-Path -Parent $path) "pyvenv.cfg"))
}

$candidates = New-Object System.Collections.Generic.List[string]
Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    ForEach-Object { $candidates.Add((Join-Path $_.FullName "pythonw.exe")) }
foreach ($dir in @("$env:ProgramFiles\Python313", "$env:ProgramFiles\Python312", "$env:ProgramFiles\Python311")) {
    $candidates.Add((Join-Path $dir "pythonw.exe"))
}
$viaLauncher = & py -c "import sys, os; print(os.path.join(sys.base_prefix, 'pythonw.exe'))" 2>$null
if ($viaLauncher) { $candidates.Add($viaLauncher.Trim()) }
$onPath = Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
if ($onPath) { $candidates.Add($onPath) }

$pythonw = $candidates | Where-Object { Test-RealPython $_ } | Select-Object -First 1
if (-not $pythonw) { throw "pythonw.exe not found. Install Python 3.11+ from python.org and re-run." }

$check = & ($pythonw -replace "pythonw\.exe$", "python.exe") -c "import sys; print('%d.%d' % sys.version_info[:2])"
"python: $pythonw ($check)"

# --- icon -------------------------------------------------------------------
$icon = Join-Path $root "icon.ico"
if (-not (Test-Path $icon)) {
    & ($pythonw -replace "pythonw\.exe$", "python.exe") (Join-Path $root "make_icon.py") | Out-Null
}

# --- shortcuts --------------------------------------------------------------
$shell = New-Object -ComObject WScript.Shell
$entry = Join-Path $root "ScreenTime.pyw"

function New-Lnk($path, $arguments, $description) {
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = $arguments
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation = "$icon,0"
    $lnk.Description = $description
    $lnk.Save()
}

New-Lnk $deskLnk "`"$entry`"" "Open your screen time dashboard"
"desktop icon: $deskLnk"

$loginArgs = if ($ShowOnLogin) { "`"$entry`"" } else { "`"$entry`" --silent" }
New-Lnk $startLnk $loginArgs "Track screen time from login"
if ($ShowOnLogin) { "login: tracks and opens the dashboard" } else { "login: tracks silently" }

""
"Done. Double-click 'Screen Time' on your Desktop to open the dashboard."
"Tracking starts automatically the next time you log in."
