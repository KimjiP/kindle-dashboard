# Kindle dashboard

A jailbroken Kindle shows a 600x800 e-ink dashboard: weather, the next T-bane and
bus departures from a nearby stop, and today's calendar and todo list.

A Python script draws the image. GitHub Actions runs it, encrypts the image, and
publishes it with GitHub Pages. Every 15 minutes the Kindle asks GitHub for a new
image, then downloads it, decrypts it and shows it.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python render.py
```

This writes `dashboard.png`, and `dashboard-charge.png` with a "please charge"
bar for when the Kindle's battery is low. Add `--fake` to use made-up data (no
internet needed).

### Calendar

The calendar comes from your Google Calendar's secret iCal address. Anyone with
that address can read your calendar, so it never goes in git:

1. In Google Calendar, open Settings, pick your calendar, and find
   "Secret address in iCal format" under "Integrate calendar".
2. Copy `.env.example` to `.env` and paste the address after `CALENDAR_URL=`.

Without it, the dashboard shows no events.

### Departures

Your stops and lines also go in `.env`, so where you live stays out of git:

- `STOPS`: the stop place IDs, comma-separated, like `NSR:StopPlace:12345`.
  Find them with Entur's geocoder:
  https://api.entur.io/geocoder/v1/autocomplete?text=Jernbanetorget&layers=venue
- `ROUTES`: the rows to show, top to bottom, as the line and the destination on
  the front of the train or bus, comma-separated. Like `1 Frognerseteren, 31 Snarøya`.

## Where the data comes from

- **Weather:** MET Norway's Locationforecast (the data behind Yr), for Oslo.
  High and low are for the next 24 hours. The drop shows the chance of rain or
  snow in the next 6 hours. If MET's full forecast is broken, the dashboard uses
  its compact forecast, which has no chance of rain: the drop then shows the
  amount in mm.
- **Sunrise and sunset:** MET Norway's Sunrise service, shown after the date in
  the header.
- **Departures:** Entur's Journey Planner, for `STOPS` and `ROUTES`.
- **Calendar:** today's events that are not over yet, from `CALENDAR_URL`.
- **Todo:** `todo.md` in this repo. The repo is public, so keep private things
  out of it.

If one source fails, the script waits 10 seconds and tries again. If it fails
again, its part of the dashboard says so and the rest still shows.

## Publishing

`.github/workflows/dashboard.yml` runs when the Kindle asks for it (see
"GitHub token" below), on every push to `main`, and from the "Run workflow"
button in the Actions tab. It has no schedule: GitHub ran a 15-minute schedule
only twice in its first day. It draws both images, encrypts them, and publishes
only the encrypted files:

    https://kimjip.github.io/kindle-dashboard/dashboard.enc
    https://kimjip.github.io/kindle-dashboard/dashboard-charge.enc

The images show calendar events and this repo is public, so the plain PNGs are
never published. The workflow needs these repository secrets:

- `DASHBOARD_KEY`: the key that encrypts the image. On the Mac it is in
  `dashboard.key` (not in git). The Kindle has a copy at `/mnt/us/dashboard.key`.
- `CALENDAR_URL`: the secret iCal address.
- `STOPS` and `ROUTES`: the same as in `.env`.

To look at the published image on the Mac:

```bash
curl -fsS -o /tmp/dashboard.enc https://kimjip.github.io/kindle-dashboard/dashboard.enc
openssl enc -d -aes-256-cbc -md sha256 -pass file:dashboard.key -in /tmp/dashboard.enc -out /tmp/dashboard.png
open /tmp/dashboard.png
```

## Kindle

Scripts for the Kindle live in `kindle/`. Plug the Kindle in by USB and run
`./copy-to-kindle.sh`: it copies them (and `dashboard.key` and `github.token`)
to the Kindle and ejects it. They show up in the Kindle library; tap one to run it.

- `dashboard.sh`: the dashboard. Tap it in the library. It first downloads and
  decrypts the image; if that fails, it says why and changes nothing. Then it
  stops the Kindle's own UI, keeps the screensaver off, shows the dashboard and
  updates it every 15 minutes. Before each update it asks GitHub to draw a new
  image and waits until it's published, usually about a minute. If an update
  fails (no Wi-Fi), the old image stays. It logs to `dashboard.log` on the
  Kindle, with the battery level. The log is kept across restarts.

  Night mode: from midnight to 06:00 (Oslo time) it doesn't update, to save
  battery. Below 20% battery, when not charging, it shows the version with the
  "please charge" bar.

  While it runs, **tap a light button** along the bottom to switch the light,
  **tap anywhere else to update now** ("Updating …" shows in the header until
  the new image is in), and **hold a finger on the screen for 3 seconds, then
  let go, to stop it** and get the normal Kindle back.
  Restarting the Kindle (hold the power button for about 40 seconds) stops it
  too; nothing it changes survives a restart. The Kindle never sleeps while the
  dashboard runs, so it uses more battery than usual. Each update (and every 15
  minutes at night) also logs the Kindle's temperature sensors: the battery
  (x100), the processor (in thousandths of a °C), and the battery in °C.

  **Inside temperature:** the Kindle draws "Inside 21°" into the header, next
  to "Updated". It's an estimate: the battery sensor's reading (whole °C) minus
  `ROOM_OFFSET` in `dashboard.sh`. Checked against a thermometer on 4 Nov 2026
  (20.4 °C at night, 21.6 °C at noon), the battery read within about 1 °C of
  the room, so the offset is 0. While the Kindle charges, and for about 40
  minutes after, the battery is warmer and the reading can be up to 4 °C too
  high. GitHub can't know this number, so the Kindle draws a small
  picture over the image after each refresh (and every 15 minutes at night).
  The pictures come from `render.py --room`; `copy-to-kindle.sh` makes them
  and copies them to `dashboard-room/` on the Kindle.
- `kindle-check.sh`: checks what the Kindle can do (openssl, HTTPS downloads,
  temperature sensors) and writes the results to `kindle-check.txt` on the
  Kindle. It changes nothing.

What it found on this Kindle (10th gen, firmware 5.15.1.1):

- `curl` 7.76.1 downloads over HTTPS fine. Busybox `wget` can't do HTTPS.
- `openssl` 1.0.2q decrypts the dashboard image.
- The Kindle UI runs as the upstart jobs `lab126_gui`, `framework` and `pillow`
  (the status bar).

### GitHub token

To start GitHub's run, the Kindle needs a token in `github.token` (not in git).
It only gives control of this repo's GitHub Actions runs. It can't change code
or read secrets. To make one:

1. Open https://github.com/settings/personal-access-tokens/new (a fine-grained
   token).
2. Name it `kindle-dashboard`, and pick a long expiration, like a year (the
   default is 30 days).
3. Under Repository access, pick "Only select repositories", then this repo.
4. Under Permissions, add Actions and set it to "Read and write". Nothing else.
5. Generate it and copy it. In this folder, run `pbpaste > github.token`, then
   `./copy-to-kindle.sh`, then restart the dashboard on the Kindle.

If the token is missing or has expired, the dashboard still works, but the image
only changes after a push, and `dashboard.log` says so. If you sell the Kindle,
delete the token on GitHub.

## Light

The light is a Xiaomi Mi LED Smart Bulb (MJDP02YL), a Yeelight inside. The Kindle
switches it over the home Wi-Fi with the bulb's LAN Control: one line of JSON over
TCP port 55443, sent with `nc`. The four buttons at the bottom of the dashboard
run these scripts, and you can also tap them in the Kindle library when the
dashboard is stopped:

- `lights-on.sh`, `lights-off.sh`
- `lights-warm.sh`: warm white, full brightness
- `lights-dim.sh`: warm white at 10%

How it was set up:

- Adding the bulb in the Yeelight app only worked from an older phone. Newer
  phones lost the bulb halfway through setup.
- The Yeelight app has no LAN Control switch for this bulb, so it was turned on
  once with `tools/miio.py`, which speaks Xiaomi's encrypted protocol. That needs
  the bulb's token (from [Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor))
  as `BULB_TOKEN` in `.env`. Only needed again if the bulb is reset:

  ```bash
  python3 tools/miio.py set_ps '["cfg_lan_ctrl","1"]'
  ```

- The bulb's address, 192.168.1.43, is in the `lights-*.sh` scripts and in
  `tools/miio.py`. If the router ever gives it a new one, update them there.

## Files

- `render.py`: draws the dashboard.
- `weather.py`, `departures.py`, `events.py`, `todo.py`: get the data.
- `fake.py`: made-up data for `--fake`.
- `icons.py`: weather icons, drawn with simple shapes.
- `todo.md`: your todo list.
- `.github/workflows/dashboard.yml`: draws, encrypts and publishes the image.
- `kindle/`: scripts that run on the Kindle.
- `copy-to-kindle.sh`: copies them to the Kindle.
- `tools/miio.py`: sends one command to the bulb over Xiaomi's protocol (setup only).
- `fonts/`: the Inter font (SIL Open Font License, see `fonts/OFL.txt`).
- `CLAUDE.md`: the project brief and plan.

## Design notes

- Departures show clock times (20:46), not "in 3 min". The image can be
  15 to 30 minutes old when you look at it.
- Every pixel is rounded to one of the 16 grays the Kindle can show.
