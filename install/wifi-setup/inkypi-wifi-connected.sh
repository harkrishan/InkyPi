#!/bin/bash
set -euo pipefail
exec 9>/run/inkypi-wifi-transition.lock
flock -w 200 9

CONFIG="/usr/local/inkypi/src/config/device.json"

# Stop the Wi-Fi setup portal so port 80 becomes free.
systemctl stop inkypi-wifi-setup.service inkypi.service

# Make sure the fallback hotspot is no longer active.
nmcli connection down inkypi-hotspot >/dev/null 2>&1 || true

# Set the startup choice before the application reads its configuration.
python3 /usr/local/sbin/inkypi-wifi-state.py normal

rm -f /var/lib/inkypi-wifi/setup-active

# Start normal InkyPi.
systemctl start inkypi.service

# Wait for the InkyPi web server to become ready.
for i in $(seq 1 30); do
    if curl -s --max-time 1 http://127.0.0.1/ >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Read the active playlist and the plugin that was last displayed.
readarray -t DISPLAY_INFO < <(
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/usr/local/inkypi/src/config/device.json").read_text())

playlist = data.get("playlist_config", {}).get("active_playlist")
refresh = data.get("refresh_info", {})

plugin_id = refresh.get("plugin_id")
plugin_instance = refresh.get("plugin_instance")

print(playlist or "")
print(plugin_id or "")
print(plugin_instance or "")
PY
)

PLAYLIST_NAME="${DISPLAY_INFO[0]}"
PLUGIN_ID="${DISPLAY_INFO[1]}"
PLUGIN_INSTANCE="${DISPLAY_INFO[2]}"

# Immediately restore the selected playlist screen.
if [ -n "$PLAYLIST_NAME" ] && [ -n "$PLUGIN_ID" ] && [ -n "$PLUGIN_INSTANCE" ]; then
    curl -s --max-time 10 \
        -X POST http://127.0.0.1/display_plugin_instance \
        -H 'Content-Type: application/json' \
        -d "$(python3 - "$PLAYLIST_NAME" "$PLUGIN_ID" "$PLUGIN_INSTANCE" <<'PYJSON'
import json, sys
print(json.dumps(dict(zip(("playlist_name", "plugin_id", "plugin_instance"), sys.argv[1:]))))
PYJSON
)" >/dev/null 2>&1
fi
