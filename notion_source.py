"""
Pulls stitch totals from a Notion "Stitch Tracker" log (the MostlyCrafty
Stitching template, and anything with the same shape) and hands them to
render.py.

Confirmed against the user's actual workspace on 2026-08-23. The log
database's real schema:
  - "Stitch log"   Title      (per-entry label, sometimes blank — not used)
  - "Date"         Date       (which day the entry counts toward)
  - "Stitches"     Number     (stitches worked that entry; summed here)
  - "Project"      Relation   (-> a separate Projects database; the log
                                row only stores related page IDs, so
                                project *names* are resolved with a
                                separate page fetch per project, cached)
  - "Time (HH:MM:SS)", "progress photo" — not used by this script

Notion split "databases" from "data sources" in the 2025-09-03 API
version — a database can hold multiple data sources, and querying rows
happens against a data_source_id, not the database_id directly.
resolve_data_source_id() does that lookup so you only need to hand this
script the database ID, which is what you copy out of Notion normally.

Setup:
  1. https://www.notion.so/my-integrations -> New integration -> copy
     the "Internal Integration Secret" -> set as NOTION_TOKEN.
  2. Share access with that integration from the TOP-level page (e.g.
     "MostlyCrafty Stitching") rather than just the Stitch Tracker
     database -> "..." menu -> Connections -> add your integration.
     Sharing at the top covers the Stitch Tracker log AND the Projects
     database beneath it (needed to look up project names), so you only
     have to do this once.
  3. Copy the Stitch Tracker database's ID out of its URL:
     notion.so/myworkspace/<DATABASE_ID>?v=...  (32 hex chars, dashes optional)
     Set as NOTION_DATABASE_ID.
"""

import os
import calendar
from datetime import date, datetime
import requests

NOTION_VERSION = "2025-09-03"
API_BASE = "https://api.notion.com/v1"

DATE_PROP = os.environ.get("DATE_PROP", "Date")
STITCH_PROP = os.environ.get("STITCH_PROP", "Stitches")
PROJECT_PROP = os.environ.get("PROJECT_PROP", "Project")


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def resolve_data_source_id(token: str, database_id: str) -> str:
    """A database can contain multiple data sources; for a normal
    single-table database (the vast majority, including this template)
    there's exactly one, so we just take the first."""
    resp = requests.get(f"{API_BASE}/databases/{database_id}", headers=_headers(token))
    resp.raise_for_status()
    data = resp.json()
    sources = data.get("data_sources", [])
    if not sources:
        raise RuntimeError(
            "No data sources found on that database. Double-check the "
            "database ID and that you shared it (or its parent page) "
            "with your integration."
        )
    return sources[0]["id"]


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1).isoformat(), date(year, month, last_day).isoformat()


def _day_bounds(d: date) -> tuple[str, str]:
    iso = d.isoformat()
    return iso, iso


def _year_bounds(year: int) -> tuple[str, str]:
    return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()


class ProjectNameCache:
    """Resolves a Project relation's page ID to its title, once per ID."""

    def __init__(self, token: str):
        self.token = token
        self._cache: dict[str, str] = {}

    def resolve(self, page_id: str) -> str:
        if page_id in self._cache:
            return self._cache[page_id]
        resp = requests.get(f"{API_BASE}/pages/{page_id}", headers=_headers(self.token))
        resp.raise_for_status()
        props = resp.json().get("properties", {})
        name = page_id  # fallback if something is unshared/unexpected
        for prop in props.values():
            if prop.get("type") == "title":
                name = "".join(t.get("plain_text", "") for t in prop.get("title", [])) or name
                break
        self._cache[page_id] = name
        return name


def _query_range(token: str, data_source_id: str, start: str, end: str) -> list[dict]:
    body = {
        "filter": {
            "and": [
                {"property": DATE_PROP, "date": {"on_or_after": start}},
                {"property": DATE_PROP, "date": {"on_or_before": end}},
            ]
        },
        "page_size": 100,
    }
    results = []
    url = f"{API_BASE}/data_sources/{data_source_id}/query"
    while True:
        resp = requests.post(url, headers=_headers(token), json=body)
        resp.raise_for_status()
        payload = resp.json()
        results.extend(payload["results"])
        if not payload.get("has_more"):
            break
        body["start_cursor"] = payload["next_cursor"]
    return results


def summarize(
    token: str,
    data_source_id: str,
    start: str,
    end: str,
    name_cache: "ProjectNameCache",
) -> tuple[int, list[tuple[str, int]]]:
    """Returns (total_stitches, [(project_name, stitches), ...]) for
    every log entry with Date between start and end (inclusive, ISO)."""
    pages = _query_range(token, data_source_id, start, end)

    total = 0
    by_project: dict[str, int] = {}
    for page in pages:
        props = page["properties"]
        count = props.get(STITCH_PROP, {}).get("number") or 0
        total += count

        relation = props.get(PROJECT_PROP, {}).get("relation") or []
        if relation:
            # A log entry is normally tied to one project; if someone
            # relates it to several, split credit isn't worth the
            # complexity here, so just credit each named project fully.
            for rel in relation:
                name = name_cache.resolve(rel["id"])
                by_project[name] = by_project.get(name, 0) + count
        elif count:
            by_project["(no project set)"] = by_project.get("(no project set)", 0) + count

    breakdown = sorted(by_project.items(), key=lambda pair: pair[1], reverse=True)
    return total, breakdown


def fetch_stats(
    token: str, data_source_id: str, today: date
) -> tuple[int, list[tuple[str, int]], int, int]:
    """Convenience wrapper: (month_total, month_breakdown, today_total, year_total).

    Note this makes three separate range queries (month/day/year) rather
    than one and slicing in Python — simpler to reason about, and still
    cheap since a daily cron isn't near Notion's rate limits. The project
    name cache is shared across all three so a project logged against
    every day of the year still only gets fetched once.
    """
    cache = ProjectNameCache(token)
    m_start, m_end = _month_bounds(today.year, today.month)
    month_total, month_breakdown = summarize(token, data_source_id, m_start, m_end, cache)

    d_start, d_end = _day_bounds(today)
    today_total, _ = summarize(token, data_source_id, d_start, d_end, cache)

    y_start, y_end = _year_bounds(today.year)
    year_total, _ = summarize(token, data_source_id, y_start, y_end, cache)

    return month_total, month_breakdown, today_total, year_total


if __name__ == "__main__":
    token = os.environ["NOTION_TOKEN"]
    database_id = os.environ["NOTION_DATABASE_ID"]
    today = datetime.now().date()

    ds_id = resolve_data_source_id(token, database_id)
    month_total, breakdown, today_total, year_total = fetch_stats(token, ds_id, today)

    print(f"{today.strftime('%B %Y')}: {month_total} stitches ({today_total} today, {year_total} this year)")
    for name, count in breakdown:
        print(f"  {name}: {count}")
