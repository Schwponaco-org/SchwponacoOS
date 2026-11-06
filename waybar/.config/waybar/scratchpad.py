#!/usr/bin/env python3
# Waybar module for one scratchpad: prints its icon, with class "active" while it's shown.
# Replaces hyprland/workspaces' show-special, which loses track of special workspaces when
# windows move on and off them. Usage: scratchpad.py <name> <glyph>
# Data: Hyprland's event socket ($XDG_RUNTIME_DIR/hypr/<instance>/.socket2.sock) and `hyprctl -j monitors`.
import json
import os
import socket
import subprocess
import sys

name, glyph = sys.argv[1], sys.argv[2]
sock = os.path.join(os.environ["XDG_RUNTIME_DIR"], "hypr", os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket2.sock")


def state():
    try:
        monitors = json.loads(subprocess.run(["hyprctl", "-j", "monitors"], capture_output=True, text=True).stdout)
    except ValueError:
        return None
    shown = any(m["specialWorkspace"]["name"] == f"special:{name}" for m in monitors)
    return json.dumps({"text": f"<span font_family='Scratchpad Icons'>{glyph}</span>",
                       "class": "active" if shown else "", "tooltip": False})


last = state()
print(last, flush=True)
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(sock)
    # window titles in the events can hold any bytes; a strict decode would kill the module
    for line in s.makefile(encoding="utf-8", errors="replace"):
        # event names differ under the Lua config, so re-check on anything workspace-related
        if "special" in line or "workspace" in line or "window" in line or "mon" in line:
            current = state()
            if current and current != last:
                print(current, flush=True)
                last = current
