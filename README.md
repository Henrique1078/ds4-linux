# DS4 Linux

A graphical app to configure the **DualShock 4** controller on Linux, inspired by DS4Windows.

> **Status: pre-alpha.** Controller discovery and battery reading work from the command line. There is no graphical interface yet, and the lightbar cannot be changed yet.

## Planned features

First milestone:

- Detect the controller over USB and Bluetooth, with automatic reconnection.
- Change the lightbar color with a color wheel.
- Turn the lightbar off and restore the color afterwards.
- Show the battery level and charging state.
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

List the connected controllers, on any USB port or over Bluetooth:

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
