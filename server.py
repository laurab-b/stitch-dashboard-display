"""
Tiny local server that serves the latest dash.png and regenerates it on
a timer. Point the Kindle's screensaver-fetch extension at
http://<this-machine-ip>:8080/dash.png

Only worth using if you have something at home that's on most of the
time (a Raspberry Pi, an old laptop, a NAS). If you don't, skip this
entirely and use the GitHub Actions approach in the setup guide instead
— for a once-a-month or once-a-day number, a cron-committed PNG on
GitHub Pages is simpler than keeping a server running.
"""

import os
import threading
import time

from flask import Flask, send_file

from main import main as regenerate

REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", str(6 * 60 * 60)))  # default: every 6h
OUT_PATH = os.environ.get("DASH_OUT_PATH", "dash.png")

app = Flask(__name__)


def _refresh_loop():
    while True:
        try:
            regenerate()
        except Exception as e:
            print(f"refresh failed: {e}")
        time.sleep(REFRESH_SECONDS)


@app.route("/dash.png")
def dash():
    return send_file(OUT_PATH, mimetype="image/png")


if __name__ == "__main__":
    threading.Thread(target=_refresh_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
