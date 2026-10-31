"""Verified Claude-to-Codex links. Never execute commands or retain prompts."""
import json
import os
from pathlib import Path
import re
import shlex
import tempfile


THREAD_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', re.I)
MAX_CALLS = 64


def valid_thread(value):
    return value.lower() if isinstance(value, str) and THREAD_ID.fullmatch(value) else None


def command_parts(command):
    """Tokenize literal commands only; quoted prompts/heredocs are never commands."""
    if not isinstance(command, str) or len(command) > 262144:
        return []
    command = re.sub(r'(?m)<<-?\s*([\'"]?)([A-Za-z_]\w*)\1[^\n]*\n.*?^\t*\2\s*$',
                     ';\n', command, flags=re.S)
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|<>()\n')
        lexer.whitespace = ' \t\r'
        lexer.whitespace_split = True
        parts, part = [], []
        for token in lexer:
            if token and all(c in ';&|()\n' for c in token):
                if part:
                    parts.append(part)
                    part = []
            else:
                part.append(token)
        if part:
            parts.append(part)
        return parts
    except ValueError:
        return []


def codex_invocations(command):
    variables = {}
    calls = []
    for part in command_parts(command):
        while part and re.match(r'^[A-Za-z_]\w*=', part[0]):
            key, value = part.pop(0).split('=', 1)
            if '$' not in value and '`' not in value:
                variables[key] = value
        if not part:
            continue
        executable = part[0].replace('\\', '/').rsplit('/', 1)[-1].lower()
        if executable not in ('codex', 'codex.exe', 'codex.cmd', 'codex.ps1'):
            continue
        args = part[1:]
        if not args or args[0] not in ('exec', 'e'):
            continue
        options = args[:args.index('--')] if '--' in args else args
        if '--help' in options or '-h' in options or '--version' in options:
            continue
        resume = valid_thread(args[2]) if len(args) > 2 and args[1] == 'resume' else None
        stdout = []
        if '--json' in options:
            for i, token in enumerate(args[:-1]):
                if token != '>' or (i and args[i-1].isdigit() and args[i-1] != '1'):
                    continue
                value = args[i+1]
                value = re.sub(r'\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)',
                               lambda m: variables.get(m[1] or m[2], m[0]), value)
                # Git Bash's local drive notation; unresolved expressions stay rejected.
                value = re.sub(r'^/([a-zA-Z])/', lambda m: m[1] + ':/', value) if os.name == 'nt' else value
                if not any(c in value for c in ('$','`','\n')):
                    stdout.append(value)
        calls.append({'thread': resume, 'stdout': stdout})
    return calls


def result_threads(content):
    """Accept protocol records, not UUIDs mentioned in ordinary result prose."""
    found = set()
    if isinstance(content, list):
        for block in content[:64]:
            if isinstance(block, dict) and block.get('type') == 'text':
                found.update(result_threads(block.get('text')))
        return found
    if isinstance(content, dict):
        if content.get('type') == 'thread.started':
            thread = valid_thread(content.get('thread_id'))
            if thread:
                found.add(thread)
        return found
    if not isinstance(content, str):
        return found
    for line in content[:65536].splitlines()[:128]:
        try:
            record = json.loads(line)
        except ValueError:
            record = None
        if isinstance(record, dict):
            found.update(result_threads(record))
        # Codex CLI's own header also carries an exact session identifier.
        match = re.fullmatch(r'\s*session id:\s*(' + THREAD_ID.pattern + r')\s*', line, re.I)
        if match:
            found.add(match[1])
    return found


class Delegations:
    def __init__(self, transcript):
        self.transcript = Path(transcript)
        self.calls = {}
        self.links = {}

    def consume(self, event, at):
        message = event.get('message') or {}
        blocks = message.get('content', []) if isinstance(message, dict) else []
        if not isinstance(blocks, list):
            return
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use':
                call_id = block.get('id')
                if not isinstance(call_id, str) or call_id in self.calls:
                    continue
                if block.get('name') not in ('Bash','PowerShell'):
                    continue
                args = block.get('input') or {}
                invocations = codex_invocations(args.get('command')) if isinstance(args, dict) else []
                if not invocations or not at:
                    continue
                outputs = []
                for invocation in invocations:
                    if invocation['thread']:
                        self.links[invocation['thread']] = max(at, self.links.get(invocation['thread'], 0))
                    for raw in invocation['stdout']:
                        path = self.output_path(raw, event.get('cwd'))
                        if path is not None:
                            outputs.append(path)
                self.calls[call_id] = {'at': at, 'outputs': outputs, 'signature': {}}
                while len(self.calls) > MAX_CALLS:
                    self.calls.pop(next(iter(self.calls)))
            elif event.get('type') == 'user' and block.get('type') == 'tool_result' and not block.get('is_error'):
                call = self.calls.get(block.get('tool_use_id'))
                if call:
                    for thread in result_threads(block.get('content')):
                        self.links[thread] = max(call['at'], self.links.get(thread, 0))

    def output_path(self, value, cwd):
        # Read only explicitly redirected JSONL under local transcript/project/temp roots.
        # Never open prompt inputs, last-message files, network shares, or arbitrary paths.
        if value.startswith(('//','\\\\')):
            return None
        path = Path(value)
        if not path.is_absolute() or path.suffix.lower() != '.jsonl':
            return None
        try:
            path = path.resolve()
            allowed = [self.transcript.parent.resolve(), Path(tempfile.gettempdir()).resolve()]
            if isinstance(cwd, str) and Path(cwd).is_absolute():
                allowed.append(Path(cwd).resolve())
            return path if any(path.is_relative_to(root) for root in allowed) else None
        except (OSError, ValueError):
            return None

    def refresh(self):
        for call in self.calls.values():
            for path in call['outputs']:
                try:
                    stat = path.stat()
                    signature = (stat.st_size, stat.st_mtime_ns)
                    if signature == call['signature'].get(path) or stat.st_mtime < call['at'] - 2:
                        continue
                    with path.open('rb') as source:
                        header = source.read(16384).decode('utf-8', errors='replace')
                    # Only thread.started from redirected --json output is evidence.
                    for line in header.splitlines()[:16]:
                        try:
                            record = json.loads(line)
                        except ValueError:
                            continue
                        for thread in result_threads(record):
                            self.links[thread] = max(call['at'], self.links.get(thread, 0))
                    call['signature'][path] = signature
                except (OSError, ValueError):
                    continue
        if len(self.links) > 128:
            self.links = dict(sorted(self.links.items(), key=lambda item: item[1], reverse=True)[:128])


def connect_delegations(states, tails):
    """Native parents win; conflicting simultaneous callers never produce a guess."""
    by_thread = {}
    for state in states:
        by_thread.setdefault((state['provider'], state['session_id']), []).append(state)
    claims = {}
    for parent in states:
        tail = tails.get(parent['id'])
        if parent['provider'] != 'Claude' or tail is None:
            continue
        for thread, at in tail.delegations.links.items():
            claims.setdefault(thread, []).append((at, parent['id']))
    for thread, candidates in claims.items():
        latest = max(at for at, _ in candidates)
        owners = {owner for at, owner in candidates if at == latest}
        children = by_thread.get(('Codex', thread), [])
        if len(owners) != 1 or len(children) != 1:
            continue
        child = children[0]
        if child.get('parent_id') or child.get('parent_session_id'):
            continue
        child['parent_id'] = owners.pop()
        child['parent_provider'] = 'Claude'
        child['subagent'] = True
