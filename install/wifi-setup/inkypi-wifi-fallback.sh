#!/bin/bash
set -euo pipefail
exec 9>/run/inkypi-wifi-transition.lock
flock -n 9 || exit 0
# Allow the radio and saved profiles to settle after boot.
for ((i=0; i<38; i++)); do
    active=$(nmcli -g GENERAL.CONNECTION device show wlan0 2>/dev/null || true)
    state=$(nmcli -g GENERAL.STATE device show wlan0 2>/dev/null || true)
    if [[ "$state" == 100* && "$active" != inkypi-hotspot ]]; then
        if [[ -f /var/lib/inkypi-wifi/setup-active ]]; then
            flock -u 9
            exec bash /usr/local/sbin/inkypi-wifi-connected.sh
        fi
        exit 0
    fi
    sleep 1
done
# Do not restart a working portal on repeated invocations.
if [[ "$active" == inkypi-hotspot ]] && systemctl is-active --quiet inkypi-wifi-setup.service; then
    exit 0
fi
nmcli connection up id inkypi-hotspot
bash /usr/local/sbin/inkypi-wifi-show-setup.sh
