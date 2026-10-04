#!/bin/bash
set -euo pipefail
PROFILE=${1:?A Wi-Fi profile is required}
[[ "$PROFILE" != inkypi-hotspot ]] || exit 1
[[ "$(nmcli -g connection.type connection show id "$PROFILE")" == 802-11-wireless ]] || exit 1
exec 9>/run/inkypi-wifi-transition.lock
flock -w 200 9
nmcli connection delete id "$PROFILE"
nmcli connection up id inkypi-hotspot
bash /usr/local/sbin/inkypi-wifi-show-setup.sh
