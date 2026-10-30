from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from pet_assets import candidates, load_sheet


class PetAssetsTests(unittest.TestCase):
    def test_environment_root(self):
        with patch.dict('os.environ', {'CODEX_HOME': 'custom-codex'}):
            self.assertEqual(candidates('dewey')[1],
                Path('custom-codex/cache/tui-pets/v1/assets/dewey-spritesheet-v4.webp'))

    def test_missing_and_invalid_files_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(load_sheet('codex', None, root, root))
            path = candidates('codex', root, root)[1]
            path.parent.mkdir(parents=True)
            path.write_bytes(b'not an image')
            self.assertIsNone(load_sheet('codex', None, root, root))

    def test_webp_cache_and_atlas_cropping(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Install requirements.txt to exercise WebP decoding')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = candidates('codex', root, root)[1]
            path.parent.mkdir(parents=True)
            Image.new('RGBA', (1536, 1872), (30, 160, 90, 255)).save(path, lossless=True)
            original = path.read_bytes()
            window = tk.Tk()
            window.withdraw()
            try:
                sheet = load_sheet('codex', window, root, root)
                self.assertEqual((sheet.width(), sheet.height()), (1536, 1872))
                crop = tk.PhotoImage(master=window, width=192, height=208)
                crop.tk.call(str(crop), 'copy', str(sheet), '-from', 0, 0, 192, 208, '-to', 0, 0)
                self.assertEqual(crop.get(10, 10), (30, 160, 90))
                self.assertEqual(path.read_bytes(), original)
                Image.new('RGBA', (20, 20)).save(path)
                self.assertIsNone(load_sheet('codex', window, root, root))
            finally:
                window.destroy()
