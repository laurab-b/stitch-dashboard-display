# Kindle stitch dashboard

Generates a landscape, Kindle-Paperwhite-sized PNG showing your running
monthly stitch total, today's count, a year-to-date total, and a
per-project breakdown — pulled from a Notion "Stitch Tracker" log (the
MostlyCrafty Stitching template).

## Try it with fake data first

```
pip install -r requirements.txt
python3 main.py --demo
```

This writes `dash.png` without touching Notion, so you can check the
layout before wiring up real data.

## Wire up Notion

This matches the real "Stitch Tracker" database's schema (confirmed
against the actual workspace): `Date` (date), `Stitches` (number),
`Project` (relation to a separate Projects database). If your columns
are named differently, override via `DATE_PROP` / `STITCH_PROP` /
`PROJECT_PROP` env vars instead of renaming your Notion columns.

1. Go to https://www.notion.so/my-integrations, create a new internal
   integration, and copy its secret.
2. Share it from the **top-level page** (e.g. "MostlyCrafty Stitching"),
   not just the Stitch Tracker database — `···` menu → **Connections**
   → add the integration. Sharing at the top also covers the Projects
   database underneath, which the script needs to resolve project
   names from the `Project` relation. (Skipping this step, or sharing
   only the log database, is the #1 cause of a 404/403.)
3. Copy the Stitch Tracker database's ID out of its URL — the
   32-character id right after your workspace name, before the `?v=`.
4. Run it for real:

```
NOTION_TOKEN=secret_xxx NOTION_DATABASE_ID=xxxxxxxx python3 main.py
```

This prints the monthly total, today's count, and the year-to-date
total, and resolves each log entry's related project to a name (cached
per run, so a project logged against many days only fetches its name
once).

## Get the image onto the Kindle

You need a URL the Kindle can reach that always serves the latest
`dash.png`. Two options, pick one:

- **No home server (recommended for a once-a-day refresh):** push this
  folder to a GitHub repo, add `NOTION_TOKEN`/`NOTION_DATABASE_ID` as
  repo secrets, and the included `.github/workflows/refresh.yml`
  regenerates and commits `dash.png` once a day. Point the Kindle at
  the raw file URL (`https://raw.githubusercontent.com/<you>/<repo>/main/dash.png`)
  and set its poll interval to once a day to match.
- **Something at home that's always on** (a Pi, an old laptop): run
  `python3 server.py`, which serves `http://<that-machine>:8080/dash.png`
  and regenerates it on a timer.

Either way, the Kindle side is the same: a jailbreak + a screensaver
extension that fetches a URL on a schedule and sets it as the sleep
screen. See the setup guide for the jailbreak-specific steps — those
depend on your Kindle's current firmware, so there's a wizard for it
rather than one fixed set of instructions.

## Files

- `render.py` — draws the PNG, landscape at 1448x1072 (the Paperwhite 3's panel rotated 90°). Centered serif ("mostlycrafty's stitches") header in Lora, a bold numeral for the monthly total, an optional "+N today" pill, a per-project breakdown on the right, and a footer line combining the year-to-date total with the "updated" timestamp — no pill around the annual total.
- `notion_source.py` — Notion API client (uses the 2025-09-03 data-source API); `fetch_stats()` returns month/today/year totals in one call
- `main.py` — glues them together, `--demo` flag for fake data
- `server.py` — optional always-on server variant
- `.github/workflows/refresh.yml` — optional serverless variant
