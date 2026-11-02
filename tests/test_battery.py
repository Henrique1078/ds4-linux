import tempfile
import unittest
from pathlib import Path

from ds4linux.battery import read_battery


class ReadBatteryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.supply = Path(tmp.name)

    def write(self, status=None, capacity=None):
        if status is not None:
            (self.supply / "status").write_text(f"{status}\n")
        if capacity is not None:
            (self.supply / "capacity").write_text(f"{capacity}\n")

    def test_reads_level_and_status(self):
        self.write("Discharging", 57)
        battery = read_battery(self.supply)
        self.assertEqual(battery.capacity, 57)
        self.assertEqual(battery.status, "Discharging")
        self.assertFalse(battery.charging)

    def test_charging_flag(self):
        self.write("Charging", 10)
        self.assertTrue(read_battery(self.supply).charging)

    def test_full_is_not_charging(self):
        self.write("Full", 100)
        self.assertFalse(read_battery(self.supply).charging)

    def test_missing_entry_returns_none(self):
        self.assertIsNone(read_battery(self.supply / "gone"))

    def test_invalid_capacity_is_unknown(self):
        self.write("Charging", "garbage")
        self.assertIsNone(read_battery(self.supply).capacity)

    def test_capacity_is_clamped(self):
        self.write("Full", 250)
        self.assertEqual(read_battery(self.supply).capacity, 100)

    def test_missing_status_is_unknown(self):
        self.write(capacity=30)
        self.assertEqual(read_battery(self.supply).status, "Unknown")


if __name__ == "__main__":
    unittest.main()
