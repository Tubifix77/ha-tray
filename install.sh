#!/bin/sh
# Install ha-tray for the current user: copy it to ~/.local/share/ha-tray, start it at
# login (XDG autostart) and put it in the application menu. Run it again to update.
set -eu

src=$(cd "$(dirname "$0")" && pwd)
dest="$HOME/.local/share/ha-tray"
autostart="$HOME/.config/autostart/ha-tray.desktop"
menu="$HOME/.local/share/applications/ha-tray.desktop"

# What the tray needs. Nothing is installed by this script.
missing=""
command -v docker >/dev/null 2>&1 || missing="$missing docker"
python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' \
    >/dev/null 2>&1 || missing="$missing python3-gi gir1.2-gtk-3.0"
if [ -n "$missing" ]; then
    echo "ha-tray needs:$missing" >&2
    exit 1
fi
docker info >/dev/null 2>&1 || echo "warning: this user cannot reach Docker right now; the icon will show the error mark" >&2

mkdir -p "$dest/icons" "$(dirname "$autostart")" "$(dirname "$menu")"
install -m 755 "$src/ha-tray.py" "$dest/ha-tray.py"
install -m 644 "$src"/icons/*.svg "$dest/icons/"

write_desktop() {
    cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Name=Home Assistant tray
Comment=Turn Home Assistant on or off from the panel
Exec=$dest/ha-tray.py
Icon=$dest/icons/ha-on.svg
Terminal=false
Categories=Utility;
StartupNotify=false
EOF
}
write_desktop "$menu"
write_desktop "$autostart"
echo "X-GNOME-Autostart-enabled=true" >> "$autostart"

echo "Installed in $dest"
echo "It starts by itself at your next login. To start it now: $dest/ha-tray.py &"
