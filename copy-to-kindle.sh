#!/bin/bash
# Copy the Kindle scripts in kindle/ to the Kindle, then eject it.
# Plug the Kindle into the Mac by USB first.
set -euo pipefail
cd "$(dirname "$0")"

KINDLE=/Volumes/Kindle
if [ ! -d "$KINDLE/documents" ]; then
    echo "No Kindle at $KINDLE. Is it plugged in?"
    exit 1
fi

# -X skips macOS extra data, which would show up as "._name" files in the Kindle library.
cp -X kindle/*.sh "$KINDLE/documents/"
echo "Copied to the Kindle: $(cd kindle && echo *.sh)"

# The key that decrypts the dashboard image, and the token that lets the Kindle ask GitHub for
# a new one. They go in the main folder, not documents/, so they don't show up in the library.
for secret in dashboard.key github.token; do
    if [ -f "$secret" ]; then
        cp -X "$secret" "$KINDLE/$secret"
        echo "Copied $secret"
    fi
done

# The pictures that the dashboard draws into its header ("Inside 21°", "Updating"),
# made fresh by render.py.
.venv/bin/python render.py --room >/dev/null
mkdir -p "$KINDLE/dashboard-room"
cp -X kindle/room/*.png "$KINDLE/dashboard-room/"
echo "Copied the header pictures"

# macOS still tags new files, and on the Kindle's FAT32 drive it keeps the tag in a
# "._name" file. A "._name.sh" would show up in the library as a broken script, so remove them.
rm -f "$KINDLE"/documents/._*.sh "$KINDLE/._dashboard.key" "$KINDLE/._github.token" "$KINDLE"/dashboard-room/._*

diskutil eject "$KINDLE"
