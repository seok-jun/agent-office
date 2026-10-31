"""Read-only, bounded local transcript observer. No prompt content leaves this process."""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from attention import Attention, NEEDS_INPUT
from live_compaction import LiveCompaction
from delegation import Delegations, connect_delegations
from team import visible_sessions

LABELS = {'working': '작업 중', 'thinking': '생각 중', 'done': '완료', 'waiting': '승인 대기', 'unknown': '상태 미확인', 'error': '오류'}
LABELS.update(paused='중단 · 쉬는 중', quota_limited='사용량 제한 · 쉬는 중', rate_limited='요청 속도 제한 · 대기')
LABELS['idle'] = '대기 · 1시간 활동 없음'
LABELS.update(needs_answer='답변 기다리는 중', needs_approval='승인 기다리는 중')
LABELS['compacting'] = '컨텍스트 압축 중'
RESTING = {'paused', 'quota_limited', 'rate_limited'}

def activity_category(provider, event):
    """Short tool-derived labels; no prompts, command lines or reasoning are displayed."""
    p=event.get('payload') or {}
    if not isinstance(p,dict): return ''
    name=''; args={}
    if provider=='Codex' and event.get('type')=='response_item':
        if p.get('type') in ('function_call_output','custom_tool_call_output'): return '실행 결과 확인 중'
        if p.get('type') in ('function_call','custom_tool_call'):
            name=p.get('name',''); args=p.get('arguments',p.get('input',{}))
        elif p.get('type')=='reasoning': return '다음 작업 검토 중'
    elif provider=='Claude' and event.get('type')=='assistant':
        msg=event.get('message') or {}
        if not isinstance(msg,dict): return ''
        for block in msg.get('content',[]) if isinstance(msg.get('content'),list) else []:
            if isinstance(block,dict) and block.get('type')=='tool_use':
                name=block.get('name',''); args=block.get('input',{})
    if not name: return ''
    raw=(name+' '+json.dumps(args,ensure_ascii=False)).lower()
    tool=name.lower()
    if any(k in tool for k in ('edit','write','patch')) or 'apply_patch' in raw: return '파일 수정 중'
    if re.search(r'\b(pytest|unittest|jest|vitest)\b|npm (run )?test',raw): return '테스트 실행 중'
    if any(k in tool for k in ('web','search','browse')): return '자료 검색 중'
    if any(k in tool for k in ('read','glob','grep')) or re.search(r'get-content|\brg\b|\bcat\b',raw): return '코드 살펴보는 중'
    if any(k in tool for k in ('agent','task','delegate')): return '서브 에이전트 협업 중'
    if any(k in tool for k in ('plan','todo')): return '작업 계획 정리 중'
    if 'git ' in raw: return '변경 사항 확인 중'
    if any(k in tool for k in ('exec','bash','shell','terminal')): return '명령 실행 중'
    return '도구로 작업 중'

def short_text(value, limit=64):
    text=re.sub(r'\s+', ' ', str(value or '')).strip()
    text=re.sub(r'(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*\S+', r'\1=[숨김]', text)
    text=re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_\-]{10,}', '[숨김]', text)
    return text if len(text)<=limit else text[:limit-1]+'…'


