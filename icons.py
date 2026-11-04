"""Simple black-and-white weather icons, drawn with shapes.

Big flat shapes read better on e-ink than small detailed pictures.
The symbol names are MET Norway's symbol codes, e.g. "lightrain" or "fair_day".
"""

import math

from PIL import Image, ImageDraw

BLACK, WHITE = 0, 255


def weather_icon(symbol, size):
    """Return a size x size grayscale icon (black on white) for a MET symbol code."""
    big = size * 4  # draw 4x bigger, then shrink: this gives smooth edges
    img = Image.new("L", (big, big), WHITE)
    d = ImageDraw.Draw(img)
    u = big / 100  # we draw on a 100 x 100 grid

    def circle(x, y, r, fill=BLACK):
        d.ellipse([(x - r) * u, (y - r) * u, (x + r) * u, (y + r) * u], fill=fill)

    def stroke(x0, y0, x1, y1, width=8):
        # A thick line with round ends.
        d.line([x0 * u, y0 * u, x1 * u, y1 * u], fill=BLACK, width=round(width * u))
        circle(x0, y0, width / 2)
        circle(x1, y1, width / 2)

    def sun(x, y, r):
        circle(x, y, r)
        for i in range(8):
            a = i * math.pi / 4
            c, s = math.cos(a), math.sin(a)
            stroke(x + c * r * 1.5, y + s * r * 1.5, x + c * r * 1.9, y + s * r * 1.9, r * 0.32)

    def moon(x, y, r):
        circle(x, y, r)
        circle(x + r * 0.55, y - r * 0.35, r * 0.8, fill=WHITE)

    def cloud(x, bottom, w, fill=BLACK, grow=0):
        # A flat-bottomed pill with two bumps on top. "grow" makes it fatter,
        # which we use to cut a white gap around the cloud.
        h = 0.36 * w
        d.rounded_rectangle(
            [(x - w / 2 - grow) * u, (bottom - h - grow) * u, (x + w / 2 + grow) * u, (bottom + grow) * u],
            radius=(h / 2 + grow) * u,
            fill=fill,
        )
        circle(x - 0.17 * w, bottom - h, 0.2 * w + grow, fill)
        circle(x + 0.1 * w, bottom - 0.42 * w, 0.28 * w + grow, fill)

    def drops(n):
        for x in [50] if n == 1 else [36, 64] if n == 2 else [30, 50, 70]:
            stroke(x + 4, 74, x - 4, 90, 8)

    def flakes(xs):
        for x in xs:
            circle(x, 84, 6)

    night = "night" in symbol or "polartwilight" in symbol

    if symbol == "drop":  # not a MET code: the mark for "chance of rain"
        circle(50, 64, 26)
        d.polygon([(50 * u, 10 * u), (27 * u, 52 * u), (73 * u, 52 * u)], fill=BLACK)
    elif symbol == "metro":  # not a MET code: the front of a train, on its rails
        d.rounded_rectangle([22 * u, 6 * u, 78 * u, 78 * u], radius=16 * u, fill=BLACK)
        d.rounded_rectangle([31 * u, 18 * u, 69 * u, 44 * u], radius=5 * u, fill=WHITE)  # window
        circle(37, 62, 6, WHITE)  # lights
        circle(63, 62, 6, WHITE)
        stroke(36, 82, 26, 96, 8)  # rails
        stroke(64, 82, 74, 96, 8)
    elif symbol == "bus":  # not a MET code: the front of a bus
        d.rounded_rectangle([18 * u, 8 * u, 82 * u, 80 * u], radius=10 * u, fill=BLACK)
        d.rounded_rectangle([26 * u, 18 * u, 74 * u, 50 * u], radius=4 * u, fill=WHITE)  # windscreen
        circle(32, 66, 6, WHITE)  # lights
        circle(68, 66, 6, WHITE)
        d.rectangle([24 * u, 78 * u, 36 * u, 94 * u], fill=BLACK)  # wheels
        d.rectangle([64 * u, 78 * u, 76 * u, 94 * u], fill=BLACK)
        d.rectangle([10 * u, 20 * u, 18 * u, 34 * u], fill=BLACK)  # mirrors
        d.rectangle([82 * u, 20 * u, 90 * u, 34 * u], fill=BLACK)
    elif "thunder" in symbol:
        cloud(50, 62, 84)
        d.polygon([(p[0] * u, p[1] * u) for p in [(56, 66), (38, 86), (50, 86), (42, 100), (66, 78), (54, 78), (62, 66)]], fill=BLACK)
    elif "sleet" in symbol:
        cloud(50, 62, 84)
        stroke(42, 74, 34, 90, 8)
        flakes([64])
    elif "snow" in symbol:
        cloud(50, 62, 84)
        flakes([30, 50, 70])
    elif "rain" in symbol:
        cloud(50, 62, 84)
        drops(2 if symbol.startswith("light") else 3)
    elif "fog" in symbol:
        for y, x0, x1 in [(28, 20, 80), (46, 10, 90), (64, 16, 84), (82, 26, 74)]:
            stroke(x0, y, x1, y, 9)
    elif "partlycloudy" in symbol:
        if night:
            moon(36, 36, 22)
        else:
            sun(36, 36, 14)
        cloud(60, 86, 70, fill=WHITE, grow=6)
        cloud(60, 86, 70)
    elif "cloudy" in symbol:
        cloud(50, 80, 90)
    elif night:
        moon(46, 52, 34)
    else:  # clearsky, fair
        sun(50, 50, 20)

    return img.reduce(4)
