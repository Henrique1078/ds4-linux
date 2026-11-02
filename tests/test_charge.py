import unittest

from ds4linux.battery import Battery
from ds4linux.charge import ChargeTracker


def battery(status, capacity=50):
    return Battery(capacity=capacity, status=status)


class ChargeTrackerTest(unittest.TestCase):
    def setUp(self):
        self.tracker = ChargeTracker()

    def test_reports_when_charging_becomes_full(self):
        self.assertFalse(self.tracker.update("a", battery("Charging", 90)))
        self.assertTrue(self.tracker.update("a", battery("Full", 100)))

    def test_reports_only_once(self):
        self.tracker.update("a", battery("Charging"))
        self.assertTrue(self.tracker.update("a", battery("Full", 100)))
        self.assertFalse(self.tracker.update("a", battery("Full", 100)))

    def test_ignores_controller_already_full_when_first_seen(self):
        self.assertFalse(self.tracker.update("a", battery("Full", 100)))

    def test_ignores_a_controller_unplugged_while_charging(self):
        self.tracker.update("a", battery("Charging"))
        self.assertFalse(self.tracker.update("a", battery("Discharging")))
        self.assertFalse(self.tracker.update("a", battery("Full", 100)))

    def test_reports_each_charge_cycle(self):
        for _ in range(2):
            self.tracker.update("a", battery("Charging"))
            self.assertTrue(self.tracker.update("a", battery("Full", 100)))

    def test_controllers_are_tracked_separately(self):
        self.tracker.update("a", battery("Charging"))
        self.assertFalse(self.tracker.update("b", battery("Full", 100)))
        self.assertTrue(self.tracker.update("a", battery("Full", 100)))

    def test_failed_read_keeps_the_state(self):
        self.tracker.update("a", battery("Charging"))
        self.assertFalse(self.tracker.update("a", None))
        self.assertTrue(self.tracker.update("a", battery("Full", 100)))

    def test_forget_drops_the_state(self):
        self.tracker.update("a", battery("Charging"))
        self.tracker.forget("a")
        self.assertFalse(self.tracker.update("a", battery("Full", 100)))


if __name__ == "__main__":
    unittest.main()
