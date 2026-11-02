"""Battery state of a controller, read from its power_supply sysfs entry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Battery:
    # None while the kernel has not reported a level yet.
    capacity: int | None
    # Kernel status: "Charging", "Discharging", "Full", "Not charging" or "Unknown".
    status: str

    @property
    def charging(self) -> bool:
        return self.status == "Charging"


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        # The entry disappears when the controller is unplugged mid-read.
        return None


def read_battery(power_supply: Path) -> Battery | None:
    """Return the battery state, or None if the entry is gone."""
    status = _read(power_supply / "status")
    raw_capacity = _read(power_supply / "capacity")
    if status is None and raw_capacity is None:
        return None
    try:
        capacity = max(0, min(100, int(raw_capacity))) if raw_capacity else None
    except ValueError:
        capacity = None
    return Battery(capacity=capacity, status=status or "Unknown")
