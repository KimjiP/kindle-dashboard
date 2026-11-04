#!/bin/sh
# Turn the light off. Tap it in the Kindle library.
# Talks to the bulb over the home Wi-Fi with its LAN Control (JSON over TCP, port 55443).
BULB=192.168.1.43  # the bulb's address; if it changes, update it in all lights-*.sh

# Keep the connection open for a second, so nc can read the bulb's answer before it hangs up.
if (printf '%s\r\n' '{"id":1,"method":"set_power","params":["off","smooth",500]}'; sleep 1) | nc -w 2 "$BULB" 55443 | grep -q '"ok"'; then
    echo "Light off"
else
    echo "No answer from the bulb at $BULB. Is it switched on at the wall?"
fi
