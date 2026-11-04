"""Draw the Kindle dashboard: a 600x800 grayscale PNG.

Run:  python3 render.py          real data, writes dashboard.png and dashboard-charge.png
      python3 render.py --fake   made-up data, no internet needed
      python3 render.py --room   the "Inside 21°" pictures the Kindle draws (copy-to-kindle.sh runs this)

dashboard-charge.png is the same image with a "please charge" bar. The Kindle
downloads that one instead when its battery is low.
"""

import os
import sys
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

import departures
import events
import fake
import todo
import weather
from icons import weather_icon

WIDTH, HEIGHT = 600, 800  # Kindle 10th gen screen, portrait
MARGIN = 28
OSLO = ZoneInfo("Europe/Oslo")
HERE = Path(__file__).parent
FONT_FILE = HERE / "fonts" / "Inter.ttf"
OUT_FILE = HERE / "dashboard.png"
CHARGE_FILE = HERE / "dashboard-charge.png"
CHARGE_BAR = 40  # height of the "please charge" bar

# Light buttons along the bottom, in four equal slots across the screen.
# kindle/dashboard.sh uses the same numbers to tell which one was tapped.
BUTTONS = ["Light on", "Light off", "Warm", "Dim"]
BUTTON_TOP, BUTTON_BOTTOM = 744, 792

# "Inside 21°" pictures. GitHub can't know the room temperature, so the Kindle draws the
# right picture into the header, at the same place kindle/dashboard.sh uses (ROOM_X, ROOM_Y).
ROOM_DIR = HERE / "kindle" / "room"
ROOM_X, ROOM_Y = 396, 16
ROOM_SIZE = (60, 72)  # narrow, so it doesn't cover the sunrise and sunset times
# "Updating ...": the Kindle draws it over "Updated 12:21" while a new image is on its way. Same
# place in kindle/dashboard.sh. 96 wide covers the widest time ("00:00", 87 pixels).
UPDATING_X, UPDATING_Y = 476, 16
UPDATING_SIZE = (WIDTH - MARGIN - UPDATING_X, 72)

# The Kindle shows 16 grays: 0, 17, 34 ... 255. We only use black and white,
# plus the grays that smooth the edges of text and icons.
BLACK, WHITE = 0, 255


@lru_cache
def font(size, weight=400):
    """Inter at a pixel size and weight (100 thin ... 900 black)."""
    f = ImageFont.truetype(str(FONT_FILE), size)
    f.set_variation_by_axes([min(max(size, 14), 32), weight])  # optical size, weight
    return f


def deg(t):
    """4 -> '4°', -3 -> '−3°' (a real minus sign, wider than a hyphen)."""
    return f"{round(t)}°".replace("-", "−")


def fit(text, f, max_width):
    """Cut text with '…' so it fits in max_width pixels."""
    if f.getlength(text) <= max_width:
        return text
    while text and f.getlength(text + "…") > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


def clock(d, right, base, t, f):
    """Draw HH:MM ending at x=right. Every digit gets the same width, so times line up in columns."""
    digit = max(f.getlength(c) for c in "0123456789")
    x = right - 4 * digit - f.getlength(":")
    for ch in f"{t:%H:%M}":
        w = digit if ch.isdigit() else f.getlength(ch)
        d.text((x + w / 2, base), ch, font=f, fill=BLACK, anchor="ms")
        x += w


def label(d, text, y):
    """Section title in spaced capitals, then a thick rule to the right edge."""
    f = font(17, 700)
    x = MARGIN
    for ch in text.upper():
        d.text((x, y + 16), ch, font=f, fill=BLACK, anchor="ls")
        x += f.getlength(ch) + 1.5
    d.rectangle([x + 10, y + 8, WIDTH - MARGIN, y + 11], fill=BLACK)
    return y + 34


def note(d, text, base):
    """A plain line of text, e.g. when some data is missing."""
    d.text((MARGIN, base), text, font=font(24, 500), fill=BLACK, anchor="ls")


def draw_header(img, d, now, sun):
    d.rectangle([0, 0, WIDTH, 96], fill=BLACK)
    d.text((MARGIN, 52), now.strftime("%A"), font=font(46, 800), fill=WHITE, anchor="ls")
    f = font(24, 500)
    date = f"{now.day} {now:%B}"
    d.text((MARGIN, 81), date, font=f, fill=WHITE, anchor="ls")
    if sun:
        # After the date: a sun, then sunrise–sunset.
        x = MARGIN + f.getlength(date) + 20
        img.paste(ImageOps.invert(weather_icon("clearsky_day", 24)), (round(x), 81 - 21))
        d.text((x + 30, 81), f"{sun['rise']:%H:%M}–{sun['set']:%H:%M}", font=f, fill=WHITE, anchor="ls")
    d.text((WIDTH - MARGIN, 48), "Updated", font=font(18, 500), fill=WHITE, anchor="rs")
    d.text((WIDTH - MARGIN, 81), f"{now:%H:%M}", font=font(30, 700), fill=WHITE, anchor="rs")
    return 96


