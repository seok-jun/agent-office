import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import ANY, patch
from PIL import Image
import pet_downloads as downloads


class DownloadTests(unittest.TestCase):
    def sheet(self):
        data = io.BytesIO()
        Image.new('RGBA', (1536, 1872)).save(data, format='WEBP')
        return data.getvalue()

    def test_download_is_validated_and_reused(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('pet_downloads.urlopen', return_value=io.BytesIO(self.sheet())) as fetch:
                self.assertEqual(downloads.download_pet('codex', root), 'downloaded')
                self.assertEqual(downloads.download_pet('codex', root), 'cached')
                fetch.assert_called_once_with(ANY, timeout=30, context=ANY)
                self.assertEqual(fetch.call_args.args[0].full_url,
                                 downloads.BASE_URL+'/codex-spritesheet-v4.webp')
            self.assertEqual(len(list(Path(root).iterdir())), 1)

    def test_invalid_response_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root)/'codex-spritesheet-v4.webp'
            target.write_bytes(b'old damaged file')
            with patch('pet_downloads.urlopen', return_value=io.BytesIO(b'not an image')):
                with self.assertRaises(OSError):
                    downloads.download_pet('codex', root)
            self.assertEqual(target.read_bytes(), b'old damaged file')
            self.assertEqual(len(list(Path(root).iterdir())), 1)

    def test_rejects_unknown_ids_oversized_and_wrong_dimensions(self):
        with patch('pet_downloads.urlopen') as fetch:
            with self.assertRaises(ValueError):
                downloads.download_pet('../other')
            fetch.assert_not_called()
        with self.assertRaises(ValueError):
            downloads.validate(b'x'*(downloads.MAX_BYTES+1))
        data = io.BytesIO()
        Image.new('RGBA', (20, 20)).save(data, format='WEBP')
        with self.assertRaises(ValueError):
            downloads.validate(data.getvalue())
