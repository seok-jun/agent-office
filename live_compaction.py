"""Merge local hook lifecycle signals with read-only session snapshots."""
import json
import os
from pathlib import Path
import time
from compaction_hook import EVENT_DIR


def path_key(value):
    return os.path.normcase(os.path.abspath(value)) if value else ''


class LiveCompaction:
    def __init__(self, directory=EVENT_DIR):
        self.directory = Path(directory)
        self.cache = {}
        self.last_received = {}

    def records(self, now):
        if not self.directory.exists():
            return []
        found = set()
        for path in self.directory.glob('*.json'):
            try:
                stat = path.stat()
                if now - stat.st_mtime > 86400:
                    continue
                found.add(path)
                signature = (stat.st_mtime_ns, stat.st_size)
                if path not in self.cache or self.cache[path][0] != signature:
                    if stat.st_size > 16384:
                        continue
                    record = json.loads(path.read_text(encoding='utf-8'))
                    if (record.get('provider') not in ('Codex', 'Claude') or
                            record.get('phase') not in ('start', 'end', 'cancel') or
                            not isinstance(record.get('at'), (int, float))):
                        continue
                    self.cache[path] = (signature, record)
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        self.cache = {p: v for p, v in self.cache.items() if p in found}
        return sorted((v[1] for v in self.cache.values()), key=lambda r: r['at'])

    def apply(self, states, now=None):
        now = time.time() if now is None else now
        states = [dict(s) for s in states]
        for record in self.records(now):
            provider = record['provider']
            at = record['at']
            if not 0 <= now - at < 1800:
                continue  # Abandoned compactions must not stick forever.
            self.last_received[provider] = max(at, self.last_received.get(provider, 0))
            transcript = path_key(record.get('transcript_path', ''))
            matches = [s for s in states if s['provider'] == provider and
                       (path_key(s['id']) == transcript if transcript else
                        s.get('session_id') == (record.get('agent_id') or record.get('session_id')))]
            if len(matches) != 1:
                continue  # Never send a parent's subagent to coffee by guessing.
            s = matches[0]
            # A recorded completion/cancellation also recovers a lost PostCompact hook.
            finished = s.get('compacted_at', 0) >= at
            interrupted = s['state'] in ('paused', 'quota_limited', 'rate_limited', 'error', 'done') and s.get('updated', 0) > at
            if record['phase'] == 'start' and not finished and not interrupted:
                if s['state'] not in ('needs_answer', 'needs_approval'):
                    s['state'] = 'compacting'
                    s['activity'] = '컨텍스트 압축 중'
                    s['updated'] = max(s.get('updated', 0), at)
            elif s['state'] == 'compacting':
                s['state'] = 'thinking' if record['phase'] != 'cancel' else 'unknown'
                s['activity'] = ''
        return states
