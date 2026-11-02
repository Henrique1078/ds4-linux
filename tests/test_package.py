import unittest

import ds4linux


class PackageTest(unittest.TestCase):
    def test_version_is_defined(self):
        self.assertIsInstance(ds4linux.__version__, str)
        self.assertTrue(ds4linux.__version__)


if __name__ == "__main__":
    unittest.main()
