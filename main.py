"""
Regenerates dash.png from Notion. Meant to be run on a schedule (cron,
a GitHub Action, a Raspberry Pi's crontab — see the setup guide) since
the Kindle just polls a static image URL; nothing here needs to be
"always on" by itself.

Usage:
    NOTION_TOKEN=secret_xxx NOTION_DATABASE_ID=xxxx python3 main.py
    python3 main.py --demo     # no Notion credentials needed, uses fake data
"""

import os
import sys
from datetime import datetime

from render import render_dashboard
from notion_source import resolve_data_source_id, fetch_stats

OUT_PATH = os.environ.get("DASH_OUT_PATH", "dash.png")


def main():
    now = datetime.now()
    month_label = now.strftime("%B %Y")

    if "--demo" in sys.argv:
        month_total = 4218
        breakdown = [("Winter Sampler", 2140), ("Autumn Fox", 1502), ("Gift tag - Mom", 576)]
        today_total = 212
        year_total = 31904
    else:
        token = os.environ["NOTION_TOKEN"]
        database_id = os.environ["NOTION_DATABASE_ID"]
        ds_id = resolve_data_source_id(token, database_id)
        month_total, breakdown, today_total, year_total = fetch_stats(token, ds_id, now.date())

    path = render_dashboard(
        month_label=month_label,
        total_stitches=month_total,
        projects=breakdown[:6],
        today_count=today_total or None,
        year_total=year_total,
        updated_at=now,
        out_path=OUT_PATH,
    )
    print(
        f"Wrote {path}: {month_total} stitches in {month_label} "
        f"({today_total} today, {year_total} this year)"
    )


if __name__ == "__main__":
    main()
