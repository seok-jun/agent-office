"""Read-only connection checks. No messages, model calls, or trust changes."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

from install_hooks import handler
from setup_office import APP, environment_python, providers, roots


def diagnose(choice='auto'):
    checks = []
    def add(name, status, detail):
        checks.append(dict(check=name, status=status, detail=detail))
    add('python', 'ok' if sys.version_info >= (3, 10) else 'error', sys.version.split()[0])
    add('virtual_environment', 'ok' if Path(sys.executable).resolve() == environment_python().resolve() else 'warning',
        'Use the .venv Python for matching installed hook definitions.')
    add('tkinter', 'ok' if importlib.util.find_spec('tkinter') else 'error', 'Required for desktop UI; display availability is not tested.')
    pillow = importlib.util.find_spec('PIL') is not None
    add('webp_decoder', 'ok' if pillow else 'warning', 'Pillow installed.' if pillow else 'WebP pets unavailable; robots remain usable.')
    selected = providers(choice)
    if not selected:
        add('providers', 'warning', 'No provider selected/detected. Demo works; use --provider to configure explicitly.')
    for name in selected:
        root = roots()[name]
        logs = root / ('projects' if name == 'Claude' else 'sessions')
        add(name+'.logs', 'ok' if logs.is_dir() else 'warning', 'Log folder exists; session freshness/content is not checked.' if logs.is_dir() else 'No log folder. Run this provider or check its environment variable.')
        target = root / ('settings.json' if name == 'Claude' else 'hooks.json')
        try:
            config = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() else {}
            hooks = config.get('hooks', {})
            required = ['PreCompact', 'PostCompact', 'Stop', 'SessionEnd', 'Interrupt' if name == 'Codex' else 'StopFailure']
            missing = [event for event in required if not any(handler(name) == h for group in hooks.get(event, []) for h in group.get('hooks', []))]
            add(name+'.hooks', 'warning' if missing else 'ok', 'Missing or different: '+', '.join(missing) if missing else 'All definitions match this Python and installation.')
        except (OSError, ValueError, TypeError, AttributeError):
            add(name+'.hooks', 'error', 'Settings unreadable or malformed. Inspect locally; no changes made.')
        if name == 'Codex':
            add(name+'.trust', 'manual', 'Trust is not inspected. User must review /hooks; registration alone does not prove execution.')
        newest = 0
        for path in (APP/'runtime/compaction').glob('*.json'):
            try:
                if path.stat().st_size > 16384:
                    continue
                record = json.loads(path.read_text(encoding='utf-8'))
                if record.get('provider') == name:
                    stamp = record.get('at')
                    if isinstance(stamp, (int, float)) and stamp <= time.time():
                        newest = max(newest, stamp)
            except (OSError, ValueError, AttributeError):
                continue
        add(name+'.signal', 'ok' if newest else 'warning',
            f'Last local signal {int(time.time()-newest)} seconds ago; not proof of a current live connection.' if newest else 'No received signal. Check after actual compaction; absence before first use is normal.')
    from pet_assets import has_local_asset
    PETS = ['codex', 'dewey', 'fireball', 'hoots', 'rocky', 'seedy', 'stacky', 'bsod', 'null-signal']
    found = sum(has_local_asset(pet) for pet in PETS)
    add('pet_files', 'ok' if found else 'warning', f'{found}/{len(PETS)} local candidates found; decoding not checked here. Missing/invalid files use robots.')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['auto', 'Claude', 'Codex', 'both', 'none'], default='auto')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    checks = diagnose(args.provider)
    if args.json:
        print(json.dumps({'checks': checks, 'errors': sum(c['status']=='error' for c in checks)}, ensure_ascii=True))
    else:
        for c in checks:
            print(f"[{c['status']}] {c['check']}: {c['detail']}")
    return int(any(c['status']=='error' for c in checks))


if __name__ == '__main__':
    sys.exit(main())
