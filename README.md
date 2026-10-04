# InkyPi — Wi-Fi Setup Edition

<img src="./docs/images/inky_clock.jpg" />


## About InkyPi 
InkyPi is an open-source, customizable E-Ink display powered by a Raspberry Pi. Designed for simplicity and flexibility, it allows you to effortlessly display the content you care about, with a simple web interface that makes setup and configuration effortless.

**Features**:
- Natural paper-like aethetic: crisp, minimalist visuals that are easy on the eyes, with no glare or backlight
- Web Interface allows you to update and configure the display from any device on your network
- Minimize distractions: no LEDS, noise, or notifications, just the content you care about
- Easy installation and configuration, perfect for beginners and makers alike
- Open source project allowing you to modify, customize, and create your own plugins
- Set up scheduled playlists to display different plugins at designated times

**Plugins**:

- Image Upload: Upload and display any image from your browser
- Daily Newspaper/Comic: Show daily comics and front pages of major newspapers from around the world
- Clock: Customizable clock faces for displaying time
- AI Image/Text: Generate images and dynamic text from prompts using OpenAI's models
- Weather: Display current weather conditions and multi-day forecasts with a customizable layout
- Calendar: Visualize your calendar from Google, Outlook, or Apple Calendar with customizable layouts

And additional plugins coming soon! For documentation on building custom plugins, see [Building InkyPi Plugins](./docs/building_plugins.md).

