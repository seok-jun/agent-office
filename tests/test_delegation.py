import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from delegation import Delegations, codex_invocations, connect_delegations
from monitor import Monitor, Tail
from team import selected_team, visible_sessions


CHILD = '11111111-2222-3333-4444-555555555555'
OTHER = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


def call(command, at, call_id='call-1', session='claude-parent', cwd=None):
    return {'type': 'assistant', 'timestamp': at, 'sessionId': session, 'cwd': cwd,
            'message': {'content': [{'type': 'tool_use', 'id': call_id, 'name': 'Bash',
                                     'input': {'command': command}}]}}


def result(content, at, call_id='call-1'):
    return {'type': 'user', 'timestamp': at, 'sessionId': 'claude-parent',
            'message': {'content': [{'type': 'tool_result', 'tool_use_id': call_id,
                                     'content': content}]}}


class DelegationTests(unittest.TestCase):
    def test_only_executable_calls_not_help_prompts_comments_or_heredocs(self):
        for command in (f'echo codex exec resume {CHILD}',
                        f"printf '%s' 'codex exec resume {CHILD}'",
                        f'# codex exec resume {CHILD}',
                        f"cat <<'EOF'\ncodex exec resume {CHILD}\nEOF\necho done",
                        'codex exec --help', 'codex exec resume --help'):
            self.assertEqual(codex_invocations(command), [], command)
        command = f"cat <<'EOF'\ncodex exec resume {OTHER}\nEOF\ncodex exec resume {CHILD} --json"
        self.assertEqual([c['thread'] for c in codex_invocations(command)], [CHILD])
        self.assertEqual(codex_invocations(f'codex exec "codex exec resume {CHILD}"')[0]['thread'], None)

    def test_exact_resume_id_and_quoted_windows_executable(self):
        command = f"& 'C:\\tools with spaces\\codex.exe' exec resume '{CHILD}' --json"
        self.assertEqual(codex_invocations(command)[0]['thread'], CHILD)
        self.assertEqual(codex_invocations('codex exec resume "$TID"')[0]['thread'], None)

    def test_result_must_match_a_real_invocation(self):
        links = Delegations(Path('transcript.jsonl'))
        protocol = json.dumps({'type': 'thread.started', 'thread_id': CHILD})
        links.consume(result(protocol, 101), 101)
        self.assertFalse(links.links)
        links.consume(call('codex exec --json -', 100), 100)
        links.consume(result(f'User mentioned thread_id {OTHER}', 101), 101)
        links.consume(result(protocol, 101, 'unrelated'), 101)
        self.assertFalse(links.links)
        links.consume(result([{'type': 'text', 'text': protocol}], 102), 102)
        self.assertEqual(links.links, {CHILD: 100})

    def test_redirected_json_header_and_late_creation_without_reading_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            links = Delegations(root/'claude.jsonl')
            header = root/'events.jsonl'
            secret = root/'prompt.md'
            secret.write_text('This input must not be treated as link evidence.')
            at = time.time()
            command = f'S="{root.as_posix()}"; codex exec --json -o "$S/final.md" - < "$S/prompt.md" > "$S/events.jsonl" 2> "$S/errors.jsonl"'
            links.consume(call(command, at), at)
            self.assertEqual(links.calls['call-1']['outputs'], [header])
            links.refresh()
            self.assertFalse(links.links)
            header.write_text(json.dumps({'type': 'thread.started', 'thread_id': CHILD})+'\n')
            links.refresh()
            self.assertEqual(links.links, {CHILD: at})
            # A later record creates no link from UUIDs inside model output.
            header.write_text(json.dumps({'type': 'item.completed', 'item': {'text': OTHER}})+'\n')
            links.refresh()
            self.assertNotIn(OTHER, links.links)

    def test_output_path_scope_and_stale_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            links = Delegations(root/'claude.jsonl')
            for raw in ('relative.jsonl', '//server/share/file.jsonl', str(root/'prompt.md')):
                self.assertIsNone(links.output_path(raw, str(root)))
            self.assertIsNone(links.output_path(str(Path.home()/'unrelated-private.jsonl'), None))
            header = root/'stale.jsonl'
            header.write_text(json.dumps({'type': 'thread.started', 'thread_id': CHILD})+'\n')
            os.utime(header, (100, 100))
            links.consume(call(f'codex exec --json > "{header.as_posix()}"', 200), 200)
            links.refresh()
            self.assertFalse(links.links)

    def test_claude_launch_in_older_history_links_live_codex_and_resets_on_truncate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claude = root/'claude'; claude.mkdir()
            codex = root/'codex'; codex.mkdir()
            parent = claude/'parent.jsonl'
            child = codex/'codex.jsonl'
            stamp = '2026-10-31T06:00:00Z'
            command = call(f'codex exec resume {CHILD} --json', stamp)
            filler = {'type':'system', 'message':{'content':'x'*600000}}
            parent.write_text(json.dumps(command)+'\n'+json.dumps(filler)+'\n')
            child.write_text(json.dumps({'type':'session_meta','payload':{'id':CHILD,'source':'exec'}})+'\n')
            monitor = Monitor({'Claude':claude,'Codex':codex})
            rows = monitor.scan()
            by_provider = {s['provider']:s for s in rows}
            self.assertEqual(by_provider['Codex']['parent_id'], str(parent))
            self.assertTrue(by_provider['Codex']['subagent'])
            self.assertEqual(selected_team(rows,str(child)),(str(parent),{str(parent),str(child)}))
            parent.write_text(json.dumps({'type':'user','sessionId':'claude-parent','message':{'content':'new session'}})+'\n')
            rows = monitor.scan()
            self.assertIsNone(next(s for s in rows if s['provider']=='Codex')['parent_id'])

    def test_latest_caller_wins_ambiguous_calls_and_native_parents_are_preserved(self):
        tails = {key:Tail(Path(key),'Claude') for key in ('one','two')}
        states = [{'id':key,'provider':'Claude','session_id':key} for key in tails]
        child = {'id':'child','provider':'Codex','session_id':CHILD,'parent_id':None}
        states.append(child)
        tails['one'].delegations.links[CHILD] = 100
        tails['two'].delegations.links[CHILD] = 100
        connect_delegations(states,tails)
        self.assertIsNone(child['parent_id'])
        tails['two'].delegations.links[CHILD] = 101
        connect_delegations(states,tails)
        self.assertEqual(child['parent_id'],'two')
        child['parent_id']='native-codex-parent'
        connect_delegations(states,tails)
        self.assertEqual(child['parent_id'],'native-codex-parent')

    def test_matching_project_or_time_without_explicit_evidence_never_links(self):
        tails = {'one':Tail(Path('one'),'Claude')}
        states = [{'id':'one','provider':'Claude','session_id':'one','project':'same','updated':100},
                  {'id':'child','provider':'Codex','session_id':CHILD,'project':'same','updated':100,'parent_id':None}]
        connect_delegations(states,tails)
        self.assertIsNone(states[1]['parent_id'])

    def test_visible_limit_keeps_parent_and_grandparent_with_active_child(self):
        states = [{'id':'child','parent_id':'parent'}] + [{'id':str(i)} for i in range(20)] + [
            {'id':'parent','parent_id':'root'},{'id':'root'}]
        selected = visible_sessions(states)
        self.assertEqual(len(selected),12)
        self.assertTrue({'child','parent','root'}.issubset({s['id'] for s in selected}))
        self.assertEqual(selected_team(selected,'child'),('root',{'child','parent','root'}))


if __name__ == '__main__':
    unittest.main()
