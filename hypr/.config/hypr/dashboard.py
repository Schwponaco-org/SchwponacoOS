#!/usr/bin/env python3
# Workspace 1 dashboard: VPN, Wi-Fi and battery status, time and date, Claude usage limits.
# Space toggles a system panel: CPU, memory and disk rings over btop's process view.
#
# Data sources:
#   - VPN: ~/.local/bin/waybar-vpn (scripts package); Wi-Fi: nmcli (networkmanager)
#   - battery: /sys/class/power_supply/BAT0
#   - Claude limits: https://api.anthropic.com/api/oauth/usage, the undocumented endpoint behind Claude's
#     usage page, signed in with terminal Claude Code's login (~/.claude/.credentials.json; run `claude` now
#     and then to keep it fresh). Cached in ~/.cache/dashboard-usage.json.
#   - CPU/memory/disk: python-psutil; processes: btop with your ~/.config/btop settings, in a vte4 terminal
#   - background: ~/Pictures/mies.jpg (not in the repo; any image works)
# Needs python-gobject, gtk4, vte4, python-psutil, btop, and the fonts Helvetica Neue, JetBrainsMono Nerd Font
# and Scratchpad Icons (built by waybar/build-scratchpad-icons.py).
import json
import os
import signal
import math
import subprocess
import threading
import time
import urllib.request

import gi
import psutil

