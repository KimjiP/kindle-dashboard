"""Send one command to the bulb over Xiaomi's encrypted miIO protocol (UDP port 54321).

We used it once, to turn on the bulb's LAN Control (the Yeelight app has no switch for it):

    python3 tools/miio.py set_ps '["cfg_lan_ctrl","1"]'

Only needed again if the bulb is reset. It needs the bulb's token as BULB_TOKEN in .env
(get it with Xiaomi-cloud-tokens-extractor). The token is never printed. AES is done with
the openssl command, so no extra Python packages are needed.
"""

import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

BULB = "192.168.1.43"  # also in kindle/lights-*.sh
ENV = Path(__file__).parent.parent / ".env"

token_hex = next(
    line.split("=", 1)[1].strip().strip("\"'")
    for line in ENV.read_text().splitlines()
    if line.startswith("BULB_TOKEN=")
)
token = bytes.fromhex(token_hex)
key = hashlib.md5(token).digest()
iv = hashlib.md5(key + token).digest()


def aes(data, decrypt=False):
    """AES-128-CBC with the bulb's key, done by openssl."""
    args = ["openssl", "enc", "-aes-128-cbc", "-K", key.hex(), "-iv", iv.hex()] + (["-d"] if decrypt else [])
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)

# Hello: the bulb answers with its device id and its clock ("stamp").
sock.sendto(bytes.fromhex("21310020" + "ff" * 28), (BULB, 54321))
hello, _ = sock.recvfrom(1024)
device_id, stamp = hello[8:12], int.from_bytes(hello[12:16], "big")

# A 32-byte header, then the encrypted JSON command. The checksum covers both, plus the token.
method = sys.argv[1]
params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
payload = aes(json.dumps({"id": 1, "method": method, "params": params}).encode() + b"\0")
header = b"\x21\x31" + (32 + len(payload)).to_bytes(2, "big") + bytes(4) + device_id + (stamp + 1).to_bytes(4, "big")
checksum = hashlib.md5(header + token + payload).digest()
sock.sendto(header + checksum + payload, (BULB, 54321))

reply, _ = sock.recvfrom(4096)
print(aes(reply[32:], decrypt=True).rstrip(b"\0").decode())
