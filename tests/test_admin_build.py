"""The built admin (admin/ui) loads its sections as separate files: every file the build asks for must be in git,
or after a deploy that section fails with «Не удалось открыть раздел»."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "admin" / "ui"


def _tracked() -> set[str] | None:
    try:
        out = subprocess.run(["git", "ls-files", "admin/ui"], cwd=ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return {line.removeprefix("admin/ui/") for line in out.stdout.splitlines()}


class AdminBuildTest(unittest.TestCase):
    def test_every_chunk_the_build_imports_is_committed(self):
        tracked = _tracked()
        if tracked is None:
            self.skipTest("no git here")
        missing = []
        for name in sorted(tracked):
            if not name.endswith(".js") or not (UI / name).exists():
                continue
            text = (UI / name).read_text(encoding="utf-8", errors="ignore")
            base = Path(name).parent
            for ref in set(re.findall(r'["\'`](\./[\w.-]+\.js|chunks/[\w.-]+\.js)["\'`]', text)):
                path = (base / ref).as_posix() if ref.startswith("./") else ref
                path = path.removeprefix("./")
                if path not in tracked:
                    missing.append(f"{name} → {path}")
        self.assertEqual(missing, [], "Собранная админка ссылается на файлы, которых нет в git: закоммитьте admin/ui целиком")


if __name__ == "__main__":
    unittest.main()