See [the wiki](https://github.com/fatihak/InkyPi/wiki) for a list of community-maintained third-party plugins.

## What this fork adds

This is [harkrishan's fork](https://github.com/harkrishan/InkyPi) of
[fatihak/InkyPi](https://github.com/fatihak/InkyPi). It keeps the original display,
plugins, playlists and installation flow, and adds a way to recover Wi-Fi without
editing files on the SD card.

When your Pi cannot join a saved Wi-Fi network at boot, it creates its own setup
network and shows connection instructions on the e-paper screen. Join that
network from your phone or computer, choose your home Wi-Fi, and enter its
password. InkyPi then returns to its normal display.

The additions include:

- A Wi-Fi setup page with network scanning, a show/hide password button and saved-network deletion.
- Setup instructions on the display, with time for slow colour panels to finish refreshing.
- A handoff back to the normal setup screen or the active playlist after Wi-Fi connects.
- Installation and update helpers that reuse existing Wi-Fi profiles.
- Automatic use of your Pi's hostname and installation location; no `pi` username or personal hostname is required.
- The exported Waveshare `epd7in3f` driver and the working `pi-heif==0.14.0` dependency pin.
- Optional fast boot, disabled by default.

## Guide

- [Hardware](#hardware)
- [Installation](#installation)
- [Using Wi-Fi setup](#using-wi-fi-setup)
- [Optional fast boot](#optional-fast-boot)
- [Update](#update)
- [Troubleshooting Wi-Fi setup](#troubleshooting-wi-fi-setup)
- [Uninstall](#uninstall)
- [Waveshare display support](#waveshare-display-support)
- [Technical notes and hardware checklist](./docs/wifi-setup.md)

## Hardware 
- Raspberry Pi (4 | 3 | Zero 2 W)
    - Recommended to get 40 pin Pre Soldered Header
- MicroSD Card (min 8 GB)
- E-Ink Display:
    - Inky Impression by Pimoroni
        - **13.3 Inch Display**
        - **7.3 Inch Display**
        - **5.7 Inch Display**
        - **4 Inch Display**
    - Inky wHAT by Pimoroni
        - **4.2 Inch Display**
    - Waveshare e-Paper Displays
        - Spectra 6 (E6) Full Color **[4 inch](https://www.waveshare.com/4inch-e-paper-hat-plus-e.htm)** **[7.3 inch](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-plus-e.htm)**
        - Black and White **[7.5 inch](https://www.waveshare.com/7.5inch-e-paper-hat.htm)** **[13.3 inch](https://www.waveshare.com/13.3inch-e-paper-hat-k.htm)**
        - See [Waveshare e-paper displays](https://www.waveshare.com/product/raspberry-pi/displays/e-paper.htm) for additional models. Note that some models like the IT8951 based displays are not supported. See later section on [Waveshare e-Paper](#waveshare-display-support) compatibility for more information.
- Picture Frame or 3D Stand
    - See [community.md](./docs/community.md) for 3D models, custom builds, and other submissions from the community

## Installation

### Before you start

Use a Raspberry Pi with a supported display and Raspberry Pi OS Bookworm or
later. The Wi-Fi helper expects NetworkManager to manage the built-in wireless
interface named `wlan0`. Set your Wi-Fi country in Raspberry Pi OS and give the Pi
internet access for downloading installation dependencies. The fallback portal
becomes available after installation; it cannot replace that initial connection.

A fresh SD card is recommended. If you are changing an existing installation,
back up its configuration first and use the update instructions below where
appropriate. Keep the checkout in a permanent location: InkyPi runs its source
files from that directory through an installation link.

### 1. Download this fork

```bash
git clone --branch main https://github.com/harkrishan/InkyPi.git
cd InkyPi
```

Use this fork's URL to get the Wi-Fi additions. The upstream repository's
installation guide remains useful for preparing Raspberry Pi OS, but its clone
command downloads the original project.

### 2. Install for your display

For a **Pimoroni Inky** display:

```bash
sudo bash install/install.sh
```

For the **Waveshare model `epd7in3f`**:

```bash
sudo bash install/install.sh -W epd7in3f
```

For another Waveshare display, replace `epd7in3f` with its matching driver name.
The original `-W` interface is preserved. Models that only appear in Waveshare's
separate-program folders can still use the full repository-relative driver path:

```bash
sudo bash install/install.sh -W E-paper_Separate_Program/3.6inch_e-Paper_E/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd3in6e.py
```

The installer enables the required SPI and I2C interfaces, installs the original
InkyPi dependencies and service, and adds the Wi-Fi setup scripts and services.
It uses the existing installation layout rather than assuming a home directory
such as `/home/pi`. Both dependency files pin `pi-heif` to `0.14.0`, the version
that worked on the exported Bookworm/ARM setup.

### 3. Reboot and open InkyPi

Accept the installer's reboot prompt, or reboot later with:

```bash
sudo reboot
```

If saved Wi-Fi connects, access InkyPi using your Pi's hostname followed by
`.local`, or its local IP address. For example, a Pi named `livingroom` can be
opened at `http://livingroom.local`. The hostname is read from your device.
If saved Wi-Fi does not connect, follow the setup instructions below.

For SD-card preparation and the original hardware instructions, see
[installation.md](./docs/installation.md).

## Using Wi-Fi setup

### Connect the Pi to Wi-Fi

1. Boot the Pi and allow time for Wi-Fi detection and the e-paper refresh.
2. If no saved Wi-Fi connects, the screen shows **Wi-Fi setup mode**.
3. On your phone or computer, join the network below. Your device may warn that
   it has no internet connection; stay connected while configuring the Pi.
4. Open the setup address manually in a browser.
5. Select your home Wi-Fi, enter its password and choose **Connect**.

| Setting | Default value |
| --- | --- |
| Setup network | `InkyPi-Setup` |
| Setup password | `inkypi123` |
| Setup page | `http://192.168.4.1` |

The setup page offers a password visibility button and a list of saved Wi-Fi
profiles with delete controls. Deleting a saved profile removes its saved
credentials. The setup hotspot itself cannot be deleted through the page.

### What happens after connecting?

The Pi switches from its setup hotspot to your Wi-Fi, closes the setup page's
service and resumes InkyPi. With an active playlist and previous-plugin metadata,
it requests that previous plugin immediately; otherwise the ordinary refresh
schedule applies. With no active playlist, it shows the normal InkyPi setup screen.

Your browser may disconnect before it receives the success page because the Pi
uses the same radio for its hotspot and your Wi-Fi. Join your home network again
and open InkyPi using its hostname or IP address. If the password was wrong or the
connection failed, the setup hotspot is restored: reconnect to it and try again.

### Behaviour to know

- The recovery check runs **once per boot**, after allowing saved networks time
  to connect. It does not continuously monitor the internet.
- A Wi-Fi connection without internet access still counts as connected.
- The page does not automatically redirect your browser; open `http://192.168.4.1` yourself.
- InkyPi finishes drawing the setup screen before the setup page takes over
  port 80. A slow colour panel can take more than a minute. If drawing has not
  completed after 180 seconds, the helper reports a failure and leaves InkyPi
  running instead of interrupting the refresh.
- The portal normally runs only in setup mode. The active-network deletion helper
  also waits for the setup image before handing over to the portal.
- The setup password is a public default. Anyone who joins that hotspot can
  manage its Wi-Fi settings. Keep the portal local and do not forward it through
  your router.

## Optional fast boot

For a dedicated display that does not need Bluetooth or a modem, add `--fast-boot`
to installation:

```bash
sudo bash install/install.sh -W epd7in3f --fast-boot
```

To apply it to an already installed device:

```bash
sudo bash install/wifi-setup/install-wifi-setup.sh --update --fast-boot
```

This disables enabled NetworkManager-wait-online, ModemManager, bluetooth and
hciuart services for future boots. It does not stop them during installation.
Bluetooth or modem features may be unavailable after reboot. Their original
enabled states are recorded once, and removing the Wi-Fi layer restores those
states. No such service changes are made without `--fast-boot`.

## Update

Run these commands from your existing checkout of **this fork**. Back up the
configuration first; the example creates a dated copy alongside it:

```bash
cd InkyPi
cp -a src/config "config-backup-$(date +%Y%m%d-%H%M%S)"
git switch main
git pull --ff-only origin main
sudo bash install/update.sh
```

If Git reports local changes or a conflict, keep those changes and resolve the
message before continuing. Do not use a hard reset to bypass it. An installation
cloned from the original upstream repository must be deliberately migrated to
this fork; pulling upstream alone will not add or maintain these customizations.

The updater reinstalls the Wi-Fi scripts and services, reuses the hotspot profile
and preserves its existing password and saved client networks. It does not replace
your application configuration. If the setup portal is active, it restarts that
portal without starting InkyPi over it. Reboot when the Wi-Fi layer is first added
through an update so its boot timer can run.

Users already on `feature/wifi-fallback-installer` can use the same commands to
switch to `main` after the merge. Use the updater for routine updates instead of
re-running the full installer.

## Troubleshooting Wi-Fi setup

| What you see | What to try |
| --- | --- |
| The setup network has no internet | Expected during setup. Stay connected and open `http://192.168.4.1`. |
| The browser disconnects after pressing Connect | Join your home Wi-Fi and check InkyPi. If the setup hotspot reappears, reconnect and retry. |
| The hotspot appears but the page is not ready | Allow the display refresh to finish. If it remains unavailable, inspect the logs below. |
| No hotspot appears | Confirm NetworkManager manages `wlan0`, the Wi-Fi country is set, and the device has rebooted since installation. A connected saved network prevents fallback. |
| The hostname address does not work | Use the Pi's IP address from your router or the normal setup screen. |
| Wi-Fi drops long after boot | The check is not continuous. Reboot, or trigger the recovery check below from a terminal you can still access. |

Request another recovery check:

```bash
sudo systemctl start inkypi-wifi-fallback.service
```

Read the relevant service logs:

```bash
journalctl -u inkypi -u inkypi-wifi-fallback -u inkypi-wifi-setup --no-pager -n 100
```

The recovery check will leave a connected saved Wi-Fi network alone; it is not a
command to force setup mode while that connection is working. For general display
or installation issues, see the [troubleshooting guide](./docs/troubleshooting.md).
The [Wi-Fi technical guide](./docs/wifi-setup.md) includes service details,
automated test commands and a hardware validation checklist.

## Uninstall

To remove **only the Wi-Fi additions**, keeping InkyPi and saved client networks:

```bash
sudo bash install/wifi-setup/uninstall-wifi-setup.sh
sudo systemctl start inkypi.service
```

This removes the setup hotspot and its services, and restores recorded fast-boot
service states. Reboot to let restored services start normally.

To remove **InkyPi and the Wi-Fi additions**:

```bash
sudo bash install/uninstall.sh
```

The full uninstaller asks for confirmation and retains the original behaviour of
removing application configuration. Back up anything you want to keep first.

## Roadmap
The InkyPi project is constantly evolving, with many exciting features and improvements planned for the future.

- Plugins, plugins, plugins
- Modular layouts to mix and match plugins
- Support for buttons with customizable action bindings
- Improved Web UI on mobile devices

Check out the public [trello board](https://trello.com/b/SWJYWqe4/inkypi) to explore upcoming features and vote on what you'd like to see next!

## Waveshare Display Support

Waveshare offers a range of e-Paper displays, similar to the Inky screens from Pimoroni, but with slightly different requirements. While Inky displays auto-configure via the inky Python library, Waveshare displays require model-specific drivers from their [Python EPD library](https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd).

The upstream project reports testing with several Waveshare models. **Displays based on the IT8951 controller are not supported**, and **screens smaller than 4 inches are not recommended** due to limited resolution.

If your display model has a corresponding driver in the link above, it’s likely to be compatible. When running the installation script, use the -W option to specify your display model (without the .py extension). The script will automatically fetch and install the correct driver.

## License

Distributed under the GPL 3.0 License, see [LICENSE](./LICENSE) for more information.

This project includes fonts and icons with separate licensing and attribution requirements. See [Attribution](./docs/attribution.md) for details.

## Issues

Check out the [troubleshooting guide](./docs/troubleshooting.md). If you're still having trouble, report fork-specific Wi-Fi or installer problems on [this fork's issues page](https://github.com/harkrishan/InkyPi/issues).

If you're using a Pi Zero W, note that there are known issues during the installation process. See [Known Issues during Pi Zero W Installation](./docs/troubleshooting.md#known-issues-during-pi-zero-w-installation) section in the troubleshooting guide for additional details..

## Acknowledgements

Check out these similar projects:

- [PaperPi](https://github.com/txoof/PaperPi) - awesome project that supports waveshare devices
    - shoutout to @txoof for assisting with InkyPi's installation process
- [InkyCal](https://github.com/aceinnolab/Inkycal) - has modular plugins for building custom dashboards
- [PiInk](https://github.com/tlstommy/PiInk) - inspiration behind InkyPi's flask web ui
- [rpi_weather_display](https://github.com/sjnims/rpi_weather_display) - alternative eink weather dashboard with advanced power efficiency
