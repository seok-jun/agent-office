import json
import tempfile
import unittest
from pathlib import Path
from attention import Attention
from monitor import Tail

class AttentionTests(unittest.TestCase):
    def test_claude_question_matching_reply(self):
        a=Attention()
        a.consume('Claude',{'type':'assistant','message':{'content':[{'type':'tool_use','id':'q1','name':'AskUserQuestion','input':{'questions':[{'question':'어떤 색으로 할까요?'}]}}]}})
        self.assertEqual(a.current()['state'],'needs_answer')
        self.assertEqual(a.current()['hint'],'어떤 색으로 할까요?')
        a.consume('Claude',{'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'other','content':'ok'}]}})
        self.assertIsNotNone(a.current())
        self.assertTrue(a.consume('Claude',{'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'q1','content':'blue'}]}}))
        self.assertIsNone(a.current())

    def test_async_ack_keeps_question_pending(self):
        a=Attention()
        a.consume('Codex',{'type':'response_item','payload':{'type':'function_call','name':'request_user_input_async','call_id':'q','arguments':json.dumps({'questions':[{'title':'선택해 주세요'}]})}})
        a.consume('Codex',{'type':'response_item','payload':{'type':'function_call_output','call_id':'q','output':'{"accepted":true}'}})
        self.assertEqual(a.current()['state'],'needs_answer')
        a.consume('Codex',{'type':'event_msg','payload':{'type':'task_complete'}})
        self.assertIsNotNone(a.current())
        a.consume('Codex',{'type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':'<send_user_message_question_reply>answer</send_user_message_question_reply>'}]}})
        self.assertIsNone(a.current())

    def test_approval_resolution_and_no_escalation_guess(self):
        a=Attention()
        a.consume('Codex',{'id':123,'method':'item/commandExecution/requestApproval','params':{'reason':'테스트를 실행할까요?'}})
        self.assertEqual(a.current()['state'],'needs_approval')
        a.consume('Codex',{'method':'serverRequest/resolved','params':{'requestId':123}})
        self.assertIsNone(a.current())
        a.consume('Codex',{'type':'response_item','payload':{'type':'function_call','name':'exec_command','arguments':'{"sandbox_permissions":"require_escalated"}'}})
        self.assertIsNone(a.current())

    def test_no_prose_detection_and_cancel_clears(self):
        a=Attention()
        a.consume('Claude',{'type':'assistant','message':{'content':[{'type':'text','text':'질문일까요? 승인해 주세요?'}]}})
        self.assertIsNone(a.current())
        a.consume('Codex',{'id':'a','method':'item/fileChange/requestApproval','params':{}})
        a.consume('Codex',{'type':'event_msg','payload':{'type':'turn_aborted'}})
        self.assertIsNone(a.current())

    def test_pending_survives_timeout_and_unrelated_work(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'s.jsonl'
            records=[{'type':'assistant','message':{'content':[{'type':'tool_use','id':'q','name':'AskUserQuestion','input':{'questions':[{'question':'계속할까요?'}]}}]}}, {'type':'api-request'}]
            path.write_text(''.join(json.dumps(e)+'\n' for e in records))
            t=Tail(path,'Claude');t.read()
            self.assertEqual(t.snapshot(t.updated+7200)['state'],'needs_answer')
            with path.open('a') as f:f.write(json.dumps({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'q','content':'yes'}]}})+'\n')
            t.read();self.assertEqual(t.snapshot(t.updated)['state'],'thinking')
