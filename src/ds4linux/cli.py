"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from ds4linux.battery import read_battery
from ds4linux.device import Controller, find_controllers


def _describe(controller: Controller) -> dict:
    battery = read_battery(controller.battery_path) if controller.battery_path else None
    return {
        "model": controller.model,
        "name": controller.name,
        "hid_id": controller.hid_id,
        "vendor_id": f"{controller.vendor_id:04x}",
        "product_id": f"{controller.product_id:04x}",
        "bus": controller.bus,
        "mac": controller.mac,
        "usb_port": controller.usb_port,
        "driver": controller.driver,
        "lightbar": controller.lightbar is not None,
        "battery": None
        if battery is None
        else {"capacity": battery.capacity, "status": battery.status},
    }


def _print_human(info: dict) -> None:
    where = info["bus"] + (f", port {info['usb_port']}" if info["usb_port"] else "")
    print(f"{info['model']} [{where}]")
    print(f"  id:       {info['hid_id']}")
    print(f"  mac:      {info['mac'] or 'unknown'}")
    print(f"  driver:   {info['driver'] or 'none'}")
    print(f"  lightbar: {'available' if info['lightbar'] else 'not available'}")
    battery = info["battery"]
    if battery is None:
        print("  battery:  not available")
    else:
        level = "unknown" if battery["capacity"] is None else f"{battery['capacity']}%"
        print(f"  battery:  {level} ({battery['status']})")


def _list(args: argparse.Namespace) -> int:
    infos = [_describe(controller) for controller in find_controllers()]
    if args.json:
        print(json.dumps(infos, indent=2))
    elif not infos:
        print("No DualShock 4 controller found.", file=sys.stderr)
    else:
        for info in infos:
            _print_human(info)
    return 0


def _gui(_args: argparse.Namespace) -> int:
    try:
        from ds4linux.ui.app import run
    except (ImportError, ValueError) as error:
        print(f"The graphical interface needs GTK4 and libadwaita: {error}", file=sys.stderr)
        return 1
    return run([sys.argv[0]])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ds4-linux")
    parser.set_defaults(handler=_gui)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="open the graphical interface (default)").set_defaults(handler=_gui)
    list_command = commands.add_parser("list", help="list connected DualShock 4 controllers")
    list_command.add_argument("--json", action="store_true", help="print machine-readable output")
    list_command.set_defaults(handler=_list)
    args = parser.parse_args(argv)
    return args.handler(args)
