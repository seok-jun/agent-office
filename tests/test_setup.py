import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import doctor
import setup_office
from install_hooks import merge_config


class SetupTests(unittest.TestCase):
    def test_auto_only_detects_existing_provider_roots(self):
        with tempfile.TemporaryDirectory() as d:
            roots = {'Claude': Path(d)/'claude', 'Codex': Path(d)/'codex'}
            roots['Codex'].mkdir()
            with patch('setup_office.roots', return_value=roots), patch('setup_office.shutil.which', return_value=None):
                self.assertEqual(setup_office.providers('auto'), ['Codex'])
                self.assertEqual(setup_office.providers('none'), [])

    def test_dry_run_does_not_create_environment_or_run_commands(self):
        with tempfile.TemporaryDirectory() as d, patch('setup_office.APP', Path(d)), patch('sys.argv', ['setup_office.py', '--dry-run', '--provider', 'both']), patch('setup_office.subprocess.run') as run:
            self.assertEqual(setup_office.main(), 0)
            self.assertEqual(list(Path(d).iterdir()), [])
            run.assert_not_called()

    def test_diagnosis_distinguishes_registration_from_trust_and_signal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config = merge_config({'theme': 'dark'}, 'Codex')
            (root/'hooks.json').write_text(json.dumps(config), encoding='utf-8')
            before = (root/'hooks.json').read_bytes()
            with patch('doctor.APP', root), patch('doctor.roots', return_value={'Codex': root}), patch('pet_assets.candidates', return_value=[]):
                checks = {c['check']: c for c in doctor.diagnose('Codex')}
            self.assertEqual(checks['Codex.hooks']['status'], 'ok')
            self.assertEqual(checks['Codex.trust']['status'], 'manual')
            self.assertEqual(checks['Codex.signal']['status'], 'warning')
            self.assertEqual((root/'hooks.json').read_bytes(), before)

    def test_invalid_settings_report_error_without_modification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'settings.json').write_text('{broken')
            with patch('doctor.APP', root), patch('doctor.roots', return_value={'Claude': root}), patch('pet_assets.candidates', return_value=[]):
                checks = {c['check']: c for c in doctor.diagnose('Claude')}
            self.assertEqual(checks['Claude.hooks']['status'], 'error')
            self.assertEqual((root/'settings.json').read_text(), '{broken')
