from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamdeck_companion.core.package import PackageValidationError, ProfilePackage
from streamdeck_companion.streamdeck_archive import StreamdeckArchiveError, export_streamdeck, import_streamdeck


class StreamdeckArchiveTests(unittest.TestCase):
    def test_round_trip_preserves_portable_sections(self) -> None:
        package = ProfilePackage(
            profile={"id": "gaming", "name": "Gaming"},
            pages=({"id": "home"}, {"id": "media"}),
            folders=({"id": "games", "page_id": "media"},),
            actions=({"id": "launch-steam", "type": "launch"},),
            widgets=({"id": "cpu", "type": "gauge"},),
            assets={"icon": "assets/icon.png"},
            settings={"theme": "dark"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = export_streamdeck(package, Path(tmp) / "gaming")
            self.assertEqual(path.suffix, ".streamdeck")
            restored = import_streamdeck(path)
        self.assertEqual(restored.to_dict(), package.to_dict())

    def test_unknown_version_is_rejected(self) -> None:
        with self.assertRaises(PackageValidationError):
            ProfilePackage.from_dict({"format": "streamdeck-esp", "version": 99, "profile": {"id": "x"}})

    def test_invalid_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.streamdeck"
            path.write_text("not-a-zip", encoding="utf-8")
            with self.assertRaises(StreamdeckArchiveError):
                import_streamdeck(path)


if __name__ == "__main__":
    unittest.main()
