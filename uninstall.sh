#!/bin/sh
# Remove ha-tray: stop the running tray and delete what install.sh wrote.
# Home Assistant itself is not touched; it stays on or off as it is now.
set -eu

dest="$HOME/.local/share/ha-tray"

# Stop the tray by the pid of the process holding its script, never by a pattern match
# (a pattern would also match this shell's own command line).
for pid in $(pgrep -u "$(id -u)" || true); do
    [ "$pid" = "$$" ] && continue
    first_two=$({ tr '\0' '\n' < "/proc/$pid/cmdline"; } 2>/dev/null | head -n 2 || true)
    case "$first_two" in
        "$dest/ha-tray.py"|*"
$dest/ha-tray.py") kill "$pid" && echo "stopped the tray (pid $pid)" ;;
    esac
done

rm -f "$HOME/.config/autostart/ha-tray.desktop" "$HOME/.local/share/applications/ha-tray.desktop"
rm -rf "$dest"
echo "ha-tray removed. Home Assistant was left as it is."
