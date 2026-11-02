import tempfile
import unittest
from pathlib import Path

from ds4linux.config import DEFAULT_COLOR, Config, LightbarSettings
from ds4linux.lightbar import Color


class ConfigTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "nested" / "config.json"

    def test_unknown_controller_gets_defaults(self):
        settings = Config(self.path).lightbar("aa:bb")
        self.assertEqual(settings.color, DEFAULT_COLOR)
        self.assertTrue(settings.enabled)

    def test_settings_survive_a_restart(self):
        Config(self.path).set_lightbar("aa:bb", LightbarSettings(Color(1, 2, 3), enabled=False))
        settings = Config(self.path).lightbar("aa:bb")
        self.assertEqual(settings, LightbarSettings(Color(1, 2, 3), enabled=False))

    def test_each_controller_keeps_its_own_settings(self):
        config = Config(self.path)
        config.set_lightbar("aa", LightbarSettings(Color(255, 0, 0)))
        config.set_lightbar("bb", LightbarSettings(Color(0, 255, 0)))
        reloaded = Config(self.path)
        self.assertEqual(reloaded.lightbar("aa").color, Color(255, 0, 0))
        self.assertEqual(reloaded.lightbar("bb").color, Color(0, 255, 0))

    def test_corrupt_file_falls_back_to_defaults(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{ not json")
        self.assertEqual(Config(self.path).lightbar("aa").color, DEFAULT_COLOR)

    def test_invalid_entry_is_skipped_but_others_load(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            '{"lightbars": {"bad": {"color": "zzz", "enabled": true},'
            ' "good": {"color": "#010203", "enabled": false}}}'
        )
        config = Config(self.path)
        self.assertEqual(config.lightbar("bad").color, DEFAULT_COLOR)
        self.assertEqual(config.lightbar("good"), LightbarSettings(Color(1, 2, 3), enabled=False))

    def test_save_leaves_no_temporary_file(self):
        Config(self.path).set_lightbar("aa", LightbarSettings())
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["config.json"])


if __name__ == "__main__":
    unittest.main()
