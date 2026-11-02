"""Per-controller settings saved in the user's config directory."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from ds4linux.lightbar import Color

DEFAULT_COLOR = Color(0, 0, 64)


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ds4-linux" / "config.json"


@dataclass(frozen=True)
class LightbarSettings:
    color: Color = DEFAULT_COLOR
    enabled: bool = True


class Config:
    """Settings keyed by controller MAC address."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()
        self._lightbars: dict[str, LightbarSettings] = {}
        self._load()

    def lightbar(self, controller_id: str) -> LightbarSettings:
        return self._lightbars.get(controller_id, LightbarSettings())

    def set_lightbar(self, controller_id: str, settings: LightbarSettings) -> None:
        self._lightbars[controller_id] = settings
        self._save()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
            entries = data["lightbars"].items()
        except (OSError, ValueError, KeyError, AttributeError):
            # Missing or corrupt file: start from defaults.
            return
        for controller_id, entry in entries:
            try:
                self._lightbars[controller_id] = LightbarSettings(
                    color=Color.from_hex(entry["color"]),
                    enabled=bool(entry["enabled"]),
                )
            except (KeyError, ValueError, TypeError):
                continue

    def _save(self) -> None:
        data = {
            "lightbars": {
                controller_id: {"color": settings.color.to_hex(), "enabled": settings.enabled}
                for controller_id, settings in self._lightbars.items()
            }
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file first so a crash never leaves a half-written config.
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2))
        temporary.replace(self.path)
