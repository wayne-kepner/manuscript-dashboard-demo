# Manuscript pipeline tracker

This repository contains the tracker interface, a Markdown parser, and a local server. It contains no manuscript records. The public GitHub Pages view shows the empty interface.

## Use it locally

1. Clone this repository.
2. Copy `pipeline.example.md` to `pipeline.local.md` and add your own rows.
3. On macOS, double-click `Open tracker.command`. On another system, run `python3 build_dashboard.py` and then `python3 tracker_server.py`.
4. Open `http://127.0.0.1:8770/dashboard.local.html`.

The builder reads `pipeline.local.md` and writes `dashboard.local.html`. Git ignores both files and the local deletion backups. The server binds to your computer only. The card menu can delete a row while saving a backup in `.tracker-backups`.

## Data format

The Markdown tables in `pipeline.example.md` define the input columns. Each manuscript needs a title, a status, and a `YYYY-MM-DD` status change date. You can leave other cells as `—`. The tracker recognizes `admin check`, `submitted`, `under review`, `revise and resubmit`, `revised submitted`, `accepted`, `published`, and `rejected`. Other status text appears under needs work.

The browser advances the displayed editorial stage as time passes. The Markdown row keeps the status you entered. Accepted manuscripts move into year review after 14 days, and published manuscripts appear there immediately.

Keep your records in `pipeline.local.md`. Never force-add that file or `dashboard.local.html` to Git.
