import json
import tempfile
import time
import unittest
from pathlib import Path
from monitor import Tail, Monitor, transition, activity_hint, reset_timestamp, wake_message
from datetime import datetime, timezone, timedelta

class MonitorTests(unittest.TestCase):
    def test_one_hour_idle_and_recovery(self):
        t=Tail(Path('test'),'Codex'); t.updated=1000
        for state in ('working','thinking','done','paused','error','unknown'):
            t.state=state
            self.assertNotEqual(t.snapshot(4599)['state'],'idle')
            self.assertEqual(t.snapshot(4600)['state'],'idle')
        for state in ('quota_limited','rate_limited'):
            t.state=state
            self.assertEqual(t.snapshot(4600)['state'],state)
        t.state='working'; t.updated=4601
        self.assertEqual(t.snapshot(4602)['state'],'working')

    def test_activity_is_tool_derived(self):
        self.assertEqual(activity_hint('Claude',{'type':'assistant','message':{'content':[{'type':'tool_use','name':'Bash','input':{'command':'python -m pytest'}}]}}),'테스트 실행 중\npython -m pytest')
        self.assertEqual(activity_hint('Codex',{'type':'response_item','payload':{'type':'custom_tool_call','name':'apply_patch','input':'*** Update File: src/office.py\nprivate content'}}),'파일 수정 중\noffice.py')
        self.assertEqual(activity_hint('Claude',{'type':'user','message':{'content':'pytest private prompt'}}),'')

    def test_activity_detail_survives_results_and_reasoning(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'session.jsonl'
            events=[{'type':'response_item','payload':{'type':'custom_tool_call','name':'apply_patch','input':'*** Update File: src/office.py\ncontent'}}, {'type':'response_item','payload':{'type':'custom_tool_call_output','output':'ok'}}, {'type':'response_item','payload':{'type':'reasoning','summary':[{'text':'not for display'}]}}]
            p.write_text(''.join(json.dumps(e)+'\n' for e in events))
            t=Tail(p,'Codex');t.read()
            self.assertEqual(t.activity,'파일 수정 중\noffice.py')
            with p.open('a') as f:f.write(json.dumps({'type':'response_item','payload':{'type':'message','role':'assistant','phase':'commentary','content':[{'type':'output_text','text':'Hover 동작을 확인하고 있어요.'}]}})+'\n')
            t.read();self.assertEqual(t.activity,'Hover 동작을 확인하고 있어요.')

    def test_nested_tool_description(self):
        e={'type':'response_item','payload':{'type':'function_call','name':'functions.exec','arguments':json.dumps({'code':'await tools.exec_command({"cmd":"python -m pytest test_hover.py", "description":"말풍선 hover 검증"})'})}}
        self.assertIn('말풍선 hover 검증',activity_hint('Codex',e))
        e={'type':'response_item','payload':{'type':'custom_tool_call','name':'exec','input':'await tools.mcp__node_repl__js({code:"inspect()",title:"실제 화면 확인"})'}}
        self.assertIn('실제 화면 확인',activity_hint('Codex',e))

    def test_wake_clock_rollover_and_expired_hint(self):
        tz=timezone(timedelta(hours=9))
        recorded=datetime(2026,10,30,23,50,tzinfo=tz).timestamp()
        hint='기록의 해제 안내: 12:10am (Asia/Seoul)'
        expected=datetime(2026,10,31,0,10,tzinfo=tz).timestamp()
        self.assertEqual(reset_timestamp(hint,recorded),expected)
        s={'state':'quota_limited','updated':recorded,'reset_hint':hint}
        self.assertIn('20분',wake_message(s,recorded))
        self.assertIn('안내 시각 지남',wake_message(s,expected+1))
        self.assertIn('재개 시간 미정',wake_message({'state':'paused'},recorded))
        self.assertIsNone(reset_timestamp('tomorrow afternoon',recorded))

    def test_quota_is_distinct_from_rate_limit(self):
        self.assertEqual(transition('Claude', {'type':'assistant','isApiErrorMessage':True,'apiError':'usage_limit_reached','error':'rate_limit','apiErrorStatus':429}), 'quota_limited')
        self.assertEqual(transition('Claude', {'type':'assistant','isApiErrorMessage':True,'apiErrorStatus':429}), 'rate_limited')
        self.assertEqual(transition('Codex', {'type':'turn.failed','error':{'code':'usage_limit_exceeded'}}), 'quota_limited')
        self.assertEqual(transition('Codex', {'type':'event_msg','payload':{'type':'error','codex_error_info':'UsageLimitExceeded'}}), 'quota_limited')
        self.assertEqual(transition('Codex', {'type':'error','message':'connection lost'}), 'error')

    def test_interruption_and_no_dialogue_false_positive(self):
        self.assertEqual(transition('Codex', {'type':'event_msg','payload':{'type':'turn_aborted'}}),'paused')
        self.assertEqual(transition('Claude', {'type':'user','message':{'content':'[Request interrupted by user]'}}),'paused')
        self.assertEqual(transition('Claude', {'type':'user','message':{'content':'Explain usage_limit_reached and rate_limit'}}),'thinking')
        self.assertIsNone(transition('Codex', {'type':'event_msg','payload':{'type':'token_count','rate_limits':{'used_percent':100}}}))

    def test_limit_persists_through_bookkeeping_and_wakes_on_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'session.jsonl'
            events=[{'type':'assistant','isApiErrorMessage':True,'apiError':'usage_limit_reached','message':{'content':[{'type':'text','text':"You've hit your session limit - resets 3:50pm (Asia/Seoul)"}]}}, {'type':'system','subtype':'turn_duration'}]
            p.write_text(''.join(json.dumps(e)+'\n' for e in events))
            t=Tail(p,'Claude'); t.read()
            self.assertEqual(t.state,'quota_limited')
            self.assertIn('3:50pm',t.snapshot(time.time())['reset_hint'])
            self.assertEqual(t.snapshot(time.time()+10000)['state'],'quota_limited')
            with p.open('a') as f: f.write(json.dumps({'type':'user','message':{'content':'continue'}})+'\n')
            t.read(); self.assertEqual(t.state,'thinking'); self.assertEqual(t.reset,'')

    def test_codex_completion_is_explicit(self):
        self.assertEqual(transition('Codex', {'type':'event_msg','payload':{'type':'task_complete'}}),'done')
        self.assertIsNone(transition('Codex', {'type':'event_msg','payload':{'type':'token_count'}}))
        self.assertEqual(transition('Codex', {'type':'response_item','payload':{'type':'function_call'}}),'working')

    def test_claude_stop_and_error(self):
        self.assertEqual(transition('Claude', {'type':'assistant','message':{'stop_reason':'end_turn'}}),'done')
        self.assertEqual(transition('Claude', {'type':'assistant','isApiErrorMessage':True,'message':{'stop_reason':'stop_sequence'}}),'error')

    def test_partial_lines_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'session.jsonl'
            data=json.dumps({'type':'turn.completed'}).encode()
            p.write_bytes(data[:12])
            t=Tail(p,'Codex'); t.read()
            self.assertEqual(t.state,'unknown')
            with p.open('ab') as f: f.write(data[12:]+b'\n')
            t.read(); self.assertEqual(t.state,'done')
            p.write_bytes(b'{"type":"error"}\n')
            t.read(); self.assertEqual(t.state,'error')

    def test_silence_never_means_done(self):
        t=Tail(Path('test'),'Codex'); t.state='working'; t.updated=time.time()-181
        self.assertEqual(t.snapshot(time.time())['state'],'unknown')
        t.state='done'
        self.assertEqual(t.snapshot(time.time())['state'],'done')

    def test_subagents_and_missing_roots(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); sub=root/'subagents'; sub.mkdir()
            (sub/'agent-a.jsonl').write_text(json.dumps({'type':'assistant','message':{'stop_reason':'tool_use'}})+'\n')
            m=Monitor({'Claude':root,'Codex':root/'missing'})
            rows=m.scan()
            self.assertEqual(len(rows),1)
            self.assertTrue(rows[0]['subagent'])
            self.assertEqual(rows[0]['state'],'working')
            self.assertTrue(m.errors)

if __name__ == '__main__': unittest.main()
