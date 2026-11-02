import tempfile
import unittest
from pathlib import Path

import fakesys
from ds4linux.device import find_controllers
from ds4linux.lightbar import OFF, Color, avoid_black, can_write, read_color, set_color, turn_off


class ColorTest(unittest.TestCase):
    def test_hex_round_trip(self):
        self.assertEqual(Color.from_hex("#ff8000"), Color(255, 128, 0))
        self.assertEqual(Color(255, 128, 0).to_hex(), "#ff8000")

    def test_hex_without_hash(self):
        self.assertEqual(Color.from_hex("00ff00"), Color(0, 255, 0))

    def test_invalid_hex_is_rejected(self):
        for value in ("#fff", "#gggggg", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Color.from_hex(value)

    def test_channels_must_be_in_range(self):
        for channels in ((256, 0, 0), (0, -1, 0)):
            with self.subTest(channels=channels), self.assertRaises(ValueError):
                Color(*channels)

    def test_avoid_black_replaces_only_pure_black(self):
        self.assertEqual(avoid_black(Color(0, 0, 0)), OFF)
        self.assertEqual(avoid_black(Color(0, 0, 1)), Color(0, 0, 1))
        self.assertEqual(avoid_black(Color(9, 8, 7)), Color(9, 8, 7))

    def test_hsv_primary_colors(self):
        self.assertEqual(Color.from_hsv(0.0, 1.0, 1.0), Color(255, 0, 0))
        self.assertEqual(Color.from_hsv(1 / 3, 1.0, 1.0), Color(0, 255, 0))
        self.assertEqual(Color.from_hsv(2 / 3, 1.0, 1.0), Color(0, 0, 255))
        self.assertEqual(Color.from_hsv(0.5, 0.0, 1.0), Color(255, 255, 255))

    def test_hsv_hue_wraps_around(self):
        self.assertEqual(Color.from_hsv(1.0, 1.0, 1.0), Color(255, 0, 0))

    def test_hsv_round_trip(self):
        color = Color(200, 100, 50)
        self.assertEqual(Color.from_hsv(*color.to_hsv()), color)


class LightbarTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        fakesys.add_hid_device(Path(tmp.name), "pci0000:00/usb1/1-3/1-3:1.3")
        (controller,) = find_controllers(Path(tmp.name))
        self.lightbar = controller.lightbar

    def test_set_and_read_color(self):
        set_color(self.lightbar, Color(10, 20, 30))
        self.assertEqual(read_color(self.lightbar), Color(10, 20, 30))

    def test_turn_off_sets_the_off_color(self):
        set_color(self.lightbar, Color(255, 255, 255))
        turn_off(self.lightbar)
        self.assertEqual(read_color(self.lightbar), OFF)

    def test_off_is_not_pure_black(self):
        # Pure black makes the controller firmware pulse orange while charging.
        self.assertNotEqual(OFF, Color(0, 0, 0))

    def test_turn_off_leaves_the_global_led_alone(self):
        global_led = self.lightbar.red.parent.parent / "input8:global" / "brightness"
        global_led.write_text("1\n")
        turn_off(self.lightbar)
        self.assertEqual(global_led.read_text(), "1\n")

    def test_read_color_returns_none_when_unreadable(self):
        self.lightbar.red.write_text("not a number")
        self.assertIsNone(read_color(self.lightbar))

    def test_can_write(self):
        self.assertTrue(can_write(self.lightbar))
        self.lightbar.green.chmod(0o444)
        self.assertFalse(can_write(self.lightbar))


if __name__ == "__main__":
    unittest.main()
