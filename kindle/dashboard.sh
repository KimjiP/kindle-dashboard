#!/bin/sh
# Kindle dashboard. Tap it in the library to start.
# It stops the Kindle's own screens, then shows the dashboard and updates it every 15 minutes,
# except at night (00:00-06:00 Oslo time). When the battery is low, it shows a "please charge" bar.
# Before each update it asks GitHub to draw a new image, because GitHub's own schedule hardly
# ever runs. That needs a token in /mnt/us/github.token (see the README).
#
# While it runs:
#   tap a light button                          switch the light
#   tap anywhere else                           update now (takes about a minute)
#   hold a finger on it for 3 seconds, let go   stop, and bring back the normal Kindle
# Restarting the Kindle (hold the power button for about 40 seconds) stops it too.
# Nothing it changes survives a restart.

BASE=https://kimjip.github.io/kindle-dashboard
SELF=/mnt/us/documents/dashboard.sh
KEY_FILE=/mnt/us/dashboard.key
TOKEN_FILE=/mnt/us/github.token  # lets the Kindle start GitHub's run (see redraw)
RUN_URL=https://api.github.com/repos/KimjiP/kindle-dashboard/actions/workflows/dashboard.yml/dispatches
LOG=/mnt/us/dashboard.log
IMAGE=/tmp/dashboard.png
LOW_BATTERY=20  # percent
BUTTON_TOP=744  # the light buttons are below this line (see BUTTONS in render.py)
ROOM_OFFSET=0   # °C the battery reads above the room. A thermometer check (4 Nov 2026) found 0.

log() {
    # Kindle time is UTC. Writing fails while the Kindle is a USB drive; that's fine.
    echo "$(date -u '+%Y-%m-%d %H:%M') UTC  $*" >>"$LOG" 2>/dev/null
}

battery() {
    lipc-get-prop com.lab126.powerd battLevel
}

# Raw temperature readings, for the log: battery (x100), processor (in thousandths of a °C), battery (°C).
temps() {
    cat /sys/class/thermal/thermal_zone*/temp /sys/class/power_supply/*/temp 2>/dev/null | tr '\n' ' '
}

# The version with a "please charge" bar when the battery is low and not charging, else the normal one.
image_name() {
    if [ "$(battery)" -lt "$LOW_BATTERY" ] && [ "$(lipc-get-prop com.lab126.powerd isCharging)" != 1 ]; then
        echo dashboard-charge
    else
        echo dashboard
    fi
}

# The hour in Oslo, 00 to 23. The Kindle's clock is UTC; this TZ rule means CET, or CEST in summer.
oslo_hour() {
    TZ=CET-1CEST,M3.5.0,M10.5.0/3 date +%H
}

# Download and decrypt the newest image into $IMAGE. If anything fails, the old image stays.
# Returns 1 if the download failed, 2 if decrypting failed. The temp files are per process ($$),
# because a tap can start an update while the 15-minute loop is doing one.
fetch() {
    curl -fsS --max-time 60 -o "/tmp/dashboard.$$.enc" "$BASE/$(image_name).enc?t=$(date +%s)" || return 1  # ?t= skips cached copies
    openssl enc -d -aes-256-cbc -md sha256 -pass env:DASHBOARD_KEY \
        -in "/tmp/dashboard.$$.enc" -out "/tmp/dashboard.$$.png" || return 2
    mv "/tmp/dashboard.$$.png" "$IMAGE"
}

show() {
    eips -f -g "$IMAGE"  # -f: full refresh, so no ghosting
}

# Draw "Inside 21°" into the header: the battery's temperature minus ROOM_OFFSET, an estimate.
# GitHub can't know it, so the Kindle draws a picture made by "render.py --room" over the image.
# The place (396, 16) is ROOM_X, ROOM_Y in render.py.
show_room() {
    t=$(cat /sys/class/power_supply/*/temp 2>/dev/null | head -n 1)  # whole °C
    case "$t" in '' | *[!0-9]*) return ;; esac  # not a number: draw nothing
    eips -g "/tmp/room/room-$((t - ROOM_OFFSET)).png" -x 396 -y 16
}

# Draw "Updating ..." over "Updated 12:21" in the header while a new image is on its way.
# The place (476, 16) is UPDATING_X, UPDATING_Y in render.py.
show_updating() {
    eips -g /tmp/room/updating.png -x 476 -y 16
}

