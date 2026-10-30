"""Quiet local lifecycle notifier. No agent output, decisions or network calls."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

EVENTS = {'PreCompact': 'start', 'PostCompact': 'end', 'Interrupt': 'cancel',
          'Stop': 'cancel', 'StopFailure': 'cancel', 'SessionEnd': 'cancel'}
EVENT_DIR = Path(__file__).resolve().parent / 'runtime' / 'compaction'


def publish(provider, payload, directory=EVENT_DIR):
    if provider not in ('Claude', 'Codex') or not isinstance(payload, dict):
        return None
    event = payload.get('hook_event_name')
    session = payload.get('session_id')
    if event not in EVENTS or not isinstance(session, str) or not session:
        return None
    # Transcript identity disambiguates subagents whose hook session_id is the parent.
    transcript = payload.get('transcript_path') or ''
    agent = payload.get('agent_id') or ''
    if not isinstance(transcript, str) or not isinstance(agent, str):
        return None
    key = hashlib.sha256((provider + '\0' + session + '\0' + transcript + '\0' + agent).encode()).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (key + '.json')
    # Normal turn endings don't create files unless this session has compacted.
    if EVENTS[event] == 'cancel' and not destination.exists():
        return None
    record = dict(provider=provider, session_id=session, transcript_path=transcript,
                  agent_id=agent, phase=EVENTS[event], at=time.time(), event=event)
    temp = directory / (key + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(record, ensure_ascii=True), encoding='utf-8')
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return record


def main():
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        # PostCompact can include a large summary. Parse it, but never save it.
        payload = json.load(sys.stdin)
        publish(sys.argv[1], payload)
    except Exception:
        # Observation must never interrupt the actual agent operation.
        pass


if __name__ == '__main__':
    main()
