# Builds dist\ScreenTime.exe - one self-contained file to share with other people.
# Keep this file ASCII-only: Windows PowerShell 5.1 reads .ps1 as ANSI.
# Needs PyInstaller once:  py -m pip install pyinstaller

# PyInstaller logs progress to stderr, which PowerShell 5.1 would turn into a
# fatal NativeCommandError. Exit codes are checked explicitly instead.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = $null
foreach ($c in @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)) { if (Test-Path $c) { $python = $c; break } }
if (-not $python) { $python = "py" }

& $python make_icon.py
if ($LASTEXITCODE -ne 0) { Write-Error "icon build failed"; exit 1 }

& $python -m PyInstaller `
    --noconfirm --clean --onefile --windowed `
    --name ScreenTime `
    --icon icon.ico `
    --add-data "screentime/web/index.html;screentime/web" `
    --exclude-module tkinter `
    --exclude-module unittest `
    --exclude-module pydoc_data `
    app.py
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed (exit $LASTEXITCODE)"; exit 1 }

$exe = Join-Path $root "dist\ScreenTime.exe"
if (-not (Test-Path $exe)) { Write-Error "build failed: $exe missing"; exit 1 }

$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
""
"Built dist\ScreenTime.exe ($mb MB)"
"Share that single file. Nothing else is needed, not even Python."