# When GitHub last published the image: the web server's Last-Modified header.
published() {
    curl -fsSI --max-time 30 "$BASE/dashboard.enc?t=$(date +%s)" | grep -i '^last-modified'
}

# Ask GitHub to draw a new image now, and wait until it's published (usually about a minute).
# Does nothing without the token.
redraw() {
    [ -n "$GITHUB_TOKEN" ] || return
    before=$(published)
    if ! curl -fsS --max-time 30 -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github+json" -d '{"ref":"main"}' "$RUN_URL"; then
        log "could not ask GitHub for a new image (no Wi-Fi? token expired?)"
        return
    fi
    for i in 1 2 3 4 5 6 7 8 9 10 11 12; do  # check every 15 seconds, for up to 3 minutes
        sleep 15
        [ "$(published)" != "$before" ] && return
    done
    log "GitHub took more than 3 minutes, so showing the image it has now"
}

# Get the newest image and show it. If that fails, show the old one again (this also clears
# "Updating"). $1 says what asked for the update.
update() {
    fetch
    case $? in
        0) log "updated ($1), battery $(battery)%, temps $(temps)" ;;
        1) log "download failed (no Wi-Fi?), showing the old image" ;;
        2) log "decrypt failed (wrong key?), showing the old image" ;;
    esac
    show
    show_room
}

