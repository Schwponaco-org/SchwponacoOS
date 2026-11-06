#!/usr/bin/env python3
# Keeps the Super+Tab overview tied to the Super key: the overview may only be open while Super is held.
#   - Super already up when asked (a quick Super+Tab tap): exits 1 at once, so the overview switches
#     workspace without showing.
#   - Super held: prints "held" (the overview shows), then waits for Super's release and exits 0
#     (the overview switches and closes).
# It reads the kernel's key events directly, so it sees the release even when the overview hasn't got
# keyboard focus yet. It only listens; other apps still get every key.
# Data: /dev/input/by-path/*-event-kbd and by-id/*-event-kbd (needs the `input` group).
import fcntl
import glob
import select
import struct
import sys

KEY_LEFTMETA, KEY_RIGHTMETA = 125, 126
SUPER = (KEY_LEFTMETA, KEY_RIGHTMETA)
EV_KEY = 1
EVIOCGKEY = (2 << 30) | (96 << 16) | (ord("E") << 8) | 0x18  # _IOR('E', 0x18, 96 bytes: KEY_MAX bits)
EVENT = struct.Struct("llHHi")  # struct input_event: time, type, code, value

devices = []
for path in set(glob.glob("/dev/input/by-path/*-event-kbd") + glob.glob("/dev/input/by-id/*-event-kbd")):
    try:
        devices.append(open(path, "rb", buffering=0))  # opened before the check, so no event slips between
    except OSError:
        pass


def held(dev):
    keys = fcntl.ioctl(dev, EVIOCGKEY, bytes(96))
    return any(keys[k // 8] >> (k % 8) & 1 for k in SUPER)


down = {dev for dev in devices if held(dev)}
if not down:
    sys.exit(1)
print("held", flush=True)

while down:
    for dev in select.select(list(down), [], [])[0]:
        data = dev.read(EVENT.size * 64)
        for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
            _, _, kind, code, value = EVENT.unpack_from(data, i)
            if kind == EV_KEY and code in SUPER and value == 0 and not held(dev):
                down.discard(dev)
sys.exit(0)
