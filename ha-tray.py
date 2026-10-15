#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Tubifix77
"""ha-tray: a tray icon that turns the Home Assistant container on and off.

The icon shows the real state, polled from Docker every few seconds:
  on        the full Home Assistant logo   (container running, page answers)
  starting  the logo, dimmed               (container running, page not answering yet;
                                            also while a stop is in progress)
  off       a white outline of the logo    (container stopped)
  error     the outline with a red mark    (Docker unavailable, or no such container)

Only the Home Assistant container is touched; other containers (an MQTT broker, say)
are left alone. The tray stores
no state of its own: the container's restart policy (unless-stopped) makes Docker
remember a manual stop across reboots. Quitting the tray leaves Home Assistant as it is.
"""

import argparse
import fcntl
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import warnings

import gi

# Gtk.StatusIcon is deprecated in GTK 3 but is the tray protocol this panel already has
# (no extra packages); the warnings say nothing new on every call.
warnings.filterwarnings("ignore", category=DeprecationWarning)
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

CONTAINER = "homeassistant"            # --container
PAGE_LOCAL = "http://localhost:8123/"   # --url
POLL_SECONDS = 3
STOP_TIMEOUT_S = 30          # time Home Assistant gets to shut down cleanly before Docker kills it
ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

STATUS_TEXT = {
    "on": "Home Assistant: Running",
    "starting": "Home Assistant: Starting...",
    "stopping": "Home Assistant: Stopping...",
    "off": "Home Assistant: Stopped",
    "missing": "Home Assistant: container not found",
    "nodocker": "Home Assistant: Docker unavailable",
}
ICON_FOR = {
    "on": "ha-on", "starting": "ha-starting", "stopping": "ha-starting",
    "off": "ha-off", "missing": "ha-error", "nodocker": "ha-error",
}


def docker_running():
    """True/False for the container's state, 'missing' or 'nodocker' when it cannot be read."""
    try:
        r = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return "nodocker"
    if r.returncode == 0:
        return r.stdout.strip() == "true"
    err = r.stderr.lower()
    # "no such object: homeassistant" (older Docker: "No such container"); a daemon that
    # cannot be reached says "failed to connect ... no such file", so check that first.
    if "connect" not in err and ("no such object" in err or "no such container" in err):
        return "missing"
    return "nodocker"


def page_answers():
    """True when Home Assistant's web server answers at all (any HTTP status counts)."""
    try:
        urllib.request.urlopen(PAGE_LOCAL, timeout=2).close()
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


