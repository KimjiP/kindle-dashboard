#!/bin/sh
# Kindle check: which tools does this Kindle have, and can it download over HTTPS?
# It only looks around and changes nothing. Turn Wi-Fi on before you tap it.
# The results go to kindle-check.txt in the Kindle's main folder
# (on the Mac: /Volumes/Kindle/kindle-check.txt).

OUT=${OUT:-/mnt/us/kindle-check.txt}
exec 3>&1 >"$OUT" 2>&1  # fd 3 is the screen; everything else goes to the file

echo "== Kindle check, $(date -u '+%Y-%m-%d %H:%M') UTC"
cat /etc/prettyversion.txt
uname -a

echo
echo "== Tools"
for tool in openssl curl wget nc base64 hexdump eips lipc-get-prop lipc-set-prop initctl; do
    echo "$tool: $(command -v "$tool" || echo MISSING)"
done

echo
echo "== Versions"
openssl version
curl --version | head -n 2

echo
echo "== HTTPS downloads (GitHub Pages; a 404 still means the connection worked)"
for url in https://kimjip.github.io/ https://pages.github.com/; do
    echo "$url"
    echo "  curl:    $(curl -sS --max-time 20 -o /dev/null -w '%{http_code}' "$url" 2>&1)"
    echo "  curl -k: $(curl -sSk --max-time 20 -o /dev/null -w '%{http_code}' "$url" 2>&1)"
    if result=$(wget -q -T 20 -O /dev/null "$url" 2>&1); then
        echo "  wget:    ok"
    else
        echo "  wget:    failed: $result"
    fi
done

echo
echo "== Decrypt test (the same format the dashboard image will use)"
# The text "kindle check ok", encrypted on a Mac with OpenSSL 3:
#   openssl enc -aes-256-cbc -md sha256 -salt -a -pass pass:kindle-check-test
echo 'U2FsdGVkX1+KKwXED7OLIeNkBSxZflVsm0wpQIr2x+s=' > /tmp/kindle-check.enc
text=$(openssl enc -d -aes-256-cbc -md sha256 -a -pass pass:kindle-check-test -in /tmp/kindle-check.enc)  # warnings go to the file, not into $text
if [ "$text" = "kindle check ok" ]; then
    echo "decrypt: OK"
else
    echo "decrypt: FAILED: $text"
fi
rm -f /tmp/kindle-check.enc

echo
echo "== Temperature sensors (to find one that can stand in for room temperature)"
for z in /sys/class/thermal/thermal_zone*; do
    [ -f "$z/temp" ] && echo "$z ($(cat "$z/type")): $(cat "$z/temp")"
done
for f in /sys/class/power_supply/*/temp /sys/class/hwmon/hwmon*/temp*_input; do
    [ -f "$f" ] && echo "$f: $(cat "$f")"
done
find /sys/devices -type f \( -name temp -o -name '*temperature' \) 2>/dev/null | head -20 | while read -r f; do
    echo "$f: $(cat "$f" 2>/dev/null)"
done
lipc-probe -v com.lab126.powerd 2>&1 | grep -i temp
echo "battTemperature: $(lipc-get-prop com.lab126.powerd battTemperature 2>&1)"
lipc-get-prop com.lab126.powerd status

echo "Done. Results are in kindle-check.txt. Plug the Kindle into the Mac." >&3
