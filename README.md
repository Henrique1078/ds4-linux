# DS4 Linux

A graphical app to configure the **DualShock 4** controller on Linux, inspired by DS4Windows.

> **Status: pre-alpha.** A graphical interface can change the lightbar color, turn it on and off, show the battery level and tell you when charging finishes. Everything else (charging mode, remapping, macros) is still planned.

## Planned features

First milestone:

- Detect the controller over USB and Bluetooth, with automatic reconnection.
- Change the lightbar color with a color wheel.
- Turn the lightbar off and restore the color afterwards.
- Show the battery level and charging state, and tell you when a controller finishes charging.
- Remember the last color and reapply it when the controller reconnects.

Later milestones: charging mode (controller powered but not configured by the PC, like the PS4 rest mode), button remapping, macros and profiles.

## How it works

The kernel's `hid_playstation` driver already exposes the controller's lightbar and battery through `sysfs`. This project uses that interface instead of reimplementing the HID protocol, which should behave the same over USB and Bluetooth (Bluetooth has not been tested yet).

The interface will be written in Python with GTK4 and libadwaita.

## Requirements

- Linux with the `hid_playstation` driver (recent kernel).
- Python 3.10 or newer.
- PyGObject, GTK4 and libadwaita. On Debian, Ubuntu and derivatives: `python3-gi`, `gir1.2-gtk-4.0` and `gir1.2-adw-1`.

## Usage

### Allow lightbar control (once)

The kernel only lets root change the lightbar. Install the udev rule from this repository so your user can change it, then reconnect the controller:

```bash
sudo install -m 644 data/70-ds4-linux.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=leds --action=add
```

The rule only makes the red, green and blue brightness files of DualShock 4 LEDs writable by every user on the machine, so anyone logged in can change the lightbar color. It matches Sony's vendor ID with the DualShock 4 product IDs, so controllers from other vendors are not covered yet.

### Open the app

```bash
PYTHONPATH=src python3 -m ds4linux
```

The app shows every connected controller, whichever USB port or Bluetooth link it uses. The color and on/off state are remembered per controller in `~/.config/ds4-linux/config.json` and are applied again when the controller reconnects while the app is open.

### About "off"

The lightbar switch does not send pure black. While a DualShock 4 is charging over USB, its firmware takes over a black lightbar and pulses orange (the charging animation). Turning the light off sets each channel to 1 instead, which does not trigger the animation.

- **Original Sony DualShock 4 (v2):** the light goes completely dark.
- **Third-party controllers:** some cannot be fully turned off while charging over USB. The lowest non-zero step of their LED is still visible, so a faint light stays on. Pure black is not an option either, because their firmware also shows the orange charging animation. This was seen on a DataFrog controller; there is no color that works around it.

Other models and Bluetooth have not been tested.

### List controllers

```bash
PYTHONPATH=src python3 -m ds4linux list
```

Add `--json` for machine-readable output.

## Development

Run the tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Contributing

Contributions are welcome: issues, testing with different controllers (original and third-party) and pull requests. Code, identifiers and documentation are written in English.

## License

[GPL-3.0-or-later](LICENSE).
