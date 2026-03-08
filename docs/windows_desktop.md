# Windows Desktop Packaging

## Overview

The Windows distribution uses a hybrid desktop shell:

- `pywebview` for the native window
- `uvicorn` + FastAPI on a random localhost port
- `Playwright` Chromium bundled inside the app
- `Inno Setup` for the installer

Writable runtime data is stored under `%LOCALAPPDATA%\BookCrawling`.

## Build Requirements

- Windows 10/11 build machine or VM
- Python with project dependencies installed
- Inno Setup compiler (`ISCC.exe`) on `PATH`, discoverable in a standard install path, or available via `ISCC_PATH`

## Build Command

```bash
pip install -e ".[dev,windows]"
python scripts/build_windows.py
```

If Inno Setup is not installed yet, you can still build the PyInstaller bundle only:

```bash
BOOKCRAWLER_SKIP_INSTALLER=1 python scripts/build_windows.py
```

## Output

- `dist/BookCrawling/`: PyInstaller onedir bundle
- `dist/installer/BookCrawlingSetup.exe`: installable Windows package

## Installer Behavior

- Installs the app under `%LOCALAPPDATA%\Programs\BookCrawling`
- Creates a Start Menu shortcut
- Optionally creates a desktop shortcut
- Installs WebView2 Runtime silently if missing
- Preserves `%LOCALAPPDATA%\BookCrawling` user data on uninstall
