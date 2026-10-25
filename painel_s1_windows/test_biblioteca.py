import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from biblioteca import ImageLibrary
from protocolo import FRAME_BYTES


class ImageLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.app_directory = self.root / "app"
        self.app_directory.mkdir()
        self.source = self.root / "minha foto.png"
        Image.new("RGB", (64, 32), (220, 40, 10)).save(self.source)
        self.library = ImageLibrary(self.app_directory)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_prepares_visible_copy_and_reuses_rgb565_cache(self):
        entry = self.library.add("image", self.source)
        first = self.library.prepare_image(
            entry,
            self.source,
            "Preencher",
            "landscape",
        )
        self.assertEqual(len(first.pixels), FRAME_BYTES)
        self.assertEqual(first.preview_path.name, "minha foto.png")
        with Image.open(first.preview_path) as preview:
            self.assertEqual(preview.size, (320, 170))

        with patch("biblioteca.prepare_image_pixels", side_effect=AssertionError):
            second = self.library.prepare_image(
                entry,
                self.source,
                "Preencher",
                "landscape",
            )

        self.assertEqual(second.pixels, first.pixels)
        self.assertEqual(second.preview_path, first.preview_path)

    def test_portrait_cache_is_visually_oriented_for_the_panel(self):
        entry = self.library.add("image", self.source)
        prepared = self.library.prepare_image(
            entry,
            self.source,
            "Ajustar",
            "portrait",
        )

        with Image.open(prepared.preview_path) as preview:
            self.assertEqual(preview.size, (170, 320))

    def test_changed_source_invalidates_prepared_copy(self):
        entry = self.library.add("image", self.source)
        original = self.library.prepare_image(
            entry,
            self.source,
            "Estender",
            "landscape",
        )
        Image.new("RGB", (64, 32), (10, 40, 220)).save(self.source)
        stat = self.source.stat()
        os.utime(
            self.source,
            ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000),
        )

        updated = self.library.prepare_image(
            entry,
            self.source,
            "Estender",
            "landscape",
        )

        self.assertNotEqual(updated.pixels, original.pixels)

    def test_removing_library_entry_preserves_original_file(self):
        entry = self.library.add("image", self.source)
        prepared = self.library.prepare_image(
            entry,
            self.source,
            "Preencher",
            "landscape",
        )

        self.library.remove(entry)

        self.assertTrue(self.source.is_file())
        self.assertFalse(prepared.preview_path.exists())
        self.assertEqual(self.library.entries, [])

    def test_library_history_persists_across_instances(self):
        self.library.add("image", self.source)

        reopened = ImageLibrary(self.app_directory)

        self.assertEqual(len(reopened.entries), 1)
        self.assertEqual(reopened.entries[0]["name"], "minha foto.png")


if __name__ == "__main__":
    unittest.main()
