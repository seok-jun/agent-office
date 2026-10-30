import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from compaction_hook import publish
from live_compaction import LiveCompaction
from install_hooks import merge_config, install
from monitor import Monitor


class LiveCompactionTests(unittest.TestCase):
    def test_both_providers_start_end_cancel_and_no_private_content(self):
        for provider in ('Claude', 'Codex'):
            with self.subTest(provider=provider), tempfile.TemporaryDirectory() as d:
                reader=LiveCompaction(d)
                states=[dict(id=str(Path(d)/'session.jsonl'),provider=provider,
                             session_id='session',state='working',updated=90)]
                payload=dict(session_id='session',transcript_path=states[0]['id'],
                             custom_instructions='PRIVATE',compact_summary='PRIVATE')
                for event,expected in [('PreCompact','compacting'),('PostCompact','working'),
                                       ('PreCompact','compacting'),('Interrupt','working')]:
                    with patch('compaction_hook.time.time',return_value=100):
                        publish(provider,dict(payload,hook_event_name=event),d)
                    self.assertEqual(reader.apply(states,101)[0]['state'],expected)
                self.assertNotIn('PRIVATE',next(Path(d).glob('*.json')).read_text())
                self.assertEqual(states[0]['state'],'working')

    def test_lost_end_recovers_from_transcript_and_stale_hook_expires(self):
        with tempfile.TemporaryDirectory() as d:
            reader=LiveCompaction(d)
            with patch('compaction_hook.time.time',return_value=100):
                publish('Claude',dict(session_id='s',hook_event_name='PreCompact'),d)
            s=dict(id='unused',provider='Claude',session_id='s',state='thinking',updated=90)
            self.assertEqual(reader.apply([s],101)[0]['state'],'compacting')
            self.assertEqual(reader.apply([dict(s,compacted_at=101)],102)[0]['state'],'thinking')
            self.assertEqual(reader.apply([dict(s,state='error',updated=101)],102)[0]['state'],'error')
            self.assertEqual(reader.apply([s],2000)[0]['state'],'thinking')

    def test_subagent_transcript_wins_over_parent_session_id(self):
        with tempfile.TemporaryDirectory() as d:
            reader=LiveCompaction(d)
            states=[dict(id=str(Path(d)/name),provider='Codex',session_id=sid,
                         state='working',updated=90) for name,sid in [('p.jsonl','parent'),('c.jsonl','child')]]
            with patch('compaction_hook.time.time',return_value=100):
                publish('Codex',dict(session_id='parent',transcript_path=states[1]['id'],hook_event_name='PreCompact'),d)
            result=reader.apply(states,101)
            self.assertEqual([s['state'] for s in result],['working','compacting'])
            self.assertEqual(reader.apply(states[:1],101)[0]['state'],'working')

    def test_monitor_receives_hooks_without_rescanning_transcript(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); logs=root/'logs';logs.mkdir();events=root/'events'
            p=logs/'session.jsonl'
            p.write_text(json.dumps(dict(type='session_meta',payload={'id':'s'}))+'\n')
            monitor=Monitor({'Codex':logs});monitor.compaction=LiveCompaction(events)
            monitor.scan()
            payload=dict(session_id='s',transcript_path=str(p))
            publish('Codex',dict(payload,hook_event_name='PreCompact'),events)
            self.assertEqual(monitor.snapshot()[0]['state'],'compacting')
            publish('Codex',dict(payload,hook_event_name='PostCompact'),events)
            self.assertNotEqual(monitor.snapshot()[0]['state'],'compacting')

    def test_existing_settings_preserved_and_install_is_idempotent(self):
        original={'permissions':{'allow':['Read']},'hooks':{'PreCompact':[{'hooks':[{'type':'command','command':'existing'}]}]}}
        for provider in ('Claude','Codex'):
            merged=merge_config(original,provider)
            self.assertEqual(merged['permissions'],original['permissions'])
            self.assertEqual(merged['hooks']['PreCompact'][0],original['hooks']['PreCompact'][0])
            self.assertEqual(merge_config(merged,provider),merged)
            self.assertEqual(len(original['hooks']['PreCompact']),1)

    def test_malformed_event_does_not_break_monitor(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{')
            reader=LiveCompaction(d)
            self.assertEqual(reader.apply([]),[])
            p.write_text('[]')
            self.assertEqual(reader.apply([]),[])


if __name__=='__main__':unittest.main()
