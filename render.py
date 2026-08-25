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
    w, bbox = _text_w(draw, text, font)
    return x0 + ((x1 - x0) - w) / 2 - bbox[0]


def render_dashboard(
    month_label: str,
    total_stitches: int,
    projects: list[tuple[str, int]] | None = None,
    today_count: int | None = None,
    year_total: int | None = None,
    updated_at: datetime | None = None,
    out_path: str = "dash.png",
):
    """
    month_label: e.g. "August 2026"
    total_stitches: the big number
    projects: optional [(name, count), ...] breakdown, shown in the right column
    today_count: optional stitches worked today, shown as a small pill
    year_total: optional stitches worked this calendar year, shown in the footer
    updated_at: when this image was generated (defaults to now)
    """
    updated_at = updated_at or datetime.now(ZoneInfo("UTC")).astimezone(LOCAL_TZ)

    img = Image.new("L", (WIDTH, HEIGHT), color=255)  # 255 = white
    draw = ImageDraw.Draw(img)

    # --- Header: centered serif brand line ---
    f_brand = _font(FONT_SERIF, 88)
    draw.text((_center_x(draw, HEADER_TEXT, f_brand, 0, WIDTH), 28), HEADER_TEXT, font=f_brand, fill=0)

    top = 206
    left_x = MARGIN
    left_w = DIVIDER_X - MARGIN - 40

    # --- Left column: month label, big number, caption, today-pill ---
    f_label = _font(FONT_SERIF, 60)
    label = month_label

    # Big numeral and the right-column project breakdown are intentionally
    # left at their existing size while everything else around them grows.
    f_number = _font(FONT_NUMERAL, 230)
    number_text = f"{total_stitches:,}"
    while _text_w(draw, number_text, f_number)[0] > left_w and f_number.size > 120:
        f_number = _font(FONT_NUMERAL, f_number.size - 10)

    f_caption = _font(FONT_SERIF, 66)
    caption = "stitches this month"

    f_pill = _font(FONT_NUMERAL, 52)
    pill_text = f"+{today_count:,} today" if today_count is not None else None

    y = top
    draw.text((left_x, y), label, font=f_label, fill=0)
    y += 82 + 26

    draw.text((left_x, y), number_text, font=f_number, fill=0)
    y += f_number.size + 4 + 26

    draw.text((left_x, y), caption, font=f_caption, fill=0)
    y += 88 + 36

    if pill_text:
        pad_x, pad_y = 36, 23
        bbox = draw.textbbox((0, 0), pill_text, font=f_pill)
        box_w = (bbox[2] - bbox[0]) + 2 * pad_x
        box_h = (bbox[3] - bbox[1]) + 2 * pad_y
        draw.rounded_rectangle([left_x, y, left_x + box_w, y + box_h], radius=box_h / 2, outline=0, width=3)
        draw.text((left_x + pad_x, y + pad_y - bbox[1]), pill_text, font=f_pill, fill=0)

    # --- Vertical divider (stops above the footer rule) ---
    divider_bottom = HEIGHT - MARGIN - 60
    draw.line([(DIVIDER_X, top - 10), (DIVIDER_X, divider_bottom)], fill=0, width=3)

    # --- Right column: per-project breakdown ---
    right_w = RIGHT_X1 - RIGHT_X0
    if projects:
        f_head = _font(FONT_SERIF, 32)
        head = "By project"
        head_y = top + 4
        draw.text((RIGHT_X0, head_y), head, font=f_head, fill=0)

        f_proj_name = _font(FONT_SERIF, 38)
        f_proj_count = _font(FONT_NUMERAL, 36)
        row_y = head_y + 60
        row_h = 64
        max_name_w = right_w - 165  # leave room for the count on the right
        for name, count in projects:
            display_name = name
            while _text_w(draw, display_name, f_proj_name)[0] > max_name_w and len(display_name) > 1:
                display_name = display_name[:-1]
            if display_name != name:
                display_name = display_name.rstrip() + "…"
            draw.text((RIGHT_X0, row_y), display_name, font=f_proj_name, fill=0)

            count_text = f"{count:,}"
            count_w, _ = _text_w(draw, count_text, f_proj_count)
            draw.text((RIGHT_X1 - count_w, row_y), count_text, font=f_proj_count, fill=0)

            row_y += row_h
            if row_y > divider_bottom - 20:
                break

    # --- Footer: full-width rule, then annual total + updated stamp centered ---
    footer_rule_y = HEIGHT - MARGIN - 74
    draw.line([(MARGIN, footer_rule_y), (WIDTH - MARGIN, footer_rule_y)], fill=0, width=2)

    if year_total is not None:
        footer = (
            f"{year_total:,} stitches this year   ·   "
            f"updated {updated_at.strftime('%b %d, %Y %-I:%M %p %Z')}"
        )
    else:
        footer = f"updated {updated_at.strftime('%b %d, %Y %-I:%M %p %Z')}"

    # Shrink-to-fit: this line's length varies with the date/numbers, so
    # keep it from ever running past the margins on a long day.
    footer_max_w = WIDTH - 2 * MARGIN
    f_footer = _font(FONT_SERIF, 54)
    while _text_w(draw, footer, f_footer)[0] > footer_max_w and f_footer.size > 30:
        f_footer = _font(FONT_SERIF, f_footer.size - 2)

    draw.text(
        (_center_x(draw, footer, f_footer, 0, WIDTH), HEIGHT - MARGIN - 56), footer, font=f_footer, fill=0
    )

    img.save(out_path)
    return out_path


if __name__ == "__main__":
    # Demo render with placeholder data
    render_dashboard(
        month_label="August 2026",
        total_stitches=4218,
        projects=[
            ("Winter Sampler", 2140),
            ("Autumn Fox", 1502),
            ("Gift tag - Mom", 576),
        ],
        today_count=212,
        year_total=31904,
        out_path="dash_demo.png",
    )
    print("Wrote dash_demo.png")
