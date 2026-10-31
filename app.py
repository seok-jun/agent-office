"""Agent Office — a local desktop pixel office for Claude Code and Codex."""
import argparse
import math
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox
from monitor import Monitor, LABELS, RESTING
from attention import NEEDS_INPUT
from team import selected_team
from office import Office, identity, NAMES, ACCESSORIES

BG = '#111722'
PANEL = '#192231'
MUTED = '#8996ab'
INK = '#e9eee7'
MINT = '#93dfb1'
PEACH = '#edb18d'
COLORS = {'working': MINT, 'thinking': '#94bdf2', 'done': '#c8d58f', 'unknown': '#8996ab', 'error': '#ef9696', 'waiting': '#f1cd81'}

class AgentOffice(Office):
    def __init__(self, demo=False):
        self.root = tk.Tk()
        self.root.title('Agent Office · Claude & Codex')
        self.root.geometry(f'{min(1480,self.root.winfo_screenwidth()-70)}x{min(990,self.root.winfo_screenheight()-90)}')
        self.root.minsize(1120, 760)
        self.root.configure(bg=BG)
        self.demo = False
        self.waiting_collapsed = True
        self.closed = threading.Event()
        self.inbox = queue.Queue(maxsize=1)
        self.monitor = Monitor()
        self.live = []
        self.characters = {}
        self.selected = None
        self.team_root = None
        self.team_ids = set()
        self.pointer = None
        self.hover_row = None
        self.started = time.monotonic()
        self.last_scan = None
        self.last_error = ''
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill='x', padx=28, pady=(22, 14))
        tk.Label(header, text='Agent Office', font=('Consolas', 23, 'bold'), fg=INK, bg=BG).pack(side='left')
        self.toggle = self.button(header, '시연 보기', self.toggle_demo)
        self.toggle.pack(side='right')
        self.button(header, '안내', self.help).pack(side='right', padx=8)
        self.button(header, '펫 도감', self.pet_catalog).pack(side='right')
        self.button(header, 'Clawd 옷장', self.clawd_catalog).pack(side='right', padx=(0, 8))
        toolbar = tk.Frame(self.root, bg=BG)
        toolbar.pack(fill='x', padx=28, pady=(0, 13))
        self.mode = tk.Label(toolbar, text='●  LOCAL / LIVE', fg=MINT, bg=BG, font=('Consolas', 11, 'bold'))
        self.mode.pack(side='left')
        self.count = tk.Label(toolbar, fg=MUTED, bg=BG, font=('Malgun Gothic', 10))
        self.count.pack(side='left', padx=22)
        self.pin = tk.BooleanVar()
        tk.Checkbutton(toolbar, text='항상 위에', variable=self.pin, command=lambda: self.root.attributes('-topmost', self.pin.get()), fg=MUTED, bg=BG, selectcolor=PANEL, activebackground=BG, activeforeground=INK, font=('Malgun Gothic', 10)).pack(side='right')
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        self.canvas = tk.Canvas(body, bg='#252e39', highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Button-1>', self.select_character)
        self.canvas.bind('<Motion>', lambda e: setattr(self, 'pointer', (e.x, e.y)))
        self.canvas.bind('<Leave>', lambda e: setattr(self, 'pointer', None))
        sidebar = tk.Frame(body, bg=PANEL, width=260)
        sidebar.pack(side='right', fill='y', padx=(16, 0))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text='에이전트', font=('Malgun Gothic', 15, 'bold'), bg=PANEL, fg=INK).pack(anchor='w', padx=19, pady=(20, 5))
        self.detail = tk.Label(sidebar, text='', justify='left', wraplength=222, font=('Malgun Gothic', 9), fg=MUTED, bg=PANEL)
        self.detail.pack(side='bottom', fill='x', padx=18, pady=16)
        listbox = tk.Frame(sidebar, bg=PANEL)
        listbox.pack(fill='both', expand=True, padx=12, pady=10)
        self.list_canvas = tk.Canvas(listbox, bg=PANEL, highlightthickness=0)
        scrollbar = tk.Scrollbar(listbox, orient='vertical', command=self.list_canvas.yview)
        scrollbar.pack(side='right', fill='y')
        self.list_canvas.pack(side='left', fill='both', expand=True)
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        self.cards = tk.Frame(self.list_canvas, bg=PANEL)
        card_window = self.list_canvas.create_window(0, 0, window=self.cards, anchor='nw')
        self.cards.bind('<Configure>', lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all')))
        self.list_canvas.bind('<Configure>', lambda e: self.list_canvas.itemconfigure(card_window, width=e.width))
        self.root.bind('<MouseWheel>', lambda e: self.list_canvas.yview_scroll(-int(e.delta / 120), 'units'))
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill='x', padx=28, pady=15)
        self.health = tk.Label(footer, text='로컬 세션을 찾는 중…', font=('Malgun Gothic', 9), fg=MUTED, bg=BG)
        self.health.pack(side='left')
        self.init_office()
        self.drawtag = 'moving'
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        if demo:
            self.root.title('Agent Office · Demo')
            self.toggle_demo()
            self.toggle.configure(state='disabled', text='시연 모드')
            self.health.configure(text='시연 데이터 · 로컬 기록 읽기 꺼짐')
        else:
            threading.Thread(target=self.poll, daemon=True).start()
        self.root.after(50, self.tick)

    def button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg='#2b394a', fg=INK, activebackground='#3b4a5c', activeforeground=INK, relief='flat', bd=0, padx=16, pady=8, cursor='hand2', font=('Malgun Gothic', 10))

    def poll(self):
        next_scan = 0
        while not self.closed.is_set():
            try:
                if time.monotonic() >= next_scan:
                    states = self.monitor.scan()
                    next_scan = time.monotonic() + 3
                else:
                    states = self.monitor.snapshot()
                result = (states, ' · '.join(self.monitor.errors), self.monitor.total)
            except Exception as exc:
                result = ([], '기록 확인 실패: ' + type(exc).__name__, 0)
            try: self.inbox.put_nowait(result)
            except queue.Full: pass
            self.closed.wait(.2)

    def toggle_demo(self):
        self.demo = not self.demo
        self.characters.clear()
        self.confirm_queue.clear()
        self.last_states = {}
        self.selected = None
        self.detail.configure(text='시연' if self.demo else '')
        self.toggle.configure(text='실제 기록 보기' if self.demo else '시연 보기')
        self.mode.configure(text='●  DEMO / 시연 데이터' if self.demo else '●  LOCAL / LIVE', fg=PEACH if self.demo else MINT)
        self.refresh_cards(force=True)

    def states(self):
        if not self.demo: return self.live
        t = int((time.monotonic() - self.started) / 60)
        modes = ['working', 'needs_answer', 'needs_approval', 'compacting', 'done', 'quota_limited', 'rate_limited', 'working', 'thinking', 'quota_limited', 'paused', 'working']
        if not hasattr(self, 'demo_ids'):
            self.demo_ids = [next('demo'+str(n) for n in range(1000) if identity({'id':'demo'+str(n)})[0] == i) for i in range(9)] + ['claude-demo-'+str(i) for i in range(3)]
        rows = [dict(id=self.demo_ids[i], provider='Codex' if i < 9 else 'Claude', state=modes[(i+t) % len(modes)], updated=time.time(), project=['웹사이트', '테스트', '리뷰', '문서', 'API', '디자인'][i%6], subagent=i%3 != 0, short='DEMO '+str(i+1)) for i in range(12)]
        for i,s in enumerate(rows):
            if s['subagent']:s['parent_id']=rows[(i//3)*3]['id']
        return rows

    def refresh_cards(self, force=False):
        states = self.states()
        self.team_root,self.team_ids=selected_team(states,self.selected)
        signature = tuple((s['id'], s['state'], s['project'], s.get('attention_hint'),s.get('parent_id')) for s in states), self.selected, self.demo, self.waiting_collapsed
        if not force and getattr(self, 'card_signature', None) == signature: return
        self.card_signature = signature
        for widget in self.cards.winfo_children(): widget.destroy()
        if len(self.team_ids)>1:
            tk.Label(self.cards,text=f'선택한 팀 · {len(self.team_ids)}명',anchor='w',bg=PANEL,fg=MINT,font=('Malgun Gothic',10,'bold')).pack(fill='x',padx=7,pady=(0,8))
        attention = [s for s in states if s['state'] in NEEDS_INPUT]
        working = [s for s in states if s['state'] in ('working', 'thinking', 'compacting')]
        waiting = [s for s in states if s['state'] not in NEEDS_INPUT | {'working', 'thinking', 'compacting'}]
        tk.Label(self.cards, text=f'!  내 응답 필요  {len(attention)}', anchor='w', bg='#3e3440' if attention else PANEL, fg='#f0c38e' if attention else MUTED, font=('Malgun Gothic', 11, 'bold'), padx=7, pady=9).pack(fill='x', pady=(0,5))
        for s in attention: self.session_card(s)
        tk.Label(self.cards, text=f'●  작업 중  {len(working)}', anchor='w', bg=PANEL, fg=MINT, font=('Malgun Gothic', 11, 'bold')).pack(fill='x', padx=7, pady=(8, 7))
        for s in working: self.session_card(s)
        if not working:
            tk.Label(self.cards, text='작업 중인 에이전트 없음', anchor='w', bg=PANEL, fg=MUTED, font=('Malgun Gothic', 9)).pack(fill='x', padx=7, pady=(2, 14))
        arrow = '▸' if self.waiting_collapsed else '▾'
        tk.Button(self.cards, text=f'{arrow}  대기 중  {len(waiting)}', command=self.toggle_waiting, anchor='w', bg='#283443', fg=INK, activebackground='#344455', activeforeground=INK, relief='flat', bd=0, padx=10, pady=9, cursor='hand2', font=('Malgun Gothic', 11, 'bold')).pack(fill='x', pady=(14, 5))
        if not self.waiting_collapsed:
            for s in waiting: self.session_card(s)
            if not waiting:
                tk.Label(self.cards, text='대기 없음', anchor='w', bg=PANEL, fg=MUTED, font=('Malgun Gothic', 9)).pack(fill='x', padx=7, pady=8)
        active = sum(s['state'] in ('working', 'thinking', 'compacting') for s in states)
        self.count.configure(text=f"{len(states)}명 입실   ·   {active}명 작업 중   ·   {len(attention)}명 응답 필요")
        if not states:
            tk.Label(self.cards, text='아직 입실한 에이전트가 없어요.\n\nClaude Code 또는 Codex에서\n작업을 시작해 보세요.\n\n시연 보기로 움직임을\n먼저 구경할 수도 있어요.', bg=PANEL, fg=MUTED, justify='left', font=('Malgun Gothic', 10)).pack(pady=32)

    def toggle_waiting(self):
        self.waiting_collapsed = not self.waiting_collapsed
        self.refresh_cards(force=True)

    def session_card(self, s):
        color = MINT if s['provider'] == 'Codex' else PEACH
        pet, variant = identity(s)
        nickname = NAMES[pet] if s['provider'] == 'Codex' else 'Clawd · ' + ACCESSORIES[variant]
        row = tk.Frame(self.cards, bg='#304c49' if s['id'] in self.team_ids else '#332e3c' if s['state'] in NEEDS_INPUT else PANEL, highlightthickness=1 if s['id'] in self.team_ids else 0, highlightbackground=MINT)
        row.pack(fill='x', pady=2)
        label = tk.Label(row, text=f"{'↳' if s['subagent'] else '★'} {nickname} · {s['short']}", anchor='w', bg=row['bg'], fg=color, font=('Consolas', 10, 'bold'), cursor='hand2')
        label.pack(fill='x', padx=7, pady=(3, 0))
        suffix = ''
        sub = tk.Label(row, text=f"{s['provider']} · {LABELS[s['state']]}{suffix}", anchor='w', bg=row['bg'], fg=MUTED, font=('Malgun Gothic', 9), cursor='hand2')
        sub.pack(fill='x', padx=7, pady=(0, 3))
        if s['state'] in NEEDS_INPUT and s.get('attention_hint'):
            tk.Label(row,text=s['attention_hint'],wraplength=195,justify='left',anchor='w',bg=row['bg'],fg='#e7cbb0',font=('Malgun Gothic',9)).pack(fill='x',padx=7,pady=(0,5))
        for widget in (row, label, sub):
            widget.bind('<Button-1>', lambda e, key=s['id']: self.select(key))
            widget.bind('<Enter>', lambda e, key=s['id']: setattr(self, 'hover_row', key))
            widget.bind('<Leave>', lambda e: setattr(self, 'hover_row', None))

    def pet_hovered(self, key, x, y):
        if self.hover_row == key: return True
        if self.pointer is None: return False
        px,py=self.pointer
        px,py=(px-self.ox)/self.scale,(py-self.oy)/self.scale
        return abs(px-x)<36 and y-54<py<y+35

    def select(self, key):
        self.selected = None if self.selected == key else key
        if self.selected is None:
            self.detail.configure(text='')
            self.refresh_cards(force=True)
            return
        self.team_root,self.team_ids=selected_team(self.states(),self.selected)
        if any(s['id'] in self.team_ids and s['state'] not in NEEDS_INPUT | {'working','thinking','compacting'} for s in self.states()):
            self.waiting_collapsed=False
        s = next((s for s in self.states() if s['id'] == key), None)
        if s:
            if s['state'] not in NEEDS_INPUT | {'working', 'thinking', 'compacting'}:
                self.waiting_collapsed = False
            stamp = time.strftime('%H:%M:%S', time.localtime(s['updated'])) if s['updated'] else '알 수 없음'
            hint = '\n'+s['reset_hint'] if s.get('reset_hint') else ''
            if s['state'] in NEEDS_INPUT: hint='\n'+(s.get('attention_hint') or '원래 Claude / Codex 창에서 응답해 주세요.')
            self.detail.configure(text=f"{s['provider']} · {'하위 에이전트' if s['subagent'] else '세션'}\n{s['project']}\n마지막 상태 기록 {stamp}\n{LABELS[s['state']]}{' · 시연' if self.demo else ' · 기록 기반'}{hint}")
        self.refresh_cards(force=True)

    def select_character(self, event):
        x, y = (event.x-self.ox)/self.scale, (event.y-self.oy)/self.scale
        for key, a in self.characters.items():
            if abs(a['x']-x) < 35 and abs(a['y']-y+15) < 40:
                self.select(key)
                return
        self.selected=None
        self.detail.configure(text='')
        self.refresh_cards(force=True)

    def rect(self, x, y, w, h, color, outline=''):
        return self.canvas.create_rectangle(self.ox+x*self.scale, self.oy+y*self.scale, self.ox+(x+w)*self.scale, self.oy+(y+h)*self.scale, fill=color, outline=outline, width=1, tags=self.drawtag)

    def text(self, x, y, content, color=INK, size=10, anchor='center'):
        self.canvas.create_text(self.ox+x*self.scale, self.oy+y*self.scale, text=content, fill=color, font=('Malgun Gothic', max(8, int(size*self.scale))), anchor=anchor, tags=self.drawtag)

    def plant(self, x, y):
        self.rect(x+5,y+20,16,15,'#be8e71'); self.rect(x+2,y+18,22,5,'#e1ad83')
        self.rect(x+11,y,5,22,'#688e78'); self.rect(x,y+3,13,10,'#8cb391'); self.rect(x+14,y+7,13,10,'#729f80')

    def tick(self):
        try:
            self.live, self.last_error, total = self.inbox.get_nowait()
            self.last_scan = time.time()
            self.health.configure(text=self.last_error or f'최근 24시간 · {min(total,12)}/{total}개 세션')
        except queue.Empty: pass
        self.refresh_cards()
        self.canvas.delete('moving')
        w,h = self.canvas.winfo_width(),self.canvas.winfo_height()
        self.scale = min(w/self.WORLD_W,h/self.WORLD_H)
        self.ox,self.oy = (w-self.WORLD_W*self.scale)/2,(h-self.WORLD_H*self.scale)/2
        if self.scene_size != (w,h):
            self.canvas.delete('all')
            self.drawtag = 'room'
            self.room()
            self.scene_size = (w,h)
        self.drawtag = 'moving'
        states = self.states()
        self.bubbles = []
        now = time.monotonic()
        keys = {s['id'] for s in states}
        self.characters = {k:v for k,v in self.characters.items() if k in keys}
        self.seats = {k:v for k,v in self.seats.items() if k in keys}
        for s in states:
            if s['id'] not in self.seats:
                self.seats[s['id']] = next(n for n in range(12) if n not in self.seats.values())
        self.sync_queue(states)
        self.sync_routines(states)
        self.draw_queue()
        self.draw_team()
        for i,s in enumerate(states):
            entry_x,entry_y = self.desk(self.seats[s['id']])
            a = self.characters.setdefault(s['id'], dict(x=entry_x,y=entry_y,target=(720,690),next=0))
            self.sprite(a,s,i,now)
        self.draw_bubbles()
        if not states:
            self.rect(220,270,280,70,'#303e48')
            self.text(360,294,'에이전트의 입실을 기다리고 있어요',INK,12)
            self.text(360,320,'작업을 시작하거나 시연 보기를 눌러주세요',MUTED,10)
        if self.demo: self.text(500,746,'DEMO', '#384d45', 10)
        self.root.after(40,self.tick)

    def help(self):
        roots = '\n'.join(f'{k}: {v}' for k,v in self.monitor.roots.items())
        signals = '\n'.join(f'{name}: '+(time.strftime('%H:%M:%S',time.localtime(at))+' 신호 수신' if at else '신호 대기') for name in ('Claude','Codex') for at in [self.monitor.compaction.last_received.get(name,0)])
        roots += '\n\n압축 연결 (0.2초 간격)\n'+signals+'\n압축 시작 → 커피 / 완료 → 책상\n새 훅이 반영되지 않으면 Claude/Codex 세션을 재개하세요.'
        messagebox.showinfo('Agent Office 사용 안내', 'Claude Code와 Codex의 로컬 JSONL 기록을 읽는 관찰용 앱입니다.\n\n작업/생각 → 책상으로 이동\n완료 → 라운지 산책\n3분간 새 상태 기록 없음 → 상태 미확인\n\n도구의 파일명·명령 종류와 공개 진행 메시지를 로컬 화면에 표시합니다. 원문 기록을 별도로 저장하거나 전송하지 않습니다. 에이전트를 실행하거나 작업을 변경하지 않습니다.\n\n최근 24시간 기록 중 최신 48개를 확인하고 작업 중인 세션을 우선해 최대 12개 표시합니다. 기록 형식 변경이나 기록을 남기지 않는 앱은 감지되지 않을 수 있습니다. 질문/승인 요청은 명시적 요청 기록이 있을 때 감지합니다. 요청을 기록하지 않는 앱/버전의 승인 창은 감지되지 않을 수 있습니다. 응답은 원래 앱에서 해 주세요.\n\n폴더 변경: CODEX_HOME / CLAUDE_CONFIG_DIR 환경변수를 설정한 뒤 다시 실행하세요.\n\n'+roots)

    def close(self):
        self.closed.set()
        self.root.destroy()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Agent Office local session viewer')
    parser.add_argument('--demo', action='store_true', help='Show fictional sessions without reading local logs')
    args = parser.parse_args()
    AgentOffice(demo=args.demo).root.mainloop()
