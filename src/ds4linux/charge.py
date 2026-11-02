"""Detects the moment a controller finishes charging."""

from __future__ import annotations

from ds4linux.battery import Battery


class ChargeTracker:
    """Reports each controller that goes from Charging to Full.

    A controller that is already full when it is first seen, or that is
    unplugged while charging, is not reported.
    """

    def __init__(self) -> None:
        self._charging: set[str] = set()

    def update(self, controller_id: str, battery: Battery | None) -> bool:
        """Feed the latest reading. True once, when charging just finished."""
        if battery is None:
            # A failed read says nothing about the charge, so keep the state.
            return False
        if battery.charging:
            self._charging.add(controller_id)
            return False
        finished = battery.status == "Full" and controller_id in self._charging
        self._charging.discard(controller_id)
        return finished

    def forget(self, controller_id: str) -> None:
        """Drop the state of a controller that was disconnected."""
        self._charging.discard(controller_id)
