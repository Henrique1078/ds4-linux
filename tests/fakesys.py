"""Builds a fake sysfs tree that mirrors the layout the kernel exposes."""

from __future__ import annotations

import os
from pathlib import Path

BUS_USB = 0x0003
BUS_BLUETOOTH = 0x0005


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def add_hid_device(
    root: Path,
    parents: str,
    *,
    vendor: int = 0x054C,
    product: int = 0x09CC,
    name: str = "Sony Interactive Entertainment Wireless Controller",
    driver: str | None = "playstation",
    bus: int = BUS_USB,
    mac: str = "a0:5a:5d:54:95:26",
    index: int = 1,
    leds: str | None = "input8",
    battery: tuple[str, int] | None = ("Full", 100),
) -> Path:
    """Create a HID device under ``parents`` and link it into bus/hid/devices.

    ``parents`` is the device path below ``devices/``, e.g.
    ``"pci0000:00/usb2/2-6/2-6.2/2-6.2:1.3"``.
    """
    hid_id = f"{bus:04X}:{vendor:04X}:{product:04X}.{index:04X}"
    device = root / "devices" / parents / hid_id
    _write(
        device / "uevent",
        f"HID_ID={bus:04X}:{vendor:08X}:{product:08X}\n"
        f"HID_NAME={name}\nHID_UNIQ={mac}\n",
    )
    if driver is not None:
        drivers = root / "bus/hid/drivers" / driver
        drivers.mkdir(parents=True, exist_ok=True)
        os.symlink(drivers, device / "driver")
    if leds is not None:
        for channel in ("red", "green", "blue", "global"):
            _write(device / "leds" / f"{leds}:{channel}" / "brightness", "0\n")
    if battery is not None:
        supply = root / "class/power_supply" / f"ps-controller-battery-{mac}"
        _write(supply / "status", f"{battery[0]}\n")
        _write(supply / "capacity", f"{battery[1]}\n")
        os.symlink(device, supply / "device")
    link = root / "bus/hid/devices" / hid_id
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(device, link)
    return device