def activity_hint(provider, event):
    """Use actual tool targets/public progress; never display private reasoning blocks."""
    p=event.get('payload') or {}
    if not isinstance(p,dict): return ''
    name=''; args={}; progress=''
    if provider=='Codex':
        if event.get('type')=='response_item':
            if p.get('type')=='message' and p.get('role')=='assistant' and p.get('phase')=='commentary':
                progress=' '.join(b.get('text','') for b in p.get('content',[]) if isinstance(b,dict) and b.get('type') in ('output_text','text'))
            elif p.get('type') in ('function_call','custom_tool_call'):
                name=p.get('name',''); args=p.get('arguments',p.get('input',{}))
        elif event.get('type')=='event_msg' and p.get('type')=='agent_message' and p.get('phase')=='commentary':
            progress=p.get('message','')
    elif provider=='Claude' and event.get('type')=='assistant' and not event.get('isApiErrorMessage'):
        msg=event.get('message') or {}
        if not isinstance(msg,dict): return ''
        for b in msg.get('content',[]) if isinstance(msg.get('content'),list) else []:
            if not isinstance(b,dict): continue
            if b.get('type')=='tool_use': name=b.get('name',''); args=b.get('input',{})
            elif b.get('type')=='text': progress=b.get('text','')
    if not name: return short_text(progress,70) if progress else ''
    if isinstance(args,str):
        try: args=json.loads(args)
        except (ValueError,TypeError): args={'code':args}
    if not isinstance(args,dict): args={}
    raw=str(args.get('code',args.get('input','')))
    # Codex orchestrators carry nested tool arguments inside their JavaScript code.
    nested={}
    for key,value in re.findall(r'\b"?(cmd|command|title|description|file_path|path)"?\s*:\s*("(?:\\.|[^"\\])*")',raw):
        try: nested[key]=json.loads(value)
        except ValueError: pass
    data={**nested,**args}
    label=activity_category(provider,event) or '작업 진행 중'
    filename=data.get('file_path') or data.get('path') or data.get('notebook_path')
    patch=str(data.get('patch',raw))
    match=re.search(r'\*\*\* (?:Update|Add|Delete) File: ([^\r\n\\"]+)',patch)
    if match: filename=match[1]
    if filename and isinstance(filename,str):
        target=filename.replace('\\','/').rstrip('/').split('/')[-1]
        return label+'\n'+short_text(target,42)
    desc=data.get('description') or data.get('title')
    if desc: return label+'\n'+short_text(desc,55)
    command=data.get('command') or data.get('cmd')
    if isinstance(command,str):
        # Only show recognizable command + test/file target, never arbitrary arguments.
        known=re.search(r'(?i)\b(?:python(?:3)?\s+-m\s+(?:pytest|unittest)(?:\s+discover)?|npm\s+(?:run\s+)?(?:test|build|lint)|npx\s+(?:vitest|jest)|pytest|git\s+(?:diff|status|log)|rg|Get-Content)\b',command)
        if known:
            files=re.findall(r'[\w./\\-]+\.(?:py|tsx?|jsx?|json|md|yaml|yml|toml|css|html)\b',command)
            detail=known[0]+(' · '+files[0].replace('\\','/').split('/')[-1] if files else '')
        else:
            first=re.match(r'\s*([\w.\/-]+)',command)
            detail=first[1] if first else ''
        if not detail: return ''
        return label+'\n'+short_text(detail,48)
    query=data.get('query') or data.get('pattern')
    if isinstance(query,str): return label+'\n'+short_text(query,44)
    if name in ('exec','functions.exec'): return ''
    return label+'\n'+short_text(name,44)


