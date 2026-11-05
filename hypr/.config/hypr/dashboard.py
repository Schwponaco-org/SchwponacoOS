#!/usr/bin/env python3
# Workspace 1 dashboard: VPN, Wi-Fi and battery status, time and date.
import json
import os
import subprocess
import time

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

VPN_SCRIPT = os.path.expanduser("~/Scripts/WaybarVPN.sh")
BATTERY = "/sys/class/power_supply/BAT0"
BACKGROUND = os.path.expanduser("~/Pictures/mies.jpg")

# sizes are recomputed from the window size so it fills any tile
CSS = """
window.dashboard {{ background: #191919; }}
/* frosted glass: blurred image under a translucent tint; scaled up so the blur doesn't fade at the edges */
.backdrop {{ filter: blur(0px); transform: scale(1.0); }}
.frost {{ background: rgba(25, 25, 25, 0.4); }}
.dashboard label {{ font-family: 'Helvetica Neue'; color: #BBBBBB; }}
.dashboard label.time {{ font-size: {time}px; font-weight: bold; letter-spacing: {track}px; color: #FFFFFF; }}
.dashboard label.date {{ font-size: {date}px; font-weight: 500; color: #888888; }}
.status label {{ font-size: {small}px; font-weight: 500; }}
.status label.key {{ color: #666666; }}
"""


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def vpn():
    try:
        out = json.loads(subprocess.run([VPN_SCRIPT], capture_output=True, text=True).stdout)
    except (OSError, ValueError):
        return "Unknown"
    name = out.get("text", "").split(" ", 1)[-1]  # drop the Nerd Font icon
    detail = out.get("tooltip", "").removeprefix("VPN active:").strip()
    return detail or name


def network():
    out = subprocess.run(["nmcli", "-t", "-f", "TYPE,NAME", "connection", "show", "--active"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        kind, _, name = line.partition(":")
        if kind == "802-11-wireless":
            return name
        if kind == "802-3-ethernet":
            return "Ethernet"
    return "Offline"


def battery():
    capacity, status = read(f"{BATTERY}/capacity"), read(f"{BATTERY}/status")
    if not capacity:
        return "None"
    # on AC at the charge limit the kernel says "Not charging" or "Full"
    on_ac = status in ("Charging", "Not charging", "Full")
    return f"{capacity}% · Charging" if on_ac else f"{capacity}%"


class Dashboard(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Dashboard")
        self.add_css_class("dashboard")
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.size = None

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay = Gtk.Overlay(overflow=Gtk.Overflow.HIDDEN)
        if os.path.exists(BACKGROUND):
            overlay.set_child(Gtk.Picture.new_for_filename(BACKGROUND))
            overlay.get_child().set_content_fit(Gtk.ContentFit.COVER)
            overlay.get_child().add_css_class("backdrop")
            overlay.add_overlay(Gtk.Box(css_classes=["frost"]))
        overlay.add_overlay(self.box)
        self.set_child(overlay)

        status = Gtk.Box(css_classes=["status"], spacing=48)
        self.status = {}
        for key in ("VPN", "Wi-Fi", "Battery"):
            item = Gtk.Box(spacing=8)
            item.append(Gtk.Label(label=key, css_classes=["key"]))
            self.status[key] = Gtk.Label()
            item.append(self.status[key])
            status.append(item)
        self.box.append(status)

        clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, valign=Gtk.Align.CENTER)
        self.time = Gtk.Label(xalign=0, css_classes=["time"])
        self.date = Gtk.Label(xalign=0, css_classes=["date"])
        clock.append(self.time)
        clock.append(self.date)
        self.box.append(clock)

        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        self.poll()
        GLib.timeout_add_seconds(5, self.poll)

    def tick(self):
        now = time.localtime()
        self.time.set_label(time.strftime("%H:%M", now))
        self.date.set_label(f"{time.strftime('%A', now)} {now.tm_mday} {time.strftime('%B %Y', now)}")
        return True

    def poll(self):
        self.status["VPN"].set_label(vpn())
        self.status["Wi-Fi"].set_label(network())
        self.status["Battery"].set_label(battery())
        return True

    def do_size_allocate(self, width, height, baseline):
        Gtk.ApplicationWindow.do_size_allocate(self, width, height, baseline)
        if (width, height) != self.size:
            self.size = (width, height)
            # the time is ~2.6em wide, so it is capped by width as well as height
            t = int(min(height * 0.36, width * 0.3))
            pad = int(min(width, height) * 0.06)
            self.box.set_margin_start(pad)
            self.box.set_margin_end(pad)
            self.box.set_margin_top(int(pad * 0.6))
            self.box.set_margin_bottom(int(pad * 0.6))
            self.css.load_from_string(CSS.format(
                time=t, track=int(-t * 0.03), blur=max(4, int(min(width, height) * 0.01)),
                date=max(14, int(t * 0.13)), small=max(12, int(t * 0.06))))


def activate(app):
    (app.get_active_window() or Dashboard(app)).present()


if __name__ == "__main__":
    app = Gtk.Application(application_id="hypr.dashboard")  # also the Hyprland window class
    app.connect("activate", activate)
    app.run(None)
