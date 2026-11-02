"""Discovery of DualShock 4 controllers through sysfs.

Controllers are found by walking the HID devices the kernel exposes, so it
does not matter which USB port (or hub) they are plugged into, nor whether
they are connected over USB or Bluetooth. The lightbar LEDs and the battery
are tied to their controller through the ``device`` symlink the kernel
creates, never through names like ``input8`` that change between connections.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

SONY_VENDOR_ID = 0x054C
DS4_PRODUCT_IDS = {
    0x05C4: "DualShock 4 (v1)",
    0x09CC: "DualShock 4 (v2)",
    0x0BA0: "DualShock 4 USB Wireless Adapter",
}
# Drivers that expose the lightbar and battery of a DualShock 4.
PLAYSTATION_DRIVERS = {"playstation", "sony"}

_BUS_NAMES = {0x0003: "usb", 0x0005: "bluetooth"}
_LIGHTBAR_CHANNELS = ("red", "green", "blue")
# Kernel names of USB devices: "2-6" (root hub port), "2-6.2" (behind a hub).
_USB_DEVICE_NAME = re.compile(r"^\d+-\d+(\.\d+)*$")


@dataclass(frozen=True)
class Lightbar:
    red: Path
    green: Path
    blue: Path


@dataclass(frozen=True)
class Controller:
    sysfs_path: Path
    hid_id: str
    name: str
    vendor_id: int
    product_id: int
    bus: str
    mac: str | None
    driver: str | None
    # Kernel name of the USB device, e.g. "2-6.2"; None over Bluetooth.
    usb_port: str | None
    # None when the kernel driver does not expose the lightbar.
    lightbar: Lightbar | None
    # Path of the power_supply entry; None when the kernel does not expose one.
    battery_path: Path | None

    @property
    def model(self) -> str:
        return DS4_PRODUCT_IDS.get(self.product_id, self.name)


def _read_uevent(path: Path) -> dict[str, str]:
    values = {}
    for line in (path / "uevent").read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    return values


def _is_ds4(vendor_id: int, product_id: int, name: str, driver: str | None) -> bool:
    if vendor_id == SONY_VENDOR_ID and product_id in DS4_PRODUCT_IDS:
        return True
    # Third-party controllers with their own IDs that the kernel handles as DS4.
    lowered = name.lower()
    return (
        driver in PLAYSTATION_DRIVERS
        and "wireless controller" in lowered
        and "dualsense" not in lowered
    )


def _driver_name(path: Path) -> str | None:
    try:
        return os.path.basename(os.readlink(path / "driver"))
    except OSError:
        return None


def _usb_port(real_path: str) -> str | None:
    for part in reversed(Path(real_path).parts):
        if _USB_DEVICE_NAME.match(part):
            return part
    return None


def _find_lightbar(path: Path) -> Lightbar | None:
    try:
        entries = list((path / "leds").iterdir())
    except OSError:
        return None
    channels = {entry.name.rsplit(":", 1)[-1]: entry / "brightness" for entry in entries}
    if all(channel in channels for channel in _LIGHTBAR_CHANNELS):
        return Lightbar(**{channel: channels[channel] for channel in _LIGHTBAR_CHANNELS})
    return None


def _find_battery(real_path: str, power_supply_dir: Path) -> Path | None:
    try:
        entries = sorted(power_supply_dir.iterdir())
    except OSError:
        return None
    for entry in entries:
        if (entry / "capacity").exists() and os.path.realpath(entry / "device") == real_path:
            return entry
    return None


def _describe(path: Path, power_supply_dir: Path) -> Controller | None:
    uevent = _read_uevent(path)
    bus, vendor_id, product_id = (int(part, 16) for part in uevent["HID_ID"].split(":"))
    name = uevent.get("HID_NAME", "")
    driver = _driver_name(path)
    if not _is_ds4(vendor_id, product_id, name, driver):
        return None
    real_path = os.path.realpath(path)
    return Controller(
        sysfs_path=Path(real_path),
        hid_id=path.name,
        name=name,
        vendor_id=vendor_id,
        product_id=product_id,
        bus=_BUS_NAMES.get(bus, "other"),
        mac=uevent.get("HID_UNIQ") or None,
        driver=driver,
        usb_port=_usb_port(real_path) if _BUS_NAMES.get(bus) == "usb" else None,
        lightbar=_find_lightbar(path),
        battery_path=_find_battery(real_path, power_supply_dir),
    )


def find_controllers(sysfs_root: Path = Path("/sys")) -> list[Controller]:
    """Return every DualShock 4 currently connected, on any port or bus."""
    try:
        devices = sorted((sysfs_root / "bus/hid/devices").iterdir())
    except OSError:
        return []
    power_supply_dir = sysfs_root / "class/power_supply"
    controllers = []
    for path in devices:
        try:
            controller = _describe(path, power_supply_dir)
        except (OSError, KeyError, ValueError):
            # Unplugged mid-scan, or not a regular HID device: skip it.
            continue
        if controller is not None:
            controllers.append(controller)
    return controllers
