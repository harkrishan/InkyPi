#!/bin/bash
# Additive installer: leaves upstream's venv, display arguments and config intact.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FAST_BOOT=false
UPDATE=false
for arg in "$@"; do
    case "$arg" in
        --fast-boot) FAST_BOOT=true ;;
        --update) UPDATE=true ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done
command -v nmcli >/dev/null || { echo 'NetworkManager is required (Raspberry Pi OS Bookworm or later).' >&2; exit 1; }
systemctl is-active --quiet NetworkManager || { echo 'NetworkManager must be running.' >&2; exit 1; }
[[ -f /usr/local/inkypi/src/config/device.json ]] || { echo 'Install InkyPi first.' >&2; exit 1; }
/usr/local/inkypi/venv_inkypi/bin/python -c 'import flask, waitress'
# Reuse the existing profile and password on upgrades; never delete saved networks.
if ! nmcli connection show id inkypi-hotspot >/dev/null 2>&1; then
    nmcli connection add type wifi ifname wlan0 con-name inkypi-hotspot ssid InkyPi-Setup \
        802-11-wireless.mode ap 802-11-wireless.band bg \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk inkypi123 \
        ipv4.method shared ipv4.addresses 192.168.4.1/24 ipv6.method disabled \
        connection.autoconnect no
else
    nmcli connection modify id inkypi-hotspot connection.autoconnect no
fi
install -m 755 "$HERE"/inkypi-*.sh "$HERE"/inkypi-*.py /usr/local/sbin/
install -m 644 "$HERE"/systemd/* /etc/systemd/system/
systemctl daemon-reload
# Explicitly started only after the setup image completes; never enabled at boot.
systemctl disable inkypi-wifi-setup.service
systemctl enable inkypi-wifi-fallback.timer
if $UPDATE; then
    if systemctl is-active --quiet inkypi-wifi-setup.service; then
        systemctl restart inkypi-wifi-setup.service
    fi
else
    systemctl stop inkypi.service
    python3 /usr/local/sbin/inkypi-wifi-state.py normal
fi
if $FAST_BOOT; then
    mkdir -p /var/lib/inkypi-wifi
    for unit in NetworkManager-wait-online.service ModemManager.service bluetooth.service hciuart.service; do
        state=$(systemctl is-enabled "$unit" 2>/dev/null || true)
        case "$state" in
            enabled|enabled-runtime)
                # Save original state once, so repeated installation remains reversible.
                [[ -f "/var/lib/inkypi-wifi/$unit" ]] || printf '%s\n' "$state" > "/var/lib/inkypi-wifi/$unit"
                systemctl disable "$unit"
                ;;
        esac
    done
fi
echo 'Wi-Fi fallback installed. Reboot to activate the boot timer. Setup: InkyPi-Setup / http://192.168.4.1'
