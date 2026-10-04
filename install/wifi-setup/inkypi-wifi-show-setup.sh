#!/bin/bash
set -euo pipefail
mkdir -p /var/lib/inkypi-wifi
touch /var/lib/inkypi-wifi/setup-active
systemctl stop inkypi-wifi-setup.service inkypi.service
python3 /usr/local/sbin/inkypi-wifi-state.py setup
systemctl start inkypi.service
# Slow colour panels can take over a minute. Do not kill an unfinished refresh.
for ((i=0; i<180; i++)); do
    if [ "$(python3 /usr/local/sbin/inkypi-wifi-state.py read)" = false ]; then
        systemctl stop inkypi.service
        systemctl start inkypi-wifi-setup.service
        exit 0
    fi
    sleep 1
done
echo "Setup display did not complete within 180s; leaving InkyPi running. See journalctl -u inkypi." >&2
exit 1
