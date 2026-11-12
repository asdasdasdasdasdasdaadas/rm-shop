import unittest

from app.vpn_apps import validate_vpn_apps

BASE = {'id': 'incy', 'name': 'Incy', 'deep_link': 'incy://import/{url}', 'platforms': ['ios'], 'stores': {'ios': 'https://apps.apple.com/x'}}


class VpnAppGuideTest(unittest.TestCase):
    def test_guide_link_is_kept_and_optional(self):
        self.assertEqual(validate_vpn_apps([{**BASE, 'guide': ' https://telegra.ph/how '}])[0]['guide'], 'https://telegra.ph/how')
        self.assertEqual(validate_vpn_apps([BASE])[0]['guide'], '')

    def test_guide_must_be_a_web_link(self):
        with self.assertRaisesRegex(ValueError, 'Как установить'):
            validate_vpn_apps([{**BASE, 'guide': 'javascript:alert(1)'}])


if __name__ == '__main__':
    unittest.main()
