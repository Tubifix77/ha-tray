# ha-tray

A system-tray icon for Linux desktops that turns a [Home Assistant](https://www.home-assistant.io/)
container on and off, the way the OneDrive icon does on Windows. It starts when you log in, shows
at a glance whether Home Assistant is running, and switches it from a small menu.

It is made for a home server or laptop that runs Home Assistant in [Docker](https://docs.docker.com/)
(for example with [Docker Compose](https://docs.docker.com/compose/)) and that you sometimes want
to free from Home Assistant's memory use without opening a terminal.

## What the icon means

| icon | state |
|---|---|
| ![on](docs/ha-on.png) | **On**: filled white house with a black circuit. The container runs and Home Assistant's page answers |
| ![starting](docs/ha-starting.png) | **Starting or stopping**: the same icon, dimmed. The container runs but the page does not answer yet (about 5 seconds on the test machine) |
| ![off](docs/ha-off.png) | **Off**: white outline. The container is stopped |
| ![error](docs/ha-error.png) | **Error**: outline with a red mark. Docker cannot be reached, or there is no container with that name. Hover over the icon to see which |

The icon checks the real state every 3 seconds, so it is also right when Home Assistant was
started or stopped some other way, for example with `docker compose up -d`.

The icons are white so they match a panel of white, colourless icons. The outline has a soft
dark edge so it can also be seen on a light panel.

## The menu

Click the icon (left or right button):

- **Running / Stopped / Starting... / Docker unavailable**: the current state.
- **Turn Home Assistant on** / **Turn Home Assistant off**: switches it. Greyed out while a switch
  is in progress. Turning off gives Home Assistant up to 30 seconds to shut down cleanly before
  Docker stops it by force.
- **Open Home Assistant**: opens the page in your default browser. Only while it is on.
- **Quit tray**: closes the icon and leaves Home Assistant as it is.

If a switch fails, Docker's error message appears greyed out under the state line.

## Requirements

- Linux with an X11 desktop whose panel has a classic system tray
  ([XEmbed](https://specifications.freedesktop.org/systemtray-spec/latest/)). Tested on
  [XFCE](https://www.xfce.org/) 4.18 (Debian 12); other X11 panels with a classic tray should
  work but have not been tried. **GNOME and Wayland sessions are not supported** (see below).
- Python 3 with the GTK 3 bindings: on Debian or Ubuntu the packages `python3-gi` and
  `gir1.2-gtk-3.0`. Tested with Python 3.11, PyGObject 3.42, GTK 3.24.
- Docker, usable by your user without `sudo` (your user is in the `docker` group).
- Home Assistant running in a Docker container. The default container name is `homeassistant`,
  as in [Home Assistant's Docker instructions](https://www.home-assistant.io/installation/linux),
  and the default page is http://localhost:8123/.

## Install

```sh
git clone https://github.com/Tubifix77/ha-tray.git
cd ha-tray
sh install.sh
```

This copies the program to `~/.local/share/ha-tray/`, adds **Home Assistant tray** to the
application menu, and makes it start at login (`~/.config/autostart/ha-tray.desktop`). It does
not install any packages; it tells you if one is missing. To start it right away without logging
out:

```sh
~/.local/share/ha-tray/ha-tray.py &
```

If your container or page is different, pass that to the installer. It is then used at every start:

```sh
sh install.sh --container my-home-assistant --url http://localhost:8123/
```

Running `install.sh` again updates the installed copy. Only one copy runs at a time; a second
start just exits.

## Uninstall

```sh
sh uninstall.sh
```

This stops the icon and removes what `install.sh` wrote. Home Assistant stays as it is, on or off.

## What it does and does not do

- It runs `docker start <container>` and `docker stop --timeout 30 <container>` on that one
  container and nothing else. Other containers, such as an MQTT broker in the same Compose
  file, keep running.
- It stores no state of its own. **Whether your choice survives a reboot depends on the
  container's [restart policy](https://docs.docker.com/engine/containers/start-containers-automatically/)**,
  which ha-tray never changes:
  - `restart: unless-stopped`: a Home Assistant you turned off stays off after a reboot, and one
    you left on comes back on. On the test machine, Docker recorded "manually stopped" in the
    container's saved state when it was turned off, and cleared it when it was turned on. A
    reboot with Home Assistant off has not been tried.
  - `restart: always`: Docker starts it again when Docker itself restarts (for example at boot),
    even if you turned it off.
  - `restart: no` (the default): it stays off after a reboot, and does not come back on by itself
    either.
- `docker compose up -d` starts every service in the Compose file, so it turns Home Assistant on
  again. The icon follows.
- It does not use Home Assistant's API, needs no token, and does not read Home Assistant's
  configuration. "On" means the container runs and the page gives any HTTP answer at all.

## How it works

`ha-tray.py` is one Python file. Every 3 seconds it runs
`docker inspect -f '{{.State.Running}}' <container>` in a background thread and, when the
container runs, checks whether the page answers. Docker's error text separates "Docker
unavailable" from "no such container".

The icon uses GTK's `Gtk.StatusIcon`, the classic XEmbed tray icon. GTK 3 marks it as
deprecated, but it works on X11 panels without installing anything extra. GNOME's top bar has no
tray, and Wayland has no XEmbed, so supporting those would mean moving to the
[StatusNotifierItem / AppIndicator](https://specifications.freedesktop.org/status-notifier-item/latest/)
protocol (on Debian, the `gir1.2-ayatanaappindicator3-0.1` package). That has not been done.

The tray prints its state changes to standard output. When it is started at login, those lines
usually end up in `~/.xsession-errors`. To watch them, quit the tray from its menu and start it
from a terminal.

## Licence

The code is under the [MIT License](LICENSE).

The icons in `icons/` are not. They come from the `home-assistant` icon in
[Material Design Icons](https://pictogrammers.com/library/mdi/) by Pictogrammers (codepoint
F07D0, from [Templarian/MaterialDesign](https://github.com/Templarian/MaterialDesign) at commit
`2424e74`). The icons there are released under the
[Pictogrammers Free License](https://github.com/Templarian/MaterialDesign/blob/master/LICENSE),
which places them under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0); a
copy is in [`icons/LICENSE-MaterialDesignIcons.txt`](icons/LICENSE-MaterialDesignIcons.txt).
`ha-on.svg` and `ha-starting.svg` use the icon's outline unchanged, recoloured white with a black
circuit. `ha-off.svg` and `ha-error.svg` are a simplified outline traced from it for this project.
The same terms apply to the previews in `docs/`.

Material Design Icons marks this icon as a brand logo and as deprecated, so it may be removed
from their library in a later release. The Home Assistant name and logo belong to the Home
Assistant project. ha-tray is not affiliated with or endorsed by the Home Assistant project.