class Tray:
    def __init__(self):
        self.state = None
        self.busy = None             # "starting" / "stopping" while a docker command runs
        self.error = None            # last failed command's message, shown in the menu
        self.size = 22
        self.polling = False

        self.icon = Gtk.StatusIcon()
        self.icon.set_title("Home Assistant")
        self.icon.connect("activate", self.on_click)
        self.icon.connect("popup-menu", self.on_popup)
        self.icon.connect("size-changed", self.on_size)
        self.icon.connect("notify::embedded", self.on_embedded)

        self.menu = Gtk.Menu()
        self.status_item = Gtk.MenuItem(label="Checking...")
        self.status_item.set_sensitive(False)
        self.error_item = Gtk.MenuItem(label="")
        self.error_item.set_sensitive(False)
        self.toggle_item = Gtk.MenuItem(label="Turn Home Assistant on")
        self.toggle_item.connect("activate", self.on_toggle)
        self.open_item = Gtk.MenuItem(label="Open Home Assistant")
        self.open_item.connect("activate", self.on_open)
        quit_item = Gtk.MenuItem(label="Quit tray")
        quit_item.connect("activate", lambda *_: Gtk.main_quit())
        for item in (self.status_item, self.error_item, Gtk.SeparatorMenuItem(),
                     self.toggle_item, self.open_item, Gtk.SeparatorMenuItem(), quit_item):
            self.menu.append(item)
        self.menu.show_all()
        self.error_item.hide()

        self.show("starting")
        self.poll()
        GLib.timeout_add_seconds(POLL_SECONDS, self.poll)

    # --- state -------------------------------------------------------------------------

    def poll(self):
        if not self.polling:
            self.polling = True
            threading.Thread(target=self.read_state, daemon=True).start()
        return True

    def read_state(self):
        running = docker_running()
        if running is True:
            state = "on" if page_answers() else "starting"
        elif running is False:
            state = "off"
        else:
            state = running
        GLib.idle_add(self.got_state, state)

    def got_state(self, state):
        self.polling = False
        if self.busy == "starting" and state == "off":
            state = "starting"       # docker start has not taken effect yet
        if self.busy == "stopping" and state in ("on", "starting"):
            state = "stopping"
        self.show(state)
        return False

    def show(self, state):
        if state == self.state:
            return
        self.state = state
        print("state", state, flush=True)
        self.redraw()
        self.status_item.set_label(STATUS_TEXT[state].replace("Home Assistant: ", ""))
        self.icon.set_tooltip_text(STATUS_TEXT[state])
        if state in ("on", "starting"):
            self.toggle_item.set_label("Turn Home Assistant off")
        else:
            self.toggle_item.set_label("Turn Home Assistant on")
        self.toggle_item.set_sensitive(self.busy is None and state in ("on", "starting", "off"))
        self.open_item.set_sensitive(state == "on")

    def redraw(self):
        path = os.path.join(ICON_DIR, ICON_FOR[self.state] + ".svg")
        self.icon.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(path, self.size, self.size))

    # --- actions -----------------------------------------------------------------------

    def on_toggle(self, _item):
        if self.busy:
            return
        if self.state in ("on", "starting"):
            self.busy = "stopping"
            cmd = ["docker", "stop", "--timeout", str(STOP_TIMEOUT_S), CONTAINER]
        else:
            self.busy = "starting"
            cmd = ["docker", "start", CONTAINER]
        self.error = None
        self.error_item.hide()
        self.show(self.busy)
        self.toggle_item.set_sensitive(False)
        threading.Thread(target=self.run, args=(cmd,), daemon=True).start()

    def run(self, cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=STOP_TIMEOUT_S + 30)
            err = None if r.returncode == 0 else (r.stderr.strip() or "docker failed")
        except (OSError, subprocess.TimeoutExpired) as e:
            err = str(e)
        GLib.idle_add(self.done, err)

    def done(self, err):
        self.busy = None
        if err:
            self.error = err
            self.error_item.set_label("Last action failed: " + err.splitlines()[-1][:80])
            self.error_item.show()
        self.state = None            # force the next poll to refresh menu and icon
        self.poll()
        return False

    def on_open(self, _item):
        Gio.AppInfo.launch_default_for_uri(PAGE_LOCAL, None)

    # --- tray --------------------------------------------------------------------------

    def on_click(self, icon):
        self.popup(icon, 1, Gtk.get_current_event_time())

    def on_popup(self, icon, button, time):
        self.popup(icon, button, time)

    def popup(self, icon, button, time):
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

    def on_embedded(self, icon, _prop):
        r = icon.get_geometry()[2]
        print(f"embedded in panel: {icon.is_embedded()} at {r.x},{r.y} {r.width}x{r.height}",
              flush=True)

    def on_size(self, _icon, size):
        if size > 0 and size != self.size:
            print("tray icon size", size, flush=True)
            self.size = size
            if self.state:
                self.redraw()
        return True


def single_instance():
    """Hold a lock for the session's lifetime; a second copy (menu launch at login) just exits."""
    run_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    lock = open(os.path.join(run_dir, "ha-tray.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("ha-tray is already running", file=sys.stderr)
        sys.exit(0)
    return lock


def parse_args():
    global CONTAINER, PAGE_LOCAL
    ap = argparse.ArgumentParser(description="Tray icon that turns a Home Assistant container on and off.")
    ap.add_argument("--container", default=CONTAINER,
                    help=f"name of the Docker container to switch (default: {CONTAINER})")
    ap.add_argument("--url", default=PAGE_LOCAL,
                    help=f"Home Assistant's page, checked and opened from the menu (default: {PAGE_LOCAL})")
    a = ap.parse_args()
    CONTAINER, PAGE_LOCAL = a.container, a.url


if __name__ == "__main__":
    parse_args()
    _lock = single_instance()
    Tray()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, Gtk.main_quit)   # SIGTERM
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, Gtk.main_quit)    # SIGINT
    Gtk.main()