def reset_timestamp(hint, recorded_at):
    # Parse only unambiguous daily-clock messages with a known timezone.
    value=hint.removeprefix('기록의 해제 안내: ').strip()
    match=re.fullmatch(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*\((Asia/Seoul|UTC)\)',value,re.I)
    if not match: return None
    hour,minute=int(match[1]),int(match[2] or 0)
    if not 1<=hour<=12 or not 0<=minute<60: return None
    hour=hour%12+(12 if match[3].lower()=='pm' else 0)
    tz=timezone(timedelta(hours=9 if match[4].lower()=='asia/seoul' else 0))
    recorded=datetime.fromtimestamp(recorded_at,tz)
    reset=recorded.replace(hour=hour,minute=minute,second=0,microsecond=0)
    if reset<recorded: reset+=timedelta(days=1)
    return reset.timestamp()

def wake_message(session, now=None):
    now=time.time() if now is None else now
    if session['state']=='paused': return 'Zzz · 재개 시간 미정\n새 작업이 오면 기상'
    hint=session.get('reset_hint','')
    reset=reset_timestamp(hint,session.get('updated',now)) if hint else None
    if reset is not None:
        label=datetime.fromtimestamp(reset,timezone(timedelta(hours=9))).strftime('%m/%d %H:%M')
        if now>=reset: return f'{label} 안내 시각 지남\n새 작업 기다리는 중'
        minutes=max(1,int((reset-now+59)//60))
        remain=f'{minutes//60}시간 {minutes%60}분' if minutes>=60 else f'{minutes}분'
        return f'{label} 해제 예정\n약 {remain} 후 · 한국 시간'
    if hint:
        value=hint.removeprefix('기록의 해제 안내: ')
        return '해제 안내 · '+value[:24]+'\n기록 기준 · 재개 대기'
    return 'Zzz · 재개 시간 미정\n해제 시각 기록 없음'

def error_state(provider, event):
    """Inspect error envelopes only; never classify ordinary dialogue by keywords."""
    p = event.get('payload') or {}
    if not isinstance(p, dict): return None
    eligible = (event.get('isApiErrorMessage') if provider == 'Claude' else
                event.get('type') in ('error', 'turn.failed') or
                (event.get('type') == 'event_msg' and p.get('type') in ('error', 'task_failed', 'turn_failed')))
    if not eligible: return None
    codes = []
    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ('code', 'type', 'apiError', 'error', 'status', 'apiErrorStatus', 'codex_error_info', 'message'):
                    if isinstance(value, (str,int)): codes.append(str(value).lower())
                    elif isinstance(value, dict): visit(value)
        elif isinstance(obj,str): codes.append(obj.lower())
    visit(event); visit(p)
    value=' '.join(codes)
    if any(code in value for code in ('usage_limit_reached', 'usage_limit_exceeded', 'insufficient_quota', 'quota_exceeded', 'usagelimitexceeded', 'usage limit', 'session limit')):
        return 'quota_limited'
    if any(code in value for code in ('rate_limit', 'ratelimit', 'too many requests', '429')):
        return 'rate_limited'
    return 'error'

def reset_hint(event):
    # Retain only the reset-time fragment from a system-generated API error.
    if not event.get('isApiErrorMessage'): return ''
    msg=event.get('message') or {}
    if not isinstance(msg,dict): return ''
    content=msg.get('content',[])
    if not isinstance(content,list): return ''
    for block in content:
        if isinstance(block,dict) and block.get('type')=='text':
            match=re.search(r'\bresets?\s+([^\r\n]{1,90})',block.get('text',''),re.I)
            if match: return '기록의 해제 안내: '+match.group(1)
    return ''

def compaction_finished(event):
    p=event.get('payload') or {}
    if not isinstance(p,dict): return False
    kind=p.get('type') if event.get('type')=='event_msg' else event.get('subtype',event.get('type'))
    return (kind in ('compacted','compact_boundary','context_compacted','compaction_completed','post_compact')
            or event.get('hook_event_name')=='PostCompact'
            or (event.get('type')=='response_item' and p.get('type')=='compaction'))

def transition(provider, event):
    kind = event.get('type')
    p = event.get('payload') or {}
    if not isinstance(p, dict): return None
    compact_kind=p.get('type') if kind=='event_msg' else event.get('subtype',kind)
    if compact_kind in ('context_compaction_started','compaction_started','pre_compact') or event.get('hook_event_name')=='PreCompact': return 'compacting'
    if compaction_finished(event): return 'thinking'
    error = error_state(provider, event)
    if error: return error
    if provider == 'Codex':
        if kind == 'event_msg':
            kind = p.get('type')
            if kind in ('task_started', 'user_message'): return 'thinking'
            if kind in ('task_complete', 'task_completed'): return 'done'
            if kind == 'turn_aborted': return 'paused'
            if kind == 'task_failed': return 'error'
        if kind == 'response_item':
            if p.get('type') in ('function_call', 'custom_tool_call'): return 'working'
            if p.get('type') in ('reasoning', 'function_call_output', 'custom_tool_call_output'): return 'thinking'
            if p.get('type') == 'message' and p.get('role') == 'user': return 'thinking'
        if kind == 'turn.started': return 'thinking'
        if kind in ('turn.aborted', 'turn.cancelled'): return 'paused'
        if kind == 'turn.completed': return 'done'
        if kind in ('turn.failed', 'error'): return 'error'
    else:
        msg = event.get('message') or {}
        if not isinstance(msg, dict): return None
        if kind == 'user':
            content = msg.get('content')
            if isinstance(content,str) and content in ('[Request interrupted by user]', '[Request interrupted by user for tool use]'):
                return 'paused'
            if isinstance(content,list) and any(isinstance(b,dict) and b.get('text') in ('[Request interrupted by user]', '[Request interrupted by user for tool use]') for b in content):
                return 'paused'
        if kind == 'assistant':
            if msg.get('stop_reason') in ('end_turn', 'stop_sequence'): return 'done'
            if msg.get('stop_reason') == 'tool_use': return 'working'
            return 'thinking'
        if kind in ('user', 'api-request'): return 'thinking'
        if kind == 'system' and event.get('subtype') == 'turn_duration': return 'done'
    return None

def timestamp(value, fallback):
    try: return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, AttributeError): return fallback

class Tail:
    def __init__(self, path, provider):
        self.path, self.provider = path, provider
        self.offset = 0
        self.pending = b''
        self.state = 'unknown'
        self.updated = 0
        self.project = ''
        self.subagent = 'subagents' in path.parts
        self.signature = None
        self.reset = ''
        self.activity = ''
        self.attention = Attention()
        self.session_id = path.stem
        self.parent_session_id = path.parent.parent.name if 'subagents' in path.parts else ''
        self.compacted_at = 0
        self.delegations = Delegations(path)

    def metadata(self,event):
        p=event.get('payload') or {}
        if not isinstance(p,dict):return
        if self.provider=='Codex' and event.get('type')=='session_meta':
            self.session_id=p.get('id',self.session_id)
            source=p.get('source') or {}
            sub=source.get('subagent',{}) if isinstance(source,dict) else {}
            spawn=sub.get('thread_spawn',{}) if isinstance(sub,dict) else {}
            if isinstance(spawn,dict):self.parent_session_id=spawn.get('parent_thread_id',self.parent_session_id)
        elif self.provider=='Claude':
            if self.subagent:self.session_id=event.get('agentId',self.session_id)
            else:self.session_id=event.get('sessionId',self.session_id)
            self.delegations.consume(event, timestamp(event.get('timestamp'), 0))

    def read(self):
        stat = self.path.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
        if signature == self.signature: return
        if stat.st_size < self.offset:
            self.offset = 0
            self.pending = b''
            self.state = 'unknown'
            self.reset = ''
            self.activity = ''
            self.attention = Attention()
            self.compacted_at = 0
            self.delegations = Delegations(self.path)
        with self.path.open('rb') as f:
            if self.offset == 0:
                # Metadata is at the head even when history is larger than the tail limit.
                # Rotated Codex rollouts put a large replacement-history compaction
                # directly after metadata. It may straddle the bounded tail window.
                for index, line in enumerate(f.read(4194304).splitlines()):
                    if index >= 8 and self.provider != 'Claude':
                        break
                    try:
                        meta = json.loads(line)
                        if isinstance(meta,dict):self.metadata(meta)
                        if index >= 8:
                            continue
                        if isinstance(meta,dict) and compaction_finished(meta):
                            self.compacted_at=timestamp(meta.get('timestamp'),stat.st_mtime)
                            self.state='thinking'
                            self.updated=self.compacted_at
                        if isinstance(meta, dict) and meta.get('type') == 'session_meta':
                            payload = meta.get('payload') or {}
                            if payload.get('cwd'): self.project = Path(payload['cwd']).name
                            source = payload.get('source', {})
                            self.subagent = isinstance(source, dict) and 'subagent' in source
                    except (ValueError, AttributeError, TypeError): continue
            # Only read the last 512 KiB on first discovery or a large jump.
            start = max(self.offset, stat.st_size - 524288)
            f.seek(start)
            if start > self.offset:
                f.readline()
                self.pending = b''
            data = self.pending + f.read(524288)
            self.offset = f.tell()
        lines = data.split(b'\n')
        self.pending = lines.pop()
        for line in lines:
            try: event = json.loads(line)
            except (ValueError, UnicodeDecodeError): continue
            if not isinstance(event, dict): continue
            self.metadata(event)
            p = event.get('payload') or {}
            if not isinstance(p, dict): continue
            if compaction_finished(event):
                self.compacted_at=timestamp(event.get('timestamp'),stat.st_mtime)
            cwd = event.get('cwd') or p.get('cwd')
            if cwd: self.project = Path(cwd).name
            if event.get('type') == 'session_meta':
                source = p.get('source', {})
                self.subagent = self.subagent or (isinstance(source, dict) and 'subagent' in source)
            resolved = self.attention.consume(self.provider,event)
            new = transition(self.provider, event)
            if resolved and new is None: new = 'thinking'
            activity = activity_hint(self.provider, event)
            fresh_turn = (event.get('type') == 'turn.started' or (event.get('type') == 'event_msg' and p.get('type') in ('task_started', 'user_message')))
            if self.provider == 'Claude' and event.get('type') == 'user':
                msg = event.get('message') or {}
                content = msg.get('content', []) if isinstance(msg, dict) else []
                fresh_turn = isinstance(content, str) or (isinstance(content, list) and any(isinstance(b, dict) and b.get('type') == 'text' for b in content) and not any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content))
            if fresh_turn: self.activity = ''
            if activity and new is None and self.state in ('working','thinking'):
                self.activity = activity
            if new:
                # A trailing duration/completion envelope is bookkeeping, not recovery.
                bookkeeping = (event.get('type') == 'system' or
                               (event.get('type') == 'event_msg' and p.get('type') in ('task_complete', 'task_completed')))
                if self.state in RESTING | {'error'} and new == 'done' and bookkeeping:
                    continue
                self.state = new
                self.reset = reset_hint(event) if new in ('quota_limited','rate_limited') else ''
                self.updated = timestamp(event.get('timestamp'), stat.st_mtime)
                if new in ('working','thinking'):
                    self.activity = activity or self.activity or ('요청 확인 중' if new=='thinking' else '작업 진행 중')
                else: self.activity = ''
        self.signature = signature

    def snapshot(self, now):
        state = self.state
        attention = self.attention.current()
        # Silence is ambiguous: never infer completion from a timeout.
        if self.updated and now - self.updated >= 3600 and state not in ('quota_limited', 'rate_limited'):
            state = 'idle'
        elif state in ('working', 'thinking', 'waiting','compacting') and now - self.updated > 180:
            state = 'unknown'
        if attention: state = attention['state']
        return dict(id=str(self.path), provider=self.provider, state=state,
                    updated=self.updated, project=self.project or '로컬 프로젝트',
                    subagent=self.subagent, short=self.path.stem[-6:], reset_hint=self.reset, activity=self.activity,
                    attention_hint=short_text(attention['hint'],70) if attention else '', pending_count=len(self.attention.pending),
                    session_id=self.session_id,parent_session_id=self.parent_session_id,compacted_at=self.compacted_at)

class Monitor:
    def __init__(self, roots=None):
        self.roots = roots or {
            'Codex': Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'sessions',
            'Claude': Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home()/'.claude'))/'projects'}
        self.tails = {}
        self.errors = []
        self.total = 0
        self.compaction = LiveCompaction()

    def scan(self):
        now = time.time()
        candidates = []
        self.errors = []
        for provider, root in self.roots.items():
            if not root.exists():
                self.errors.append(provider + ': 기록 폴더 없음')
                continue
            try:
                for path in root.rglob('*.jsonl'):
                    try:
                        modified = path.stat().st_mtime
                        if now - modified < 86400: candidates.append((modified, provider, path))
                    except OSError: continue
            except OSError:
                self.errors.append(provider + ': 기록 읽기 실패')
        candidates.sort(reverse=True)
        # Manual compaction can start on an old transcript before it is written again.
        known = {str(p) for _, _, p in candidates}
        for event in self.compaction.records(now):
            if event['phase'] != 'start' or not 0 <= now-event['at'] < 1800:
                continue
            path = Path(event.get('transcript_path') or '')
            root = self.roots.get(event['provider'])
            if root and path.is_absolute() and path.suffix == '.jsonl':
                try:
                    if path.resolve().is_relative_to(root.resolve()) and path.is_file() and str(path) not in known:
                        candidates.insert(0, (now, event['provider'], path))
                        known.add(str(path))
                except OSError: pass
        self.total = len(candidates)
        keep = set()
        for _, provider, path in candidates[:48]:
            key = str(path)
            keep.add(key)
            tail = self.tails.setdefault(key, Tail(path, provider))
            try: tail.read()
            except OSError: self.errors.append(provider + ': 세션 읽기 실패')
            if provider == 'Claude':
                tail.delegations.refresh()
        self.tails = {k: v for k, v in self.tails.items() if k in keep}
        return self.snapshot(now)

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        states = self.compaction.apply([v.snapshot(now) for v in self.tails.values()], now)
        lookup={(s['provider'],s['session_id']):s['id'] for s in states if not s['subagent']}
        lookup.update({(s['provider'],s['session_id']):s['id'] for s in states if s['subagent']})
        for s in states:s['parent_id']=lookup.get((s['provider'],s['parent_session_id']))
        connect_delegations(states, self.tails)
        states.sort(key=lambda v: (2 if v['state'] in NEEDS_INPUT else 1 if v['state'] in ('thinking', 'working','compacting') else 0, v['updated']), reverse=True)
        return visible_sessions(states)
