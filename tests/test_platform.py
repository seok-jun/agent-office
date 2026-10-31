import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pet_assets
from install_hooks import handler
from ui_platform import wheel_units


class PlatformTests(unittest.TestCase):
    def test_aqua_small_deltas_and_windows_notches(self):
        self.assertEqual(wheel_units(1, 'aqua'), -1)
        self.assertEqual(wheel_units(-2, 'aqua'), 2)
        self.assertEqual(wheel_units(0.5, 'aqua'), -1)
        self.assertEqual(wheel_units(0, 'aqua'), 0)
        self.assertEqual(wheel_units(120, 'win32'), -1)
        self.assertEqual(wheel_units(-240, 'win32'), 2)

    def test_mac_archives_do_not_launch_powershell(self):
        pet_assets.desktop_archives.cache_clear()
        try:
            with patch('pet_assets.sys.platform', 'darwin'), patch('pet_assets.Path.home', return_value=Path('/test-home')), patch('pet_assets.subprocess.run') as run:
                self.assertEqual(pet_assets.desktop_archives(), (
                    Path('/Applications/Codex.app/Contents/Resources/app.asar'),
                    Path('/test-home/Applications/Codex.app/Contents/Resources/app.asar')))
                run.assert_not_called()
        finally:
            pet_assets.desktop_archives.cache_clear()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX shell test')
    def test_posix_hooks_with_unicode_spaces_and_shell_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "한글 office $cash & team's"
            root.mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1] / 'compaction_hook.py', root)
            for provider in ('Claude', 'Codex'):
                with patch('install_hooks.APP', root):
                    definition = handler(provider)
                command = ([definition['command'], *definition['args']] if provider == 'Claude'
                           else ['/bin/sh', '-c', definition['command']])
                for event in ('PreCompact', 'PostCompact'):
                    result = subprocess.run(command, input=json.dumps({
                        'session_id': 'synthetic-' + provider, 'hook_event_name': event
                    }), encoding='utf-8', capture_output=True, timeout=15, cwd=directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, '')
                records = [json.loads(p.read_text(encoding='utf-8'))
                           for p in (root / 'runtime/compaction').glob('*.json')]
                self.assertTrue(any(r['provider'] == provider and r['phase'] == 'end'
                                    for r in records))
