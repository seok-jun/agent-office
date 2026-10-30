"""Install locally without changing global Python packages or hook trust."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

APP = Path(__file__).resolve().parent


def roots():
    return {'Claude': Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home()/'.claude')),
            'Codex': Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))}


def providers(choice):
    if choice == 'none':
        return []
    if choice == 'both':
        return ['Claude', 'Codex']
    if choice != 'auto':
        return [choice]
    return [name for name, root in roots().items()
            if root.is_dir() or shutil.which(name.lower())]


def environment_python():
    return APP / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['auto', 'Claude', 'Codex', 'both', 'none'], default='auto')
    parser.add_argument('--robot-only', action='store_true', help='Skip Pillow installation; no network needed')
    parser.add_argument('--dry-run', action='store_true', help='Print plan without creating files or changing settings')
    args = parser.parse_args()
    selected = providers(args.provider)
    print(json.dumps({'python': str(environment_python()), 'providers': selected,
                      'install_pillow': not args.robot_only, 'dry_run': args.dry_run}))
    if args.dry_run:
        return 0
    if sys.version_info < (3, 10):
        raise RuntimeError('Python 3.10+ required; Python 3.14 is the tested version')
    import tkinter  # Fail before changing settings if this Python lacks tkinter.
    executable = environment_python()
    if not executable.exists():
        venv.EnvBuilder(with_pip=not args.robot_only).create(APP / '.venv')
    subprocess.run([str(executable), '-c', 'import tkinter'], check=True)
    if not args.robot_only:
        subprocess.run([str(executable), '-m', 'ensurepip'], check=True)
        subprocess.run([str(executable), '-m', 'pip', 'install', '-r', str(APP/'requirements.txt')], check=True)
    # Validate all selected JSON settings before mutating any of them.
    from install_hooks import merge_config
    for name in selected:
        target = roots()[name] / ('settings.json' if name == 'Claude' else 'hooks.json')
        config = json.loads(target.read_text(encoding='utf-8-sig')) if target.exists() else {}
        merge_config(config, name)
    for name in selected:
        subprocess.run([str(executable), str(APP/'install_hooks.py'), '--provider', name], check=True)
    print('Installation complete. Start.cmd or the .venv Python can launch app.py.')
    if 'Codex' in selected:
        print('User action: review and trust these hooks in Codex /hooks. Trust is not automated.')
    if selected:
        print('Restart existing Claude/Codex sessions if they have not loaded the hooks.')
    return subprocess.run([str(executable), str(APP/'doctor.py'), '--provider', args.provider]).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, AttributeError, ImportError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('Setup failed: ' + str(exc), file=sys.stderr)
        print('Correct the reported problem and rerun. Existing settings are backed up before changes.', file=sys.stderr)
        sys.exit(1)
