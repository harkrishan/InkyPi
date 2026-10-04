# Wi-Fi fallback and setup

This fork integrates `inkypi-custom-export.tar.gz`: the Flask portal (including
password visibility and saved-network deletion), connection handoff, fallback
units, startup image and exported Waveshare `epd7in3f` driver. The existing
installer remains the source of the interface, driver selection, OS setup,
virtual environment and application service. Its machine-specific exported
copy is deliberately not substituted for the upstream installer.

## Install

Use Raspberry Pi OS Bookworm or later with NetworkManager managing `wlan0`.
Configure the Wi-Fi country in Raspberry Pi OS first. Run from any user's checkout:

```sh
git clone --branch feature/wifi-fallback-installer https://github.com/harkrishan/InkyPi.git
cd InkyPi
sudo bash install/install.sh -W epd7in3f
```

Omit `-W` for Pimoroni Inky. Other upstream Waveshare model names and repository
relative driver paths remain supported. The included `epd7in3f` is the exported
working driver; the upstream download mechanism handles other models.

The runtime resolves configuration through upstream's `/usr/local/inkypi/src`
symlink. No username, home directory or device hostname is assumed. The hostname
on the ordinary setup screen comes from the running device. The access point
name/address are intentionally stable onboarding defaults, not device hostnames.

Both requirements files pin `pi-heif==0.14.0`, matching the version that worked
on the exported Pi's Bookworm/ARM installation. This does not claim compatibility
with every future Python/OS combination; validate fresh installs on your image.

## Use

After reboot, the boot timer waits for the radio and saved Wi-Fi connections.
If none connects, it activates `inkypi-hotspot`:

- SSID: **InkyPi-Setup**
- Password: **inkypi123**
- Setup page: **http://192.168.4.1**

Join it from a phone/computer and open that address manually. This is not a DNS
captive-portal redirect. The page is served only on the hotspot address, supports
saved-network deletion, and protects forms against cross-site requests. Anyone
with access to the setup hotspot can configure Wi-Fi; the default password is
public. Do not expose the portal through router forwarding.

The device renders the setup instructions before giving port 80 to the portal.
The startup flag is cleared by InkyPi only after `display_image()` returns.
A 180-second timeout reports failure without stopping an unfinished display
refresh. Inspect the application journal if the portal does not appear.

Successful Wi-Fi selection schedules a separate service to stop the portal and
resume InkyPi. The active playlist's previous plugin is requested immediately
when its metadata exists; otherwise the normal refresh schedule applies.
With no active playlist, InkyPi displays its normal setup instructions. Failed
connections reactivate the setup hotspot. Since a single radio cannot keep the
hotspot connected while joining another Wi-Fi network, the browser may lose its
connection before receiving the result: reconnect to the hotspot after a failure,
or join the home network after success.

The fallback timer runs once per boot, matching the exported behavior. It is not
a continuous internet monitor. A connected Wi-Fi network without internet access
counts as connected. To request recovery after a later disconnection:

```sh
sudo systemctl start inkypi-wifi-fallback.service
```

Active-network deletion hands control to a separate service and waits for the
setup image to complete. The portal normally runs only while the hotspot is up,
so ordinary saved-network deletion is the usual path through its UI.

## Update and uninstall

Back up `src/config` before updating. Stay on this fork's branch:

```sh
git pull --ff-only
sudo bash install/update.sh
```

The helper reinstalls scripts and units without duplicating or deleting saved
Wi-Fi profiles, changing the existing hotspot password, or replacing application
configuration. An active portal is restarted and the updater does not start
InkyPi over it. Reboot after first installing the fallback timer through an update.
Switching back to upstream alone will not maintain these customizations.

Remove only the Wi-Fi layer, preserving saved client networks and app config:

```sh
sudo bash install/wifi-setup/uninstall-wifi-setup.sh
sudo systemctl start inkypi.service
```

The upstream full `install/uninstall.sh` also removes this layer after its normal
confirmation, then retains its original behavior of deleting application config.

## Optional fast boot

```sh
sudo bash install/install.sh -W epd7in3f --fast-boot
# Or apply to an existing installation:
sudo bash install/wifi-setup/install-wifi-setup.sh --update --fast-boot
```

This disables enabled NetworkManager-wait-online, ModemManager, bluetooth and
hciuart services for subsequent boots. Bluetooth/modem functionality may be
unavailable after reboot. It does not stop them during installation or change
other upstream boot settings. Original enabled states are recorded once in
`/var/lib/inkypi-wifi`; uninstalling the Wi-Fi layer restores those states.
No fast-boot changes occur unless explicitly requested.

## Validation

Host-side tests (Flask required) do not invoke real network or service commands:

```sh
python -m unittest discover -s tests -p 'test_wifi_*.py' -v
bash -n install/install.sh
bash -n install/update.sh
bash -n install/uninstall.sh
for script in install/wifi-setup/*.sh; do bash -n "$script"; done
```

Before merging, test on a spare SD card and actual display:

1. Fresh install with `-W epd7in3f`, a different username/hostname and checkout path.
2. Boot with saved Wi-Fi; verify normal display with and without active playlist.
3. Boot without reachable saved Wi-Fi; verify the full setup image completes,
   hotspot works, and only the portal owns port 80.
4. Submit a wrong password; reconnect to the restored hotspot and retry correctly.
5. Verify normal setup screen or previous playlist returns after connection.
6. Delete a saved profile; exercise the active-deletion helper on a disposable
   test network and confirm the display completes before application shutdown.
7. Re-run install/update and verify profile counts, credentials and app config.
8. Reboot after setup mode with saved Wi-Fi now available; verify display recovery.
9. Test optional fast boot and uninstall restoration. Test another supported
   display before claiming broad display compatibility.

Logs: `journalctl -u inkypi -u inkypi-wifi-fallback -u inkypi-wifi-setup`.
Host tests cannot establish radio, DHCP, Raspberry Pi dependency or panel behavior.
