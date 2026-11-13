"""Device names in the panel: Telegram nick (or the first name in Latin) + Telegram ID + device number."""
import re
import unittest

from app.web import device_panel_username as name


class DevicePanelUsernameTest(unittest.TestCase):
    def test_nick_and_id(self):
        self.assertEqual(name(123456789, "@Ivan_Petrov", "Иван"), "Ivan_Petrov_123456789")
        self.assertEqual(name(123456789, "ivan", None, 2), "ivan_123456789_2")

    def test_first_name_in_latin_then_tg(self):
        self.assertEqual(name(42, None, "Анна Щукина"), "anna_schukina_42")
        self.assertEqual(name(42, "", "🙂"), "tg_42")
        self.assertEqual(name(42, None, None), "tg_42")

    def test_long_name_is_cut_but_the_id_stays(self):
        u = name(7123456789, "a" * 32, None, 12)
        self.assertLessEqual(len(u), 36)
        self.assertTrue(u.endswith("_7123456789_12"))
        self.assertRegex(u, r"^[A-Za-z0-9_-]{3,36}$")

    def test_only_allowed_characters(self):
        for nick, first in [("x.y", None), (None, "Jean-Luc O'Neil"), (None, "Ёжик в тумане")]:
            self.assertTrue(re.fullmatch(r"[A-Za-z0-9_-]{3,36}", name(5, nick, first)), name(5, nick, first))


if __name__ == "__main__":
    unittest.main()
