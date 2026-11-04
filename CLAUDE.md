# Kindle E-ink Dashboard: Project Brief

Paste this into Claude Code (or save it as `CLAUDE.md` in a new repo).

## Goal

Turn my jailbroken Kindle into a wall/desk e-ink dashboard for home.
A server makes a 600x800 grayscale PNG. The Kindle downloads it and shows it, on a loop.
Later: control a Xiaomi bulb from the Kindle, and add a room temperature sensor.

Keep code simple, in Python. The computer side runs on a Mac.
Write in plain, simple English in docs and comments.

## What is already done and tested

- **Device:** Kindle 10th gen (2019, basic model). Screen 600x800, 167 ppi, touch, front light.
- **Jailbreak:** WinterBreak2 (jb.sh v2.5.0). Works. Updates are blocked by the jailbreak.
  Filler files are already deleted.
- **Tools installed by the jailbreak:**
  - KPM (Kindle Package Manager), run via `;kpm` in the search bar.
  - **sh_integration:** any `.sh` file in `documents/` shows up in the library like a book.
    Tapping it runs it. Its stdout/stderr is drawn on screen.
- **No KUAL.** The wiki now lists KUAL as legacy, and the PEKI author says not to use it on
  modern devices. We use `.sh` files in the library instead. Don't add KUAL.
- **Mounting:** Kindle shows up on the Mac as `/Volumes/Kindle` (FAT32, so max 4 GB per file).
  On the Kindle, the same folder is `/mnt/us/`. So `/Volumes/Kindle/documents/x.sh` is
  `/mnt/us/documents/x.sh` on the device.
- **Tested and working:**
  - A `hello.sh` in `documents/` runs when tapped.
  - `eips -c` then `eips -g /mnt/us/documents/test.png` shows a 600x800 grayscale PNG.
    Gray levels look clean.
- **Known problems to fix:**
  1. `eips` prints debug text, and sh_integration draws it on screen. Redirect all output:
     `> /dev/null 2>&1`.
  2. The Kindle's own status bar (clock at top left) draws over our image. The dashboard
     script must hide or pause the Kindle UI while it runs (look into stopping the
     framework / disabling pillow, and keep the screensaver off, e.g.
     `lipc-set-prop com.lab126.powerd preventScreenSaver 1`). Check what works on this
     firmware. Make sure a reboot brings the normal Kindle back.
  3. Kindle system time is UTC. Don't rely on it. The server draws the time in Europe/Oslo.

## Architecture

### Server side (free)

- A GitHub repo with a Python script (Pillow, or HTML + Playwright screenshot, whichever
  looks better on e-ink).
- GitHub Actions runs it on a schedule (every 15 to 30 min. GitHub cron can be late, that's OK).
- Output: `dashboard.png`, 600x800, 8-bit grayscale. Published with GitHub Pages.
- Design for e-ink: high contrast, big text, few gray levels, no thin lines, no colors.

**Privacy note:** GitHub Pages is public. Anyone with the URL can see the image. That's fine
for weather and transit. For calendar items, either:
- keep calendar off the public image, or
- use an unguessable file path, or
- host the image somewhere private (Cloudflare R2 with a secret URL, etc.).
Ask me before putting calendar data in a public place.
Also keep where I live out of the repo: no stop names, stop IDs, routes or exact coordinates
in code, docs or commit messages. They go in `.env` and GitHub secrets (`STOPS`, `ROUTES`).

### Kindle side

One `dashboard.sh` in `documents/`. When tapped, it:
1. Hides the Kindle UI and stops the screensaver.
2. Loops: download PNG -> full refresh (`eips -f -g`) -> sleep 15 min.
3. Handles no Wi-Fi: keep the last image, try again next round. Don't hang.
4. Does a full refresh every time to avoid ghosting.

Check first which downloader works over HTTPS on this Kindle (`curl` or `wget`). Old TLS
can be a problem.

Also make a `copy-to-kindle.sh` (on the Mac) that copies the Kindle scripts to
`/Volumes/Kindle/documents/` and ejects.

## Phase 1: content (no smart home needed)

Layout idea (portrait, 600x800):
- **Header:** day and date, "Updated HH:MM" (Oslo time).
- **Weather for Oslo** from MET Norway / Yr (`api.met.no` locationforecast, free).
  Now, today high/low, rain chance, next few hours. Use Oslo city centre's coordinates.
  MET requires a User-Agent that names the app,
  e.g. `kindle-dashboard github.com/<repo>`. Don't put my email in it.
- **Next departures from my stop** (T-bane and bus) from Entur's free Journey Planner API
  (GraphQL). Needs an `ET-Client-Name` header. Look up the stop place IDs with
  Entur's geocoder.
- **Today's calendar** from a Google Calendar secret iCal URL (store it as a GitHub secret).
  See privacy note above.
- **Daily focus / todo:** read from a simple text or markdown file in the repo that I can edit.

## Phase 2: Xiaomi bulb

- Bulb: **Xiaomi Mi LED Smart Bulb (White and Color), model MJDP02YL.**
- Needs **2.4 GHz** Wi-Fi.
- Control options, try in this order:
  1. Yeelight **LAN control** (JSON over TCP, port 55443). Simple enough to send from the
     Kindle with `nc`.
  2. If not supported: `python-miio` with the device token.
- On the Kindle: one script per action in the library, e.g. `lights-on.sh`, `lights-off.sh`,
  `lights-warm.sh`, `lights-dim.sh`. Touch buttons on the dashboard can come later.
- Note: the bulb is on my home network, so control must run from the Kindle (or another
  device at home), not from GitHub Actions.

## Phase 3: room temperature

- A phone is not a good sensor (only battery temperature).
- Options: Xiaomi Mijia Bluetooth thermometer (needs a BLE reader like a Pi or ESP32),
  or an ESP32 + temp sensor that posts readings over Wi-Fi.
- An ESP32 build is fine.
- Show room temp and humidity on the dashboard.

## Nice to have later

- Touch buttons on the dashboard (read touch input on the Kindle).
- Battery level on the image, and a low-battery warning.
- A night mode (no refresh between midnight and 6:00 to save battery).

## Start here

1. Make the repo and a local `render.py` that writes `dashboard.png` with fake data.
   Show me the image.
2. Add real weather, then Entur, then calendar.
3. Set up GitHub Actions + Pages.
4. Write `dashboard.sh`, test on the Kindle, fix the status bar overlay.
