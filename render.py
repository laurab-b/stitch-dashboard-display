"""
Renders the stitch-count dashboard as an e-ink-friendly PNG for a
Kindle Paperwhite 3 (7th generation, 2015 — 1072x1448 px native panel,
300ppi, 16-level grayscale), landscape orientation, "Serif Label" style.

Landscape means this image is authored at 1448x1072 (width x height) —
rotated 90 degrees from the panel's native portrait framebuffer. Most
screensaver-fetch setups (KOReader's sleep screen included) rotate the
image to fit automatically, but confirm on your own device; if yours
doesn't, rotate this output 90 degrees as a post-processing step before
serving it.

Style: Lora (a serif) carries the header, month label, caption, and
project names — warmer than a plain grotesque. The big number and the
"+N today" pill stay in a bold sans (DejaVu Sans Bold) since a display
serif at that size gets harder to read at a glance on e-ink. Pure
black-on-white throughout, no gradients or thin hairlines that fall
apart on e-ink.
"""

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from zoneinfo import ZoneInfo

WIDTH, HEIGHT = 1448, 1072

# The GitHub Actions runner that generates this image daily runs on UTC,
# not LB's local time — convert the "updated at" stamp to Pacific so the
# footer shows the time she'd actually recognize.
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

DEJAVU_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_NUMERAL = f"{DEJAVU_DIR}/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"

MARGIN = 56
# Left (stat) column vs. right (breakdown) column, split by a vertical divider.
DIVIDER_X = 860
RIGHT_X0 = DIVIDER_X + 56
RIGHT_X1 = WIDTH - MARGIN

HEADER_TEXT = "laura's stitching"


def _font(path, size):
    return ImageFont.truetype(path, size)


def _text_w(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox


def _center_x(draw, text, font, x0, x1):
