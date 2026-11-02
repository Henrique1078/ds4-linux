"""Main window: controller status, lightbar on/off and color."""

from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk

from ds4linux.battery import read_battery
from ds4linux.charge import ChargeTracker
from ds4linux.config import Config, LightbarSettings
from ds4linux.device import Controller, find_controllers
from ds4linux.lightbar import OFF, Color, avoid_black, can_write, set_color
from ds4linux.ui.color_wheel import ColorWheel

POLL_SECONDS = 2
# Dragging the wheel fires many events; write to the controller at ~30 Hz.
APPLY_DELAY_MS = 33
SAVE_DELAY_MS = 400

UDEV_INSTALL_COMMANDS = """\
sudo install -m 644 data/70-ds4-linux.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=leds --action=add"""


def _key(controller: Controller) -> str:
    return controller.mac or controller.hid_id


def _label(controller: Controller) -> str:
    where = controller.bus + (f" {controller.usb_port}" if controller.usb_port else "")
    return f"{controller.model} ({where})"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, config: Config | None = None) -> None:
        super().__init__(application=application, title="DS4 Linux")
        self.set_default_size(440, 840)
        self._config = config or Config()
        self._charge = ChargeTracker()
        self._controllers: dict[str, Controller] = {}
        self._keys: list[str] = []
        self._selected: str | None = None
        self._shown: str | None = None
        self._color = LightbarSettings().color
        self._enabled = True
        self._updating = False
        self._apply_source = 0
        self._save_source = 0
        self._build()
        self._refresh()
        GLib.timeout_add_seconds(POLL_SECONDS, self._on_poll)

    # Layout

    def _build(self) -> None:
        self._empty = Adw.StatusPage(
            icon_name="input-gaming-symbolic",
            title="No controller found",
            description="Connect a DualShock 4 with a USB cable or over Bluetooth.",
        )
        self._banner = Adw.Banner()
        self._banner.connect("button-clicked", self._on_banner_clicked)

        self._combo = Adw.ComboRow(title="Controller")
        self._combo.connect("notify::selected", self._on_combo_selected)
        self._battery_bar = Gtk.LevelBar(min_value=0, max_value=1, valign=Gtk.Align.CENTER)
        self._battery_bar.set_size_request(110, -1)
        self._battery_label = Gtk.Label(xalign=1, width_chars=14)
        self._battery_label.add_css_class("dim-label")
        battery_row = Adw.ActionRow(title="Battery")
        battery_row.add_suffix(self._battery_bar)
        battery_row.add_suffix(self._battery_label)
        controller_group = Adw.PreferencesGroup(title="Controller")
        controller_group.add(self._combo)
        controller_group.add(battery_row)

        self._switch = Adw.SwitchRow(title="Lightbar", subtitle="Turn the light on or off")
        self._switch.connect("notify::active", self._on_switch)
        self._wheel = ColorWheel()
        self._wheel.connect("changed", self._on_wheel_changed)
        self._brightness = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self._brightness.set_draw_value(False)
        self._brightness.connect("value-changed", self._on_wheel_changed)
        brightness_row = Adw.ActionRow(title="Brightness")
        brightness_row.add_suffix(self._brightness)
        self._brightness.set_size_request(200, -1)
        self._hex = Adw.EntryRow(title="Color (hex)", show_apply_button=True)
        self._hex.connect("apply", self._on_hex_apply)
        power_group = Adw.PreferencesGroup(title="Lightbar")
        power_group.add(self._switch)
        color_group = Adw.PreferencesGroup()
        color_group.add(brightness_row)
        color_group.add(self._hex)
        # Grouped so the banner can disable every lightbar control at once.
        self._lightbar_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for widget in (power_group, self._wheel, color_group):
            self._lightbar_controls.append(widget)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for margin in ("top", "bottom", "start", "end"):
            getattr(page, f"set_margin_{margin}")(18)
        page.append(self._banner)
        page.append(controller_group)
        page.append(self._lightbar_controls)
        clamp = Adw.Clamp(maximum_size=480, child=page)
        scrolled = Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._empty, "empty")
        self._stack.add_named(scrolled, "controller")
        self._toasts = Adw.ToastOverlay(child=self._stack)
        toolbar = Adw.ToolbarView(content=self._toasts)
        toolbar.add_top_bar(Adw.HeaderBar())
        self.set_content(toolbar)

    # Controller discovery

    def _on_poll(self) -> bool:
        self._refresh()
        return True

    def _refresh(self) -> None:
        found = {_key(controller): controller for controller in find_controllers()}
        newly_connected = [key for key in found if key not in self._controllers]
        for key in self._controllers.keys() - found.keys():
            self._charge.forget(key)
        self._controllers = found
        self._check_charging()
        keys = list(found)
        if keys != self._keys:
            self._keys = keys
            self._updating = True
            self._combo.set_model(Gtk.StringList.new([_label(found[key]) for key in keys]))
            self._updating = False
        if self._selected not in found:
            self._selected = keys[0] if keys else None
        if self._selected is not None:
            self._updating = True
            self._combo.set_selected(self._keys.index(self._selected))
            self._updating = False
        # The kernel resets the lightbar when a controller connects.
        for key in newly_connected:
            self._apply_saved(found[key], self._config.lightbar(key))
        self._update_view()

    def _check_charging(self) -> None:
        """Tell the user when any connected controller finishes charging."""
        for key, controller in self._controllers.items():
            battery = read_battery(controller.battery_path) if controller.battery_path else None
            if self._charge.update(key, battery):
                self._notify_charged(key, controller)

    def _notify_charged(self, key: str, controller: Controller) -> None:
        message = f"{_label(controller)} is fully charged."
        self._toasts.add_toast(Adw.Toast(title=message))
        if self.is_active():
            return
        # The window is in the background, so also use a desktop notification.
        notification = Gio.Notification.new("Controller charged")
        notification.set_body(message)
        notification.set_icon(Gio.ThemedIcon.new("battery-full-charged-symbolic"))
        self.get_application().send_notification(f"charged-{key}", notification)

    def _apply_saved(self, controller: Controller, settings: LightbarSettings) -> None:
        if controller.lightbar is None:
            return
        try:
            set_color(controller.lightbar, avoid_black(settings.color) if settings.enabled else OFF)
        except OSError:
            pass

    def _on_combo_selected(self, combo: Adw.ComboRow, _param) -> None:
        if self._updating or combo.get_selected() >= len(self._keys):
            return
        self._selected = self._keys[combo.get_selected()]
        self._update_view()

    # View

    def _update_view(self) -> None:
        controller = self._controllers.get(self._selected) if self._selected else None
        if controller is None:
            self._stack.set_visible_child_name("empty")
            self._shown = None
            return
        self._stack.set_visible_child_name("controller")
        self._combo.set_visible(len(self._keys) > 1)
        self._update_battery(controller)
        self._update_banner(controller)
        if self._shown != self._selected:
            self._shown = self._selected
            settings = self._config.lightbar(self._selected)
            self._color, self._enabled = settings.color, settings.enabled
            self._sync_widgets()

    def _update_battery(self, controller: Controller) -> None:
        battery = read_battery(controller.battery_path) if controller.battery_path else None
        if battery is None or battery.capacity is None:
            self._battery_bar.set_value(0)
            self._battery_label.set_label("Not available")
            return
        self._battery_bar.set_value(battery.capacity / 100)
        self._battery_label.set_label(f"{battery.capacity}% · {battery.status}")

    def _update_banner(self, controller: Controller) -> None:
        if controller.lightbar is None:
            self._banner.set_title("The kernel driver does not expose this controller's lightbar.")
            self._banner.set_button_label(None)
        elif not can_write(controller.lightbar):
            self._banner.set_title("The lightbar is read-only until the udev rule is installed.")
            self._banner.set_button_label("Show commands")
        else:
            self._banner.set_revealed(False)
            self._lightbar_controls.set_sensitive(True)
            return
        self._banner.set_revealed(True)
        self._lightbar_controls.set_sensitive(False)

    def _on_banner_clicked(self, _banner) -> None:
        commands = Gtk.Label(label=UDEV_INSTALL_COMMANDS, selectable=True, xalign=0)
        commands.add_css_class("monospace")
        dialog = Adw.AlertDialog(
            heading="Install the udev rule",
            body="Run these commands from the project folder, then reconnect the controller.",
            extra_child=commands,
        )
        dialog.add_response("close", "Close")
        dialog.present(self)

    def _sync_widgets(self, *, move_pickers: bool = True) -> None:
        """Show the current color in the widgets without re-triggering them.

        The wheel and the brightness slider are left alone when the user is
        dragging them: rebuilding their position from the rounded RGB color
        would make the marker jitter and lose the hue at low brightness.
        """
        self._updating = True
        self._switch.set_active(self._enabled)
        if move_pickers:
            hue, saturation, value = self._color.to_hsv()
            self._wheel.set_position(hue, saturation)
            self._brightness.set_value(max(value, 0.01) * 100)
        self._hex.set_text(self._color.to_hex())
        self._hex.remove_css_class("error")
        self._updating = False

    # User actions

    def _on_wheel_changed(self, _widget) -> None:
        if self._updating:
            return
        color = Color.from_hsv(self._wheel.hue, self._wheel.saturation, self._brightness.get_value() / 100)
        self._set_color(color, move_pickers=False)

    def _on_hex_apply(self, _row) -> None:
        try:
            color = Color.from_hex(self._hex.get_text().strip())
        except ValueError:
            self._hex.add_css_class("error")
            return
        self._set_color(color)

    def _on_switch(self, switch: Adw.SwitchRow, _param) -> None:
        if self._updating:
            return
        self._enabled = switch.get_active()
        self._schedule_apply()
        self._schedule_save()

    def _set_color(self, color: Color, *, move_pickers: bool = True) -> None:
        self._color = color
        # Picking a color while the light is off turns it back on.
        self._enabled = True
        self._sync_widgets(move_pickers=move_pickers)
        self._schedule_apply()
        self._schedule_save()

    # Writing to the controller and to disk

    def _schedule_apply(self) -> None:
        if not self._apply_source:
            self._apply_source = GLib.timeout_add(APPLY_DELAY_MS, self._flush_apply)

    def _flush_apply(self) -> bool:
        self._apply_source = 0
        controller = self._controllers.get(self._selected) if self._selected else None
        if controller is not None:
            self._apply_saved(controller, LightbarSettings(self._color, self._enabled))
        return False

    def _schedule_save(self) -> None:
        if self._save_source:
            GLib.source_remove(self._save_source)
        self._save_source = GLib.timeout_add(SAVE_DELAY_MS, self._flush_save)

    def _flush_save(self) -> bool:
        self._save_source = 0
        if self._selected is not None:
            self._config.set_lightbar(self._selected, LightbarSettings(self._color, self._enabled))
        return False
