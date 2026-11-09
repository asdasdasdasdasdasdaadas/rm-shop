import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import backup


class BackupCleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for p in [patch.object(backup, "backup_dir", return_value=self.dir),
                  patch.object(backup, "get_settings", return_value=SimpleNamespace(backup_keep_days=14))]:
            p.start()
            self.addCleanup(p.stop)

    def make(self, day: int, age_days: float) -> str:
        name = f"rm-shop-2026-10-{day:02d}T0001-MSK.sql.gz"
        path = self.dir / name
        path.write_bytes(b"x")
        ts = time.time() - age_days * 86400
        os.utime(path, (ts, ts))
        return name

    def names(self):
        return sorted(p.name for p in self.dir.iterdir())

    def test_prune_deletes_old_copies_but_keeps_three_newest(self):
        fresh = self.make(20, 1)
        old = [self.make(d, 30 + d) for d in range(1, 6)]
        self.assertEqual(backup.prune_old_backups(), 3)
        self.assertEqual(self.names(), sorted([fresh, old[0], old[1]]))

    def test_prune_keeps_three_even_when_all_are_old(self):
        names = [self.make(d, 100 + d) for d in range(1, 4)]
        self.assertEqual(backup.prune_old_backups(), 0)
        self.assertEqual(self.names(), sorted(names))

    def test_delete_one_copy(self):
        newest = self.make(20, 1)
        older = self.make(10, 5)
        backup.delete_backup(older)
        self.assertEqual(self.names(), [newest])

    def test_newest_copy_cannot_be_deleted(self):
        newest = self.make(20, 1)
        self.make(10, 5)
        with self.assertRaisesRegex(ValueError, "свежую"):
            backup.delete_backup(newest)

    def test_unknown_or_unsafe_name_is_rejected(self):
        self.make(20, 1)
        for name in ["../etc/passwd", "rm-shop-2026-10-01T0001-MSK.sql.gz"]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "не найден"):
                backup.delete_backup(name)


if __name__ == "__main__":
    unittest.main()