# Tapped in the library. Get the first image now, so a problem leaves the Kindle as it was.
launch() {
    if [ ! -f "$KEY_FILE" ]; then
        echo "There is no $KEY_FILE. Run copy-to-kindle.sh on the Mac."
        exit 1
    fi
    export DASHBOARD_KEY="$(cat "$KEY_FILE")"
    [ -f "$TOKEN_FILE" ] && export GITHUB_TOKEN="$(cat "$TOKEN_FILE")"
    echo "Downloading the dashboard..."
    fetch >/dev/null 2>&1
    case $? in
        1) echo "Could not download the dashboard. Is Wi-Fi on?"; exit 1 ;;
        2) echo "Could not decrypt the dashboard. Does dashboard.key match the GitHub secret?"; exit 1 ;;
    esac

    # Run the loop from a copy in /tmp, in its own session. That way it keeps going when this
    # app closes, and when /mnt/us disappears because the Kindle is plugged into a computer.
    cp "$SELF" /tmp/dashboard.sh
    cp /mnt/us/documents/lights-*.sh /tmp/ 2>/dev/null  # for the light buttons
    mkdir -p /tmp/room && cp /mnt/us/dashboard-room/*.png /tmp/room/ 2>/dev/null  # "Inside 21°" pictures
    if command -v setsid >/dev/null 2>&1; then
        setsid sh /tmp/dashboard.sh loop </dev/null >/dev/null 2>&1 &
    else
        nohup sh /tmp/dashboard.sh loop </dev/null >/dev/null 2>&1 &
    fi
    echo "Dashboard started. Tap the screen to update it. Hold a finger on it for 3 seconds to stop."
}

# The loop, running in the background. Its output goes nowhere, so eips can't print on the screen.
run_loop() {
    trap 'why=tap' USR1  # sent by watch_touch on a tap. Set first: USR1 would otherwise stop the loop.
    # The log is kept across restarts (it grows about 10 KB a day), so a restart doesn't lose readings.
    log "starting as user $(id -u), battery $(battery)%"
    lipc-set-prop com.lab126.powerd preventScreenSaver 1  # no screensaver, no sleep

    # Stop the Kindle's own UI (home screen, status bar), so nothing draws over the dashboard.
    trap '' TERM  # stopping the UI can send TERM to processes it started, like this one
    if initctl stop lab126_gui; then
        log "stopped the Kindle UI"
    else
        lipc-set-prop com.lab126.pillow disableEnablePillow disable  # at least hide the status bar
        log "could not stop the Kindle UI, hid the status bar instead"
    fi
    sleep 3  # let the UI finish closing before we draw
    trap - TERM
    show
    show_room
    log "showing the dashboard"
    sh /tmp/dashboard.sh touch $$ &  # watch for taps; $$ lets it signal or stop this loop
    if [ -n "$GITHUB_TOKEN" ]; then
        show_updating
        why=start  # the image we have can be hours old, so get a new one right away
    else
        log "no $TOKEN_FILE, so the image only changes after a push to GitHub"
    fi

    while true; do
        if [ -z "$why" ]; then
            sleep 900 &  # 15 minutes,
            wait $!      # or less: a tap ends the wait early
            kill $! 2>/dev/null
        fi
        if [ -z "$why" ] && [ "$(oslo_hour)" -lt 6 ]; then
            # Night mode: no updates from midnight to 06:00, to save battery. Still redraw the
            # room temperature (a small update, no flash) and log the readings.
            show_room
            log "night mode, battery $(battery)%, temps $(temps)"
            continue
        fi
        redraw
        update "${why:-every 15 minutes}"
        why=  # taps made during the update are covered by it
    done
}

# The touchscreen is the input device that reports positions: its block in
# /proc/bus/input/devices has an "ABS" line.
touch_device() {
    awk '/^I:/ { ev = "" }
         /^H:/ && match($0, /event[0-9]+/) { ev = substr($0, RSTART, RLENGTH) }  # "H: Handlers=kbd event1"
         /^B: ABS=/ && ev != "" { print "/dev/input/" ev; exit }' /proc/bus/input/devices
}

# Watch the touchscreen. A tap (under 1 second) on a light button switches the light. A tap
# anywhere else shows "Updating" and asks the loop for a new image. A hold of 3 seconds or
# more stops the dashboard. $1 is the loop's process id.
# This Kindle's touchscreen (cyttsp5_mt) sends BTN_TOUCH 1 when a finger goes down and
# BTN_TOUCH 0 when it lifts, with the position in between.
watch_touch() {
    dev=$(touch_device)
    if [ -z "$dev" ]; then
        log "no touchscreen found, so taps won't work"
        return
    fi
    log "listening for taps on $dev ($(cat "/sys/class/input/${dev##*/}/device/name" 2>/dev/null))"
    exec 3<"$dev"
    while true; do
        # One read gets all the events waiting, 16 bytes each. hexdump turns them into
        # lines of "seconds microseconds type code value". (Each field is its own "1/n" unit:
        # with "2/4", hexdump drops the space after the last of the two.)
        dd bs=4096 count=1 <&3 >/tmp/touch.bin 2>/dev/null
        hexdump -v -e '1/4 "%u " 1/4 "%u " 1/2 "%u " 1/2 "%u " 1/4 "%d" "\n"' /tmp/touch.bin >/tmp/touch.txt
        while read -r sec usec type code value; do
            case "$type $code $value" in
                "3 53 "*) x=$value ;;            # ABS_MT_POSITION_X
                "3 54 "*) y=$value ;;            # ABS_MT_POSITION_Y
                "1 330 1") s0=$sec u0=$usec ;;   # finger down
                "1 330 0")                       # finger up
                    [ -z "$s0" ] && continue     # it went down before we were listening
                    held=$(( (sec - s0) * 1000 + (usec - u0) / 1000 ))  # milliseconds
                    s0=
                    if [ "$held" -ge 3000 ]; then
                        stop_dashboard "$1"
                    elif [ "$held" -lt 1000 ]; then
                        if [ "$y" -ge "$BUTTON_TOP" ]; then
                            press_button "$x"
                        else
                            show_updating
                            kill -USR1 "$1"  # the loop gets the new image, so taps keep working
                        fi
                        exec 3<&- 3<"$dev"  # forget taps made while it was busy
                        break
                    fi ;;
            esac
        done </tmp/touch.txt
    done
}

# A tap on the light buttons: four equal slots from x=28 to x=572 (see BUTTONS in render.py).
# Runs the matching lights-*.sh, which launch copied to /tmp. $1 is the tap's x.
press_button() {
    case $(( ($1 - 28) / 136 )) in
        0) light=on ;;
        1) light=off ;;
        2) light=warm ;;
        *) light=dim ;;
    esac
    log "tap at $x,$y: lights-$light: $(sh "/tmp/lights-$light.sh")"
}

# Stop the dashboard and bring back the normal Kindle. $1 is the loop's process id.
stop_dashboard() {
    eips -c
    eips 2 2 "Starting the normal Kindle..."
    kill "$1"
    lipc-set-prop com.lab126.powerd preventScreenSaver 0
    lipc-set-prop com.lab126.pillow disableEnablePillow enable  # in case only the status bar was hidden
    initctl start lab126_gui
    log "stopped by a 3-second hold, Kindle UI started again"
    exit 0
}

case "$1" in
    loop) run_loop ;;
    touch) watch_touch "$2" ;;
    *) launch ;;  # tapped in the library
esac