def draw_weather(img, d, w, y):
    y = label(d, "Weather · Oslo", y)
    if w is None:
        note(d, "Weather is not available right now", y + 30)
        return y + 46

    # Now: big icon and temperature on the left, details on the right.
    img.paste(weather_icon(w["symbol"], 112), (MARGIN - 8, y))
    temp = deg(w["temp"])
    size = 112
    while font(size, 800).getlength(temp) > 200:  # "−12°" is too wide at full size
        size -= 8
    big = font(size, 800)
    top, bottom = big.getbbox(temp, anchor="ls")[1::2]
    d.text((MARGIN + 116, y + 56 - (top + bottom) / 2), temp, font=big, anchor="ls")  # centred on the icon
    right = WIDTH - MARGIN
    room = right - (MARGIN + 116 + big.getlength(temp)) - 16
    small = font(26, 500)
    d.text((right, y + 34), fit(w["text"], font(28, 700), room), font=font(28, 700), anchor="rs")
    d.text((right, y + 68), f"↑ {deg(w['high'])}   ↓ {deg(w['low'])}", font=small, anchor="rs")
    if w["rain_chance"] is None:  # the compact forecast has the amount of rain, not the chance
        rain = f"{w['rain_mm']:g} mm"
    else:
        rain = f"{w['rain_chance']}%"  # chance of rain or snow in the next 6 hours
    d.text((right, y + 100), rain, font=small, anchor="rs")
    img.paste(weather_icon("drop", 24), (round(right - small.getlength(rain) - 28), y + 78))

    # Next hours: one column each.
    y += 124
    hours = w["hours"]
    col = (WIDTH - 2 * MARGIN) / len(hours)
    for i, h in enumerate(hours):
        cx = MARGIN + col * (i + 0.5)
        d.text((cx, y + 18), f"{h['time']:%H}", font=font(20, 500), anchor="ms")
        img.paste(weather_icon(h["symbol"], 40), (round(cx - 20), y + 24))
        d.text((cx, y + 92), deg(h["temp"]), font=font(28, 700), anchor="ms")
    return y + 96


def badge(img, d, x, mid, line, mode):
    """A train or bus picture and the line number, in a box: filled for metro, outlined for bus.
    Returns the right edge."""
    f = font(22, 800)
    icon = weather_icon("metro" if mode == "metro" else "bus", 22)
    w = max(76, 47 + f.getlength(line))  # same width up to 2 digits, so names line up
    box = [x, mid - 17, x + w, mid + 17]
    if mode == "metro":
        d.rounded_rectangle(box, radius=8, fill=BLACK)
        img.paste(ImageOps.invert(icon), (x + 10, mid - 11))
        color = WHITE
    else:
        d.rounded_rectangle(box, radius=8, fill=WHITE, outline=BLACK, width=4)
        img.paste(icon, (x + 10, mid - 11))
        color = BLACK
    d.text((x + 37 + (w - 47) / 2, mid + 8), line, font=f, fill=color, anchor="ms")  # centred after the picture
    return x + w


def draw_departures(img, d, rows, y):
    # Clock times, not "in 3 min": the image can be 15-30 min old when you look at it.
    y = label(d, "Metro & bus", y)
    if rows is None:
        note(d, "Departures are not available right now", y + 32)
        return y + 46

    first, later, name = font(26, 700), font(26, 400), font(26, 600)
    clock_width = 4 * max(first.getlength(c) for c in "0123456789") + first.getlength(":")
    step = clock_width + 14
    rights = [WIDTH - MARGIN - step * (2 - i) for i in range(3)]  # right edges of the 3 time columns
    for row in rows:
        base = y + 31  # text baseline
        x = badge(img, d, MARGIN, base - 10, row["line"], row["mode"]) + 14
        room = rights[0] - clock_width - x - 12
        d.text((x, base), fit(row["destination"], name, room), font=name, anchor="ls")
        for i, (t, right) in enumerate(zip(row["times"], rights)):
            clock(d, right, base, t, first if i == 0 else later)
        if not row["times"]:
            d.text((rights[0], base), "–", font=later, anchor="rs")
        y += 44
    return y


def draw_today(d, calendar, todo_list, y, bottom):
    """Calendar events, then todo items with an empty checkbox. As many rows as fit above bottom."""
    y = label(d, "Today", y)
    max_rows = (bottom - y) // 34
    todo_list = todo_list or []
    if calendar is None:
        rows = [("", "Calendar is not available right now")]
    else:
        calendar = calendar[: max_rows - min(len(todo_list), 1)]  # a busy day still leaves room for one todo
        rows = [("All day" if e["start"] is None else f"{e['start']:%H:%M}", e["title"]) for e in calendar]
    rows += [(None, item) for item in todo_list]
    if not rows:
        rows = [("", "Nothing planned")]

    f = font(24, 500)
    text_x = MARGIN + 100
    for when, text in rows[:max_rows]:
        base = y + 26
        x = text_x
        if when is None:
            d.rectangle([MARGIN + 1, base - 19, MARGIN + 20, base], outline=BLACK, width=4)
        elif when:
            d.text((MARGIN, base), when, font=font(24, 700), anchor="ls")
        else:
            x = MARGIN  # a message, not an event
        d.text((x, base), fit(text, f, WIDTH - MARGIN - x), font=f, anchor="ls")
        y += 34
    return y