gi.require_version("Gdk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
from gi.repository import Gdk, GLib, Graphene, Gtk, Pango, Vte

VPN_SCRIPT = os.path.expanduser("~/.local/bin/waybar-vpn")
BATTERY = "/sys/class/power_supply/BAT0"
BACKGROUND = os.path.expanduser("~/Pictures/mies.jpg")
CLAUDE_CREDENTIALS = os.path.expanduser("~/.claude/.credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_CACHE = os.path.expanduser("~/.cache/dashboard-usage.json")
BTOP_COLUMNS, BTOP_ROWS = 72, 24  # btop's size in the panel; it grows to fill a squeezed window

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
.dashboard label.percent {{ font-size: {pct}px; font-weight: bold; color: #FFFFFF; }}
.dashboard label.caption {{ font-size: {small}px; font-weight: 500; color: #888888; }}
/* Clawd from the waybar scratchpad font (waybar/build-scratchpad-icons.py) */
.stats {{ background: rgba(25, 25, 25, 0.92); padding: {panel}px; }}  /* kitty's #191919, a hint of frost left */
/* the GTK theme paints terminals white; btop's own colours come from its theme */
.stats vte-terminal {{ background-color: transparent; color: #BBBBBB; }}
.dashboard label.clawd {{ font-family: 'Scratchpad Icons'; font-size: {clawd}px; color: #BBBBBB; }}
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


def claude_usage():
    """Session (5 h) and weekly utilisation in percent, as on claude.ai's usage page; None until first known."""
    # The endpoint rate-limits hard (the Claude app polls it too), so the cache file remembers the last
    # answer and when to ask next, across restarts: every 5 minutes, backing off 15 min .. 1 h on failure.
    try:
        with open(USAGE_CACHE) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    usage = tuple(cache["usage"]) if cache.get("usage") else None
    if time.time() < cache.get("next", 0):
        return usage
    try:
        # terminal Claude Code's login (the desktop app keeps its own): fresh while `claude` gets used
        with open(CLAUDE_CREDENTIALS) as f:
            token = json.load(f)["claudeAiOauth"]["accessToken"]
        req = urllib.request.Request(USAGE_URL, headers={
            "Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        usage = data["five_hour"]["utilization"], data["seven_day"]["utilization"]
        cache = {"usage": usage, "next": time.time() + 300, "backoff": 0}
    except (OSError, ValueError, KeyError, TypeError):
        backoff = min(max(cache.get("backoff", 0) * 2, 900), 3600)
        cache = {"usage": usage, "next": time.time() + backoff, "backoff": backoff}
    try:
        with open(USAGE_CACHE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass
    return usage


class Ring(Gtk.Overlay):
    """Progress circle with the percentage in the middle."""

    def __init__(self):
        super().__init__()
        self.value = 0
        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self.draw)
        self.set_child(self.area)
        self.label = Gtk.Label(label="–", css_classes=["percent"])
        self.add_overlay(self.label)

    def set(self, percent):
        self.value = percent
        self.label.set_label("–" if percent is None else f"{percent:.0f}%")
        self.area.queue_draw()

    def draw(self, area, cr, w, h):
        line = max(2, min(w, h) * 0.035)
        r = (min(w, h) - line) / 2
        cr.set_line_width(line)
        cr.set_source_rgba(1, 1, 1, 0.12)
        cr.arc(w / 2, h / 2, r, 0, 2 * math.pi)
        cr.stroke()
        if self.value:
            cr.set_source_rgb(0xBB / 255, 0xBB / 255, 0xBB / 255)
            start = -math.pi / 2  # fill clockwise from 12 o'clock
            cr.arc(w / 2, h / 2, r, start, start + 2 * math.pi * min(self.value, 100) / 100)
            cr.stroke()


class BlurBehind(Gtk.Widget):
    """Draws the background blurred, clipped to a target widget: GTK has no backdrop-filter."""

    def __init__(self, texture, target):
        super().__init__(can_target=False)
        self.texture, self.target = texture, target

    def do_snapshot(self, snap):
        target = self.target()
        if not target:
            return
        ok, rect = target.compute_bounds(self)
        if not ok:
            return
        w, h = self.get_width(), self.get_height()
        tw, th = self.texture.get_width(), self.texture.get_height()
        scale = max(w / tw, h / th)  # same cover fit as the Gtk.Picture underneath, so it lines up
        snap.push_clip(rect)
        snap.push_blur(max(8, min(w, h) * 0.02))
        snap.save()
        snap.translate(Graphene.Point().init((w - tw * scale) / 2, (h - th * scale) / 2))
        self.texture.snapshot(snap, tw * scale, th * scale)
        snap.restore()
        snap.pop()
        snap.pop()


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
        self.blurred = None
        if os.path.exists(BACKGROUND):
            texture = Gdk.Texture.new_from_filename(BACKGROUND)
            overlay.set_child(Gtk.Picture.new_for_paintable(texture))
            overlay.get_child().set_content_fit(Gtk.ContentFit.COVER)
            overlay.get_child().add_css_class("backdrop")
            self.blurred = BlurBehind(texture, lambda: self.stats.get_child() if self.stats.get_reveal_child() else None)
            overlay.add_overlay(self.blurred)
            overlay.add_overlay(Gtk.Box(css_classes=["frost"]))
        overlay.add_overlay(self.box)
        self.set_child(overlay)

        self.status_bar = status = Gtk.Box(css_classes=["status"], spacing=48)
        self.status = {}
        for key in ("VPN", "Wi-Fi", "Battery"):
            item = Gtk.Box(spacing=8)
            item.append(Gtk.Label(label=key, css_classes=["key"]))
            self.status[key] = Gtk.Label()
            item.append(self.status[key])
            status.append(item)
        self.box.append(status)

        self.clock = clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, valign=Gtk.Align.CENTER)
        self.time = Gtk.Label(xalign=0, css_classes=["time"])
        self.date = Gtk.Label(xalign=0, css_classes=["date"])
        clock.append(self.time)
        clock.append(self.date)

        # Claude usage under the date, marked by Clawd
        self.usage = Gtk.Box(halign=Gtk.Align.START)
        self.clawd = Gtk.Label(label="\ue000", valign=Gtk.Align.START, css_classes=["clawd"])
        self.usage.append(self.clawd)
        self.rings = []
        for caption in ("Session", "Week"):
            item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            ring = Ring()
            item.append(ring)
            item.append(Gtk.Label(label=caption, css_classes=["caption"]))
            self.usage.append(item)
            self.rings.append(ring)
        clock.append(self.usage)

        row = Gtk.Box(vexpand=True)
        clock.set_hexpand(True)
        row.append(clock)
        self.stats = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.CROSSFADE,
                                  transition_duration=150, valign=Gtk.Align.CENTER, hexpand=False)
        self.narrow = False
        self.system, self.meters = [], None  # panel is built on first open: labels styled while hidden keep stale font sizes
        row.append(self.stats)
        self.box.append(row)

        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)  # before btop sees Space
        keys.connect("key-pressed", self.on_key)
        self.add_controller(keys)

        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        self.poll()
        GLib.timeout_add_seconds(5, self.poll)
        self.poll_usage()
        GLib.timeout_add_seconds(300, self.poll_usage)

    def build_stats(self):
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["stats"])
        self.meters = Gtk.Box(homogeneous=True)
        self.system = []
        for caption, align in (("CPU", Gtk.Align.START), ("Memory", Gtk.Align.CENTER), ("Disk", Gtk.Align.END)):
            item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, halign=align)
            ring = Ring()
            item.append(ring)
            item.append(Gtk.Label(label=caption, css_classes=["caption"]))
            self.meters.append(item)
            self.system.append(ring)
        panel.append(self.meters)

        # the real btop, with your own ~/.config/btop settings; transparent so the frost shows through
        self.term = Vte.Terminal(vexpand=True, scroll_on_output=False, cursor_blink_mode=Vte.CursorBlinkMode.OFF)
        # kitty's colours (kitty/current-theme.conf), with a clear background
        rgba = lambda spec: (lambda c: (c.parse(spec), c)[1])(Gdk.RGBA())
        self.term.set_colors(rgba("#BBBBBB"), rgba("rgba(0,0,0,0)"), [rgba(c) for c in (
            "#191919", "#DE6E7C", "#819B69", "#B77E64", "#6099C0", "#B279A7", "#66A5AD", "#BBBBBB",
            "#3D3839", "#E8838F", "#8BAE68", "#D68C67", "#61ABDA", "#CF86C1", "#65B8C1", "#8E8E8E")])
        self.term.connect("child-exited", self.btop_exited)
        panel.append(self.term)
        self.btop = None
        self.sampler = None
        self.size_meters()
        return panel

    def size_meters(self):
        for r in self.system:
            r.area.set_content_width(self.ring)
            r.area.set_content_height(self.ring)
        self.meters.set_margin_bottom(int(self.t * 0.2))
        px = max(10, self.t * 0.04)
        font = Pango.FontDescription.from_string("JetBrainsMono Nerd Font")
        font.set_absolute_size(px * Pango.SCALE)
        self.term.set_font(font)
        # hold the grid in pixels (JetBrains Mono: 0.6em advance, 1.32em line); VTE alone shrinks to fit
        self.term.set_size_request(int(px * 0.6 * BTOP_COLUMNS) + 1, int(px * 1.32 * BTOP_ROWS) + 1)

    def spawn_btop(self):
        def spawned(term, pid, error):
            self.btop = pid if pid > 0 else None
        self.term.spawn_async(Vte.PtyFlags.DEFAULT, os.path.expanduser("~"), ["btop"], ["COLORTERM=truecolor"],
                              GLib.SpawnFlags.SEARCH_PATH, None, None, -1, None, spawned)

    def btop_exited(self, term, status):
        # quit from inside btop (q): close the panel, a fresh one starts on the next open
        self.btop = None
        self.show_stats(False)

    def show_stats(self, show):
        if show and not self.stats.get_child():
            self.stats.set_child(self.build_stats())
        self.stats.set_reveal_child(show)
        if show:
            if self.btop:
                os.kill(self.btop, signal.SIGCONT)
            else:
                self.spawn_btop()
            self.term.grab_focus()
            self.poll_stats()
            if not self.sampler:
                self.sampler = GLib.timeout_add_seconds(2, self.poll_stats)
        else:
            self.set_focus(None)
            if self.btop:
                os.kill(self.btop, signal.SIGSTOP)  # frozen while hidden: no CPU at all
        self.update_layout()

    def update_layout(self):
        # squeezed window: the open panel takes the whole window
        full = self.narrow and self.stats.get_reveal_child()
        self.status_bar.set_visible(not full)
        self.clock.set_visible(not full)
        self.stats.set_hexpand(full)
        self.stats.set_valign(Gtk.Align.FILL if full else Gtk.Align.CENTER)
        if self.blurred:
            self.blurred.queue_draw()
        return False

    def on_key(self, controller, keyval, keycode, state):
        # Space opens and closes the panel; every other key goes to btop
        if keyval == Gdk.KEY_space:
            self.show_stats(not self.stats.get_reveal_child())
            return True
        return False

    def poll_stats(self):
        # only sampled while the panel is open, so the dashboard idles otherwise
        if not self.stats.get_reveal_child():
            self.sampler = None
            return False
        self.system[0].set(psutil.cpu_percent())
        self.system[1].set(psutil.virtual_memory().percent)
        self.system[2].set(psutil.disk_usage("/").percent)
        return True

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

    def poll_usage(self):
        # network call, so off the UI thread
        def fetch():
            usage = claude_usage()
            if usage:  # on a failed fetch the rings keep their last values ("–" until the first success)
                GLib.idle_add(lambda: [ring.set(v) for ring, v in zip(self.rings, usage)] and False)
        threading.Thread(target=fetch, daemon=True).start()
        return True

    def do_size_allocate(self, width, height, baseline):
        Gtk.ApplicationWindow.do_size_allocate(self, width, height, baseline)
        if self.blurred:
            self.blurred.queue_draw()  # the panel may have moved
        if (width, height) != self.size:
            narrow = width < height * 1.4
            if narrow != self.narrow:
                self.narrow = narrow
                GLib.idle_add(self.update_layout)  # not mid-allocation
            self.size = (width, height)
            # the time is ~2.6em wide, so it is capped by width as well as height
            t = int(min(height * 0.36, width * 0.3))
            pad = int(min(width, height) * 0.06)
            self.box.set_margin_start(pad)
            self.box.set_margin_end(pad)
            self.box.set_margin_top(int(pad * 0.6))
            self.box.set_margin_bottom(int(pad * 0.6))
            ring = int(t * 0.28)
            for r in self.rings:
                r.area.set_content_width(ring)
                r.area.set_content_height(ring)
            self.usage.set_spacing(int(ring * 0.35))
            self.ring, self.t = ring, t
            if self.meters:
                self.size_meters()
            self.usage.set_margin_top(int(t * 0.2))
            self.clawd.set_size_request(-1, ring)  # centres Clawd on the rings, above the captions
            self.css.load_from_string(CSS.format(
                time=t, track=int(-t * 0.03), blur=max(4, int(min(width, height) * 0.01)),
                date=max(14, int(t * 0.13)), small=max(12, int(t * 0.06)), pct=max(12, int(t * 0.06)), clawd=int(t * 0.14), panel=int(t * 0.1)))


def activate(app):
    (app.get_active_window() or Dashboard(app)).present()


if __name__ == "__main__":
    app = Gtk.Application(application_id="hypr.dashboard")  # also the Hyprland window class
    app.connect("activate", activate)
    app.run(None)
