"""Provider by IP: reading the iptoasn table, the names people know, and the line in the alert."""
import gzip
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from app import ip_isp

TABLE = "\n".join([
    "1.0.0.0\t1.0.0.255\t13335\tUS\tCLOUDFLARENET",
    "5.3.0.0\t5.3.255.255\t8359\tRU\tMTS PJSC",
    "5.4.0.0\t5.4.0.255\t0\tNone\tNot routed",
    "31.173.80.0\t31.173.87.255\t15378\tRU\tT2-MOBILE-AS T2 Mobile LLC",
    "95.24.0.0\t95.31.255.255\t8402\tRU\tCORBINA-AS PJSC Vimpelcom",
    "2a00:1fa0::\t2a00:1fa3:ffff:ffff:ffff:ffff:ffff:ffff\t8359\tRU\tMTS PJSC",
    "broken line",
]) + "\n"


class IspTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.path = Path(d.name) / "t.tsv.gz"
        with gzip.open(self.path, "wt") as fh:
            fh.write(TABLE)
        p = patch.object(ip_isp, "_index", None)
        p.start()
        self.addCleanup(p.stop)
        self.assertIsNone(ip_isp.lookup("5.3.1.1"))   # no table yet
        self.assertTrue(await ip_isp.ensure(self.path))

    async def test_ranges_names_and_kinds(self):
        self.assertEqual(ip_isp.text(ip_isp.lookup("5.3.1.1")), "МТС (RU)")
        self.assertEqual(ip_isp.text(ip_isp.lookup("31.173.81.9")), "Tele2 (мобильный, RU)")
        self.assertEqual(ip_isp.lookup("95.30.0.1")["name"], "Билайн")
        self.assertEqual(ip_isp.lookup("1.0.0.1")["name"], "CLOUDFLARENET")
        self.assertEqual(ip_isp.lookup("2a00:1fa1::5")["name"], "МТС")
        self.assertEqual(ip_isp.lookup("::ffff:5.3.1.1")["name"], "МТС")
        for ip in ("5.4.0.1", "5.5.0.1", "0.0.0.1", "nope", ""):
            self.assertIsNone(ip_isp.lookup(ip), ip)

    def test_names_from_the_real_table(self):
        say = lambda asn, cc, name: ip_isp.text(ip_isp.label(asn, cc, name))
        self.assertEqual(say(16345, "RU", 'BEE-AS PJSC "Vimpelcom"'), "Билайн (мобильный, RU)")
        self.assertEqual(say(3216, "RU", 'SOVAM-AS PJSC "Vimpelcom"'), "Билайн (RU)")
        self.assertEqual(say(31363, "RU", 'MOSCOW-AS JSC "ER-Telecom Holding"'), "Дом.ру (домашний, RU)")
        self.assertEqual(say(9123, "RU", 'TimeWeb-AS JSC "TIMEWEB"'), "TIMEWEB (хостинг, RU)")
        self.assertEqual(say(34665, "RU", "PINDC-AS Petersburg Internet Network ltd."), "Petersburg Internet Network (RU)")

    async def test_device_providers_and_the_alert_line(self):
        rows = [{"ip": "31.173.81.9"}, {"ip": "5.3.1.1"}, {"ip": "5.3.2.2"}, {"ip": "10.0.0.1"}]
        from app import db
        with patch.object(db, "device_ips_recent", AsyncMock(return_value=rows)):
            got = await ip_isp.device_providers(1)
            self.assertEqual([x["name"] for x in got], ["Tele2", "МТС"])
            from app import stuck_alert
            with patch.object(stuck_alert, "_diagnosis_only", AsyncMock(return_value=None)):
                out = await stuck_alert._diagnosis(None, 1)
        self.assertEqual(out["isp"], "Tele2 (мобильный, RU), МТС (RU)")
        text, _ = stuck_alert.format_no_traffic({"telegram_id": 1, "title": "iPhone", "traffic": 0}, 1, out)
        self.assertIn("📶 Провайдер: Tele2 (мобильный, RU), МТС (RU)", text)

    async def test_a_broken_download_keeps_the_old_table(self):
        bad = self.path.with_name("bad.tsv.gz")
        bad.write_bytes(b"not gzip")
        bad.touch()
        with patch.object(ip_isp, "_loaded_mtime", 0.0), self.assertLogs("rm-shop.ip-isp", "WARNING"):
            await ip_isp.ensure(bad)
        self.assertEqual(ip_isp.lookup("5.3.1.1")["name"], "МТС")


if __name__ == "__main__":
    unittest.main()