def kindle_grays(img):
    """Round every pixel to one of the 16 grays the Kindle can show."""
    return img.point(lambda v: (v + 8) // 17 * 17)


def render(data, charge_bar=False):
    img = Image.new("L", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)
    bottom = BUTTON_TOP - 10  # the content stops above the light buttons
    if charge_bar:
        bottom -= CHARGE_BAR + 6  # and above the "please charge" bar
    y = draw_header(img, d, data["now"], data.get("sun"))
    y = draw_weather(img, d, data["weather"], y + 12)
    y = draw_departures(img, d, data["departures"], y + 12)
    y = draw_today(d, data["calendar"], data["todo"], y + 14, bottom)
    if y > bottom:
        print(f"Warning: content is {y - bottom}px too tall and gets cut off")
    if charge_bar:
        draw_charge_bar(d, bottom + 6)
    draw_buttons(d)
    return kindle_grays(img)


def draw_buttons(d):
    """The light buttons. The Kindle runs kindle/lights-*.sh when one is tapped."""
    f = font(22, 700)
    w = (WIDTH - 2 * MARGIN - 3 * 12) / len(BUTTONS)
    for i, text in enumerate(BUTTONS):
        x = MARGIN + i * (w + 12)
        d.rounded_rectangle([x, BUTTON_TOP, x + w, BUTTON_BOTTOM], radius=10, outline=BLACK, width=3)
        d.text((x + w / 2, (BUTTON_TOP + BUTTON_BOTTOM) / 2 + 8), text, font=f, fill=BLACK, anchor="ms")


def draw_charge_bar(d, top):
    """A black "please charge" bar, just above the light buttons."""
    mid = top + CHARGE_BAR // 2
    d.rounded_rectangle([MARGIN, top, WIDTH - MARGIN, top + CHARGE_BAR], radius=10, fill=BLACK)
    # An almost empty battery.
    x = MARGIN + 16
    d.rounded_rectangle([x, mid - 10, x + 36, mid + 10], radius=3, outline=WHITE, width=3)
    d.rectangle([x + 37, mid - 4, x + 40, mid + 4], fill=WHITE)  # the battery's tip
    d.rectangle([x + 6, mid - 4, x + 11, mid + 4], fill=WHITE)  # what's left
    d.text((x + 56, mid + 8), "Battery low. Please charge the Kindle.", font=font(22, 700), fill=WHITE, anchor="ls")


def header_picture(size, top, small_line, big_line):
    """A small black picture for the Kindle to draw into the header at y=top, styled like
    "Updated 12:21"."""
    img = Image.new("L", size, BLACK)
    d = ImageDraw.Draw(img)
    d.text((size[0], 48 - top), small_line, font=font(18, 500), fill=WHITE, anchor="rs")  # same baselines
    d.text((size[0], 81 - top), big_line, font=font(30, 700), fill=WHITE, anchor="rs")  # as draw_header
    return kindle_grays(img)


def room_pictures():
    """Write "Inside 0°" ... "Inside 40°", and "Updating ...", for the Kindle."""
    ROOM_DIR.mkdir(exist_ok=True)
    for t in range(41):
        header_picture(ROOM_SIZE, ROOM_Y, "Inside", deg(t)).save(ROOM_DIR / f"room-{t}.png", optimize=True)
    header_picture(UPDATING_SIZE, UPDATING_Y, "Updating", "…").save(ROOM_DIR / "updating.png", optimize=True)


def load_env():
    """Read KEY=value lines from .env, if there is one. It holds secrets for runs on the Mac."""
    env_file = HERE / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def safe(fetch, *args):
    """Get one kind of data. The services sometimes have short hiccups (like "502 Bad Gateway"),
    so if it fails, wait 10 seconds and try once more. If that fails too, return None, so the
    rest still shows."""
    name = f"{fetch.__module__}.{fetch.__name__}"
    for attempt in (1, 2):
        try:
            return fetch(*args)
        except Exception as e:
            print(f"{name} failed (try {attempt} of 2): {e!r}")
            if attempt == 1:
                time.sleep(10)
    return None


def main():
    if "--room" in sys.argv:
        room_pictures()
        print(f"Wrote the pictures the Kindle draws into the header to {ROOM_DIR}")
        return
    load_env()
    now = datetime.now(OSLO)
    if "--fake" in sys.argv:
        data = fake.data(now)
    else:
        data = {
            "now": now,
            "weather": safe(weather.fetch, now),
            "sun": safe(weather.sun, now),
            "departures": safe(departures.fetch, now),
            "calendar": safe(events.fetch, now),
            "todo": safe(todo.read),
        }
    render(data).save(OUT_FILE, optimize=True)
    render(data, charge_bar=True).save(CHARGE_FILE, optimize=True)
    print(f"Wrote {OUT_FILE} and {CHARGE_FILE.name}")


if __name__ == "__main__":
    main()
