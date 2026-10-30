import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from install_hooks import handler, install, merge_config, remove_config
from monitor import Monitor


class DistributionTests(unittest.TestCase):
    def test_remove_preserves_unrelated_settings_and_mixed_group(self):
        for provider in ('Claude', 'Codex'):
            other = {'type': 'command', 'command': 'unrelated'}
            original = {'permissions': {'allow': ['Read']}, 'theme': 'dark'}
            merged = merge_config(original, provider)
            merged['hooks']['PreCompact'][0]['hooks'].append(other)
            cleaned = remove_config(merged, provider)
            self.assertEqual(cleaned['permissions'], original['permissions'])
            self.assertEqual(cleaned['theme'], 'dark')
            self.assertEqual(cleaned['hooks'], {'PreCompact': [{'hooks': [other]}]})
            self.assertEqual(remove_config(cleaned, provider), cleaned)

    def test_preview_install_backup_idempotency_and_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for provider in ('Claude', 'Codex'):
                target = root / (provider + '.json')
                original = b'{"theme":"dark"}'
                target.write_bytes(original)
                with patch('install_hooks.APP', root):
                    install(provider, target, preview=True)
                    self.assertEqual(target.read_bytes(), original)
                    self.assertFalse((root / 'runtime').exists())
                    result = install(provider, target)
                    self.assertEqual(Path(result['backup']).read_bytes(), original)
                    self.assertEqual(install(provider, target)['status'], 'unchanged')
                    install(provider, target, remove=True)
                    self.assertEqual(json.loads(target.read_text()), {'theme': 'dark'})
                # Use separate runtime roots between iterations.
                shutil.rmtree(root / 'runtime')

    @unittest.skipUnless(os.name == 'nt', 'Windows hook shell test')
    def test_commands_execute_from_unicode_spaces_and_shell_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "한글 office $cash & team's"
            root.mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1] / 'compaction_hook.py', root)
            for provider in ('Claude', 'Codex'):
                with patch('install_hooks.APP', root):
                    h = handler(provider)
                command = ([h['command'], *h['args']] if provider == 'Claude' else
                           ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', h['commandWindows']])
                for event in ('PreCompact', 'PostCompact'):
                    result = subprocess.run(command, input=json.dumps({
                        'session_id': 'synthetic-' + provider, 'hook_event_name': event
                    }), encoding='utf-8', capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, '')
                records = [json.loads(p.read_text()) for p in (root / 'runtime/compaction').glob('*.json')]
                self.assertTrue(any(r['provider'] == provider and r['phase'] == 'end' for r in records))

    def test_new_user_without_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(Monitor({'Codex': root/'sessions', 'Claude': root/'projects'}).scan(), [])


if __name__ == '__main__':
    unittest.main()
