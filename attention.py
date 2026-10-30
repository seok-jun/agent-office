"""Correlate explicit requests and replies, not prose/question-mark heuristics."""
import json

NEEDS_INPUT = {'needs_answer', 'needs_approval'}
QUESTION_TOOLS = {'AskUserQuestion', 'request_user_input', 'request_user_input_async'}
APPROVAL_TOOLS = {'ExitPlanMode', 'request_permissions'}
APPROVAL_EVENTS = {'exec_approval_request','apply_patch_approval_request','permission_request',
                   'item/commandExecution/requestApproval','item/fileChange/requestApproval',
                   'item/permissions/requestApproval'}

def obj(value):
    if isinstance(value,dict): return value
    if isinstance(value,str):
        try:
            decoded=json.loads(value)
            return decoded if isinstance(decoded,dict) else {}
        except ValueError: pass
    return {}

class Attention:
    def __init__(self):
        self.pending={}

    def add(self,key,kind,args,asynchronous=False):
        questions=args.get('questions',[])
        first=questions[0] if isinstance(questions,list) and questions and isinstance(questions[0],dict) else {}
        hint=first.get('question') or first.get('title') or args.get('reason') or args.get('message') or args.get('justification') or ''
        self.pending[str(key)]={'state':kind,'hint':str(hint),'async':asynchronous}

    def finish(self,key,value):
        key=str(key)
        if key not in self.pending:return
        result=obj(value)
        # Asynchronous submission acknowledgment is NOT a user answer.
        if self.pending[key]['async'] and result.get('accepted') is True and not result.get('answers'):
            return
        self.pending.pop(key,None)

    def consume(self,provider,event):
        p=obj(event.get('payload'))
        kind=p.get('type') if event.get('type')=='event_msg' else event.get('type')
        method=event.get('method') or kind
        params=obj(event.get('params')) or p or event
        before=bool(self.pending)
        if method in ('turn_aborted','turn.aborted','turn.cancelled','session_end'):
            self.pending.clear()
        if method in APPROVAL_EVENTS or method in ('item/tool/requestUserInput','tool/requestUserInput','mcpServer/elicitation/request'):
            approval=method in APPROVAL_EVENTS
            self.add(event.get('id',params.get('requestId',params.get('call_id',params.get('id',method)))), 'needs_approval' if approval else 'needs_answer', params)
        if method=='serverRequest/resolved':
            self.pending.pop(str(params.get('requestId')),None)
        if method in ('exec_approval_response','apply_patch_approval_response','permission_response'):
            self.pending.pop(str(params.get('request_id',params.get('call_id',params.get('id')))),None)
        if provider=='Codex' and event.get('type')=='response_item':
            if p.get('type') in ('function_call','custom_tool_call'):
                name=p.get('name','').split('.')[-1]
                args=obj(p.get('arguments',p.get('input')))
                if name in QUESTION_TOOLS | APPROVAL_TOOLS:
                    self.add(p.get('call_id',name),'needs_answer' if name in QUESTION_TOOLS else 'needs_approval',args,name=='request_user_input_async')
            elif p.get('type') in ('function_call_output','custom_tool_call_output'):
                self.finish(p.get('call_id'),p.get('output'))
            elif p.get('type')=='message' and p.get('role')=='user':
                text=' '.join(b.get('text','') for b in p.get('content',[]) if isinstance(b,dict))
                if '<send_user_message_question_reply>' in text:
                    self.pending={k:v for k,v in self.pending.items() if v['state']!='needs_answer'}
        if provider=='Claude':
            message=obj(event.get('message'))
            content=message.get('content',[])
            if isinstance(content,list):
                for block in content:
                    if not isinstance(block,dict):continue
                    name=block.get('name','')
                    if event.get('type')=='assistant' and block.get('type')=='tool_use' and name in QUESTION_TOOLS | APPROVAL_TOOLS:
                        self.add(block.get('id',name),'needs_answer' if name in QUESTION_TOOLS else 'needs_approval',obj(block.get('input')))
                    elif event.get('type')=='user' and block.get('type')=='tool_result':
                        self.finish(block.get('tool_use_id'),block.get('content'))
        return before and not self.pending

    def current(self):
        if not self.pending:return None
        # Approval blocks execution; show it before other open questions.
        return next((v for v in self.pending.values() if v['state']=='needs_approval'),next(iter(self.pending.values())))
