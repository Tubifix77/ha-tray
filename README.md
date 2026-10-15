# Home Assistant tray

A small icon in the panel of the homelab laptop that turns Home Assistant on and off, the
way the OneDrive icon does for OneDrive on Windows. It starts by itself when you log in.

## What the icon means

| icon | meaning |
|---|---|
| ![on](icons/ha-on.svg) filled white house with a black circuit | Home Assistant is **on** and its page answers |
| ![starting](icons/ha-starting.svg) dimmed logo | Home Assistant is **starting** (or stopping): the container runs, the page does not answer yet. Starting takes about 5 seconds here |
| ![off](icons/ha-off.svg) white outline | Home Assistant is **off** |
| ![error](icons/ha-error.svg) outline with a red mark | **Docker is unavailable**, or there is no container called `homeassistant`. Hover the icon to see which |

The icon checks the real state every 3 seconds, so it is correct even if Home Assistant was
started or stopped some other way (for example `docker compose up -d`).

## The menu

Click the icon (left or right button):

- **Running / Stopped / Starting... / Docker unavailable**: the current state.
- **Turn Home Assistant on** / **Turn Home Assistant off**: switches it. Greyed out while a
  switch is in progress. Turning off gives Home Assistant up to 30 seconds to save and shut
  down cleanly.
- **Open Home Assistant**: opens http://localhost:8123 in your browser. Only when it is on.
- **Quit tray**: closes the icon. Home Assistant stays as it is. The icon comes back at the
  next login, or start it from the application menu (**Home Assistant tray**).

If a switch fails, the reason is shown greyed out under the state line.

## What it switches, and what it leaves alone

It starts and stops **only the Home Assistant container**. **Mosquitto (the MQTT broker)
keeps running at all times**: the Potluck boards send their sensors to it, and it uses about
7 MB. Home Assistant uses about 530 MB when it is on.

The tray does not save anything itself. Docker remembers your choice: the containers use
`restart: unless-stopped`, so a Home Assistant you turned off stays off after a reboot, and
one you left on comes back on. (Checked on this laptop: when you turn it off, Docker writes
"manually stopped" into the container's saved state, and clears it when you turn it on. That
it then stays off across a reboot is what Docker's documentation says; it has not been
tried here with an actual reboot yet.)

One thing to know: `docker compose up -d` in `~/homeassistant` starts every service in the
file, so it turns Home Assistant on again. That is fine; the icon will follow.

## Install

It needs nothing new on the laptop: Python 3 with GTK (`python3-gi`, `gir1.2-gtk-3.0`) and
Docker, which are already there. Copy this folder to the laptop and run:

```sh
sh install.sh
```

This puts the program in `~/.local/share/ha-tray/`, adds it to the application menu, and makes
it start at login (`~/.config/autostart/ha-tray.desktop`). To start it right away without
logging out:

```sh
~/.local/share/ha-tray/ha-tray.py &
```

Running `install.sh` again updates it. Only one copy runs at a time; a second start just exits.

## Uninstall

```sh
sh uninstall.sh
```

It stops the icon and removes what `install.sh` wrote. Home Assistant is left as it is, on or off.

## How it works

`ha-tray.py` is one Python file. Every 3 seconds it asks Docker
(`docker inspect -f '{{.State.Running}}' homeassistant`) and, when the container runs, whether
http://localhost:8123 answers. The menu runs `docker start homeassistant` and
`docker stop --timeout 30 homeassistant`.

The icon uses the classic system tray (GTK's `StatusIcon`), which the XFCE panel's Status Tray
supports out of the box. That is deprecated in GTK but still works on X11, and it avoids
installing anything. If the laptop ever moves to Wayland or GNOME, the tray would need the
AppIndicator library instead (`gir1.2-ayatanaappindicator3-0.1`).

## Icon credits

The logo is the `home-assistant` icon from [Material Design Icons](https://pictogrammers.com/library/mdi/)
by Pictogrammers (glyph codepoint F07D0, taken from
[Templarian/MaterialDesign](https://github.com/Templarian/MaterialDesign) at commit `2424e74`).
The icons are released under the
[Pictogrammers Free License](https://github.com/Templarian/MaterialDesign/blob/master/LICENSE),
which puts icons under the Apache License 2.0 (a copy is in `icons/LICENSE-MaterialDesignIcons.txt`). `ha-on.svg` and `ha-starting.svg` use the glyph's path
unchanged, filled white with a black circuit so they match the panel's white, colourless icons
(Home Assistant's own blue, #18BCF2 in the official logo in
[home-assistant/assets](https://github.com/home-assistant/assets), is not used);
`ha-off.svg` and `ha-error.svg` are a simplified outline traced from it for this project.

Material Design Icons marks this glyph as a brand logo and as deprecated (brand icons may be
removed from its library in a later release). The Home Assistant logo belongs to the Home
Assistant project; it is used here only to label a private tool on your own laptop.
