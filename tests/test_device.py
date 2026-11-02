import tempfile
import unittest
from pathlib import Path

import fakesys
from ds4linux.device import find_controllers


class FindControllersTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_empty_sysfs_has_no_controllers(self):
        self.assertEqual(find_controllers(self.root), [])

    def test_finds_controller_on_any_usb_port(self):
        ports = {
            "1-3": "pci0000:00/usb1/1-3/1-3:1.3",
            "2-6.2": "pci0000:00/usb2/2-6/2-6.2/2-6.2:1.3",
            "1-1.4.3": "pci0000:00/usb1/1-1/1-1.4/1-1.4.3/1-1.4.3:1.3",
        }
        for port, parents in ports.items():
            with self.subTest(port=port):
                root = self.root / port
                fakesys.add_hid_device(root, parents)
                (controller,) = find_controllers(root)
                self.assertEqual(controller.usb_port, port)
                self.assertEqual(controller.bus, "usb")

    def test_reads_identity(self):
        fakesys.add_hid_device(self.root, "pci0000:00/usb1/1-3/1-3:1.3")
        (controller,) = find_controllers(self.root)
        self.assertEqual(controller.vendor_id, 0x054C)
        self.assertEqual(controller.product_id, 0x09CC)
        self.assertEqual(controller.model, "DualShock 4 (v2)")
        self.assertEqual(controller.mac, "a0:5a:5d:54:95:26")
        self.assertEqual(controller.driver, "playstation")

    def test_finds_first_generation_controller(self):
        fakesys.add_hid_device(self.root, "pci0000:00/usb1/1-3/1-3:1.3", product=0x05C4)
        (controller,) = find_controllers(self.root)
        self.assertEqual(controller.model, "DualShock 4 (v1)")

    def test_finds_bluetooth_controller(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-7/1-7:1.0/bluetooth/hci0/hci0:11",
            bus=fakesys.BUS_BLUETOOTH,
        )
        (controller,) = find_controllers(self.root)
        self.assertEqual(controller.bus, "bluetooth")
        self.assertIsNone(controller.usb_port)
        self.assertIsNotNone(controller.lightbar)

    def test_ignores_other_hid_devices(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-6/1-6.4/1-6.4:1.1",
            vendor=0x046D,
            product=0x4091,
            name="Logitech Wireless Mouse PID:4091",
            driver="logitech-hidpp-device",
            leds=None,
            battery=None,
        )
        self.assertEqual(find_controllers(self.root), [])

    def test_ignores_dualsense(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-3/1-3:1.3",
            product=0x0CE6,
            name="Sony Interactive Entertainment DualSense Wireless Controller",
        )
        self.assertEqual(find_controllers(self.root), [])

    def test_finds_third_party_controller_handled_as_ds4(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-3/1-3:1.3",
            vendor=0x1234,
            product=0xABCD,
            name="Third Party Wireless Controller",
        )
        (controller,) = find_controllers(self.root)
        self.assertEqual(controller.model, "Third Party Wireless Controller")
        self.assertIsNotNone(controller.lightbar)

    def test_controller_without_driver_has_no_lightbar_or_battery(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-3/1-3:1.3",
            driver=None,
            leds=None,
            battery=None,
        )
        (controller,) = find_controllers(self.root)
        self.assertIsNone(controller.driver)
        self.assertIsNone(controller.lightbar)
        self.assertIsNone(controller.battery_path)

    def test_links_lightbar_and_battery_to_the_right_controller(self):
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb1/1-3/1-3:1.3",
            mac="aa:aa:aa:aa:aa:aa",
            index=1,
            leds="input8",
            battery=("Charging", 40),
        )
        fakesys.add_hid_device(
            self.root,
            "pci0000:00/usb2/2-6/2-6.2/2-6.2:1.3",
            mac="bb:bb:bb:bb:bb:bb",
            index=2,
            leds="input12",
            battery=("Full", 100),
        )
        first, second = find_controllers(self.root)
        self.assertEqual(first.usb_port, "1-3")
        self.assertIn("input8:red", str(first.lightbar.red))
        self.assertIn("aa:aa:aa:aa:aa:aa", str(first.battery_path))
        self.assertEqual(second.usb_port, "2-6.2")
        self.assertIn("input12:blue", str(second.lightbar.blue))
        self.assertIn("bb:bb:bb:bb:bb:bb", str(second.battery_path))

    def test_survives_a_broken_device(self):
        broken = self.root / "bus/hid/devices/0003:054C:09CC.0009"
        broken.mkdir(parents=True)
        fakesys.add_hid_device(self.root, "pci0000:00/usb1/1-3/1-3:1.3")
        self.assertEqual(len(find_controllers(self.root)), 1)


if __name__ == "__main__":
    unittest.main()
