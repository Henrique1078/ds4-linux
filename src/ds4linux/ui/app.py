"""GTK application entry point."""

from __future__ import annotations

from gi.repository import Adw

from ds4linux.ui.window import MainWindow


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="io.github.henrique1078.ds4linux")

    def do_activate(self) -> None:
        window = self.props.active_window or MainWindow(self)
        window.present()


def run(argv: list[str] | None = None) -> int:
    return Application().run(argv)
