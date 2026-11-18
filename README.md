# FAANGrind local mirror

An offline copy of faangrind.vercel.app. Its pages and static files live in `mirror/`, and `serve.py` serves them locally, standing in for the site's `/api` endpoints using the JSON snapshots in `mirror/_data/`.

## Quick start

Linux / macOS / WSL:

```bash
cd faanggrind                        # the project folder
python3 -m venv .venv                # create the environment (one time)
source .venv/bin/activate            # activate it
pip install -r requirements.txt      # install pinned packages (one time)
python serve.py                      # start the server
```

Windows (PowerShell):

```powershell
cd faanggrind
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python serve.py
```

Then open **http://localhost:3000**. Press `Ctrl+C` to stop the server.

Next time, you only need to start it again:

```bash
cd faanggrind
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python serve.py
```

The server itself needs no packages, so `python3 serve.py` also works without the environment.

## Requirements

- Python 3.7 or newer. Nothing else is needed to run the server, since `serve.py` uses only the standard library.
- The `mirror/` folder (about 330 MB). Copy the whole project folder to the new machine.

Check your Python version:

```bash
python3 --version        # Windows: python --version  (or py --version)
```

If Python is missing, install it:

| OS | Command |
|---|---|
| Ubuntu / Debian / WSL | `sudo apt update && sudo apt install -y python3` |
| Fedora | `sudo dnf install -y python3` |
| macOS (Homebrew) | `brew install python` |
| Windows | `winget install Python.Python.3.12`, or download it from python.org (tick "Add Python to PATH") |

## Run the server

From the project folder:

```bash
python3 serve.py                 # http://localhost:3000
python3 serve.py 8080            # use a different port
python3 serve.py --quiet         # turn off per-request logging
```

On Windows, use `python` (or `py`) instead of `python3`.

Then open http://localhost:3000 in a browser. Stop the server with `Ctrl+C`.

To keep it running in the background on Linux/macOS:

```bash
nohup python3 serve.py --quiet > serve.log 2>&1 &
kill %1                          # or: pkill -f serve.py
```

### Notes

- The server listens on `127.0.0.1` only, so other devices on your network can't reach it. To allow that, change `"127.0.0.1"` to `"0.0.0.0"` at the bottom of `serve.py`.
- **Your progress is saved in the browser, not on the server.** Solved/attempted statuses, notes, bookmarks, the revision list and your streak are kept in the browser's localStorage, which is tied to the exact address (for example `localhost:3000`). Changing the port, host or browser starts you with empty progress. To move progress, go to **Settings → Export JSON** on the old setup, then **Settings → Import JSON** on the new one. Import *replaces* the current progress; it doesn't merge with it.

## Rebuild the mirror (optional)

Only do this to refresh the content from the live site. It needs internet access and a few packages, pinned to exact versions in `requirements.txt`. They were tested with Python 3.8.10.

### Create the environment

Linux / macOS / WSL:

```bash
sudo apt install -y python3-venv     # Ubuntu/Debian only, if "venv" is missing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1           # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check that it worked:

```bash
python -c "import requests, bs4, markdownify; print('ok')"
```

Leave the environment with `deactivate`.

To re-pin after upgrading packages, run the line below. It drops `pkg_resources==0.0.0`, which Ubuntu's venv adds and which can't be installed from PyPI.

```bash
pip freeze | grep -v '^pkg_resources==' > requirements.txt
```

### Rebuild

With the environment active:

```bash
python3 crawl.py                 # 1. crawl the sitemap into scrape/ (raw HTML + Markdown)
python3 mirror.py                # 2. build mirror/ from scrape/raw plus static assets
python3 fetch_data.py            # 3. snapshot the /api data into mirror/_data/
```

## Files

| Path | Purpose |
|---|---|
| `serve.py` | Local server for `mirror/`, with offline `/api` replacements |
| `mirror/` | Site pages (`<path>.html`), `_next/` static assets, `_data/` API snapshots |
| `crawl.py` | Crawls the live site into `scrape/` |
| `mirror.py` | Builds `mirror/` from the crawl |
| `fetch_data.py` | Downloads the API data into `mirror/_data/` |
| `scrape/` | Crawl output (raw HTML, Markdown, `pages.jsonl`) |
