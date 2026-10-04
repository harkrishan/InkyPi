#!/bin/bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
systemctl disable --now inkypi-wifi-fallback.timer inkypi-wifi-setup.service || true
systemctl stop inkypi-wifi-fallback.service || true
nmcli connection delete id inkypi-hotspot || true
for name in inkypi-wifi-fallback.sh inkypi-wifi-connected.sh inkypi-delete-active-wifi.sh inkypi-wifi-show-setup.sh inkypi-wifi-state.py inkypi-wifi-setup.py; do
    rm -f "/usr/local/sbin/$name"
done
rm -f /etc/systemd/system/inkypi-wifi-{fallback.service,fallback.timer,setup.service}
for unit in NetworkManager-wait-online.service ModemManager.service bluetooth.service hciuart.service; do
    record="/var/lib/inkypi-wifi/$unit"
    if [[ -f "$record" ]]; then
        if [[ "$(cat "$record")" == enabled-runtime ]]; then
            systemctl enable --runtime "$unit"
        else
            systemctl enable "$unit"
        fi
        rm -f "$record"
    fi
done
rm -f /var/lib/inkypi-wifi/setup-active
systemctl daemon-reload
