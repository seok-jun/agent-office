from pathlib import Path
import tempfile
import struct
import json
import io
import tkinter as tk
import unittest
from unittest.mock import patch

from pet_assets import candidates, load_sheet, desktop_bytes


class PetAssetsTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('pet_assets.desktop_archives', return_value=())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_desktop_v2_atlas_and_truncated_archive(self):
        from PIL import Image
        raw = io.BytesIO()
        Image.new('RGBA', (1536, 2288), (90, 100, 150, 255)).save(raw, format='WEBP', lossless=True)
        data = raw.getvalue()
        header = json.dumps({'files': {'webview': {'files': {'assets': {'files': {
            'codex-spritesheet-v6-test.webp': {'size': len(data), 'offset': '0'}
        }}}}}}).encode()
        packed = struct.pack('<4I', 4, len(header)+8, len(header)+4, len(header))+header+data
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); archive=root/'app.asar';archive.write_bytes(packed)
            with patch('pet_assets.desktop_archives', return_value=(archive,)):
                self.assertEqual(next(desktop_bytes('codex')), data)
                self.assertEqual(list(desktop_bytes('dewey')), [])
                window=tk.Tk();window.withdraw()
                try:
                    sheet=load_sheet('codex',window,root,root)
                    self.assertEqual((sheet.width(),sheet.height()),(1536,2288))
                finally:
                    window.destroy()
                archive.write_bytes(packed[:-100])
                self.assertEqual(list(desktop_bytes('codex')), [])

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
