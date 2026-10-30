"""Merge Agent Office hooks without changing existing permissions or hook trust."""
import argparse
import base64
import shlex
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

APP = Path(__file__).resolve().parent


def handler(provider):
    script = str(APP / 'compaction_hook.py')
    if provider == 'Claude':
        return dict(type='command', command=sys.executable,
                    args=[script, provider], timeout=3, onFailure='continue')
    # This absolute Python path has no dependency on the session working directory.
    argv = [sys.executable, script, provider]
    # Encoded literal arguments avoid shell expansion of spaces, $, quotes and Unicode.
    ps = '& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in argv)
    encoded = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
    windows = 'powershell.exe -NoProfile -NonInteractive -EncodedCommand ' + encoded
    return dict(type='command', command=shlex.join(argv), commandWindows=windows, timeout=3)



def merge_config(config, provider):
    result = copy.deepcopy(config)
    hooks = result.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('Existing hooks must be an object')
    events = ['PreCompact', 'PostCompact', 'Stop', 'SessionEnd']
    events += ['Interrupt'] if provider == 'Codex' else ['StopFailure']
    h = handler(provider)
    for event in events:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError('Existing hook event must be a list: ' + event)
        if not any(h == old for g in groups for old in g.get('hooks', [])):
            groups.append({'hooks': [copy.deepcopy(h)]})
    return result


def remove_config(config, provider):
    result = copy.deepcopy(config)
    expected = handler(provider)
    hooks = result.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('Existing hooks must be an object')
    for event, groups in list(hooks.items()):
        retained = []
        for group in groups:
            remaining = [h for h in group.get('hooks', []) if h != expected]
            if remaining == group.get('hooks', []):
                retained.append(group)
            elif remaining:
                retained.append(dict(group, hooks=remaining))
        if retained:
            hooks[event] = retained
        else:
            del hooks[event]
    if not hooks:
        result.pop('hooks', None)
    return result


def install(provider, target, preview=False, remove=False):
    old = target.read_bytes() if target.exists() else None
    config = json.loads(old.decode('utf-8-sig')) if old is not None else {}
    merged = remove_config(config, provider) if remove else merge_config(config, provider)
    if preview:
        return dict(provider=provider, target=str(target), action='remove' if remove else 'install',
                    changed=merged != config, handler=handler(provider))
    if merged == config:
        return dict(provider=provider, status='unchanged')
    backups = APP / 'runtime' / 'backups'
    backups.mkdir(parents=True, exist_ok=True)
    backup = backups / (provider.lower() + '-' + str(time.time_ns()) + '.json')
    if old is not None:
        backup.write_bytes(old)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Recheck before replacing so a concurrent settings edit isn't overwritten.
    if (target.read_bytes() if target.exists() else None) != old:
        raise RuntimeError('Settings changed during installation; retry')
    temporary = target.with_name(target.name + '.agent-office.tmp')
    temporary.write_text(json.dumps(merged, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temporary, target)
    return dict(provider=provider, status='removed' if remove else 'installed', target=str(target),
                backup=str(backup) if old is not None else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--remove', action='store_true', help='Remove only this installation’s exact hook definitions')
    parser.add_argument('--provider', choices=['Claude', 'Codex', 'both'], default='both')
    args = parser.parse_args()
    roots = {'Claude': Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home()/'.claude'))/'settings.json',
             'Codex': Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'hooks.json'}
    for provider, target in roots.items():
        if args.provider in ('both', provider):
            print(json.dumps(install(provider, target, args.preview, args.remove), ensure_ascii=True))


if __name__ == '__main__':
    main()
