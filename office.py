"""Native canvas office and official companion sprite playback."""
import hashlib
import heapq
import math
import random
import tkinter as tk
import time
from pet_assets import load_sheet
from companions import robot_frame
from monitor import RESTING, LABELS, wake_message
from attention import NEEDS_INPUT
from routines import Routines

PETS = ['codex', 'dewey', 'fireball', 'hoots', 'rocky', 'seedy', 'stacky', 'bsod', 'null-signal']
NAMES = ['Codex', 'Dewey', 'Fireball', 'Hoots', 'Rocky', 'Seedy', 'Stacky', 'BSOD', 'Null Signal']
COUNTS = [6, 8, 8, 4, 5, 8, 6, 6, 6]
ACCENTS = ['#9fd8cb', '#e6bc76', '#b8ace2', '#92bcdf', '#dba8b9', '#bad194']
ACCESSORIES = ['헤드셋', '안경', '리본', '캡', '스카프', '백팩']

def identity(session):
    seed = int(hashlib.sha256(session['id'].encode()).hexdigest()[:12], 16)
    # Assignment is stable between refreshes and app restarts.
    return seed % len(PETS), (seed // 9) % 6

class Office(Routines):
    WORLD_W, WORLD_H = 1000, 760

    def draw_bubbles(self):
        occupied=[]
        now=time.monotonic()
        for x,y,message,sleeping in self.bubbles:
            width,height=(210,66) if not sleeping and len(message)>32 else (164,56)
            left=max(24,min(self.WORLD_W-width-24,x-width/2))
            top=max(24,y-116)
            for offset in (0, -64, -128, 64):
                candidate=max(24,top+offset)
                if not any(left<r+5 and left+width>l-5 and candidate<b+4 and candidate+height>t-4 for l,t,r,b in occupied):
                    top=candidate; break
            occupied.append((left,top,left+width,top+height))
            top+=math.sin(now*1.3+x*.025)*2
            fill='#f2edf8' if sleeping else '#f1f8ed'
            border='#d4c9e2' if sleeping else '#c5d9c7'
            # A single scalloped silhouette avoids seams between overlapping ovals.
            profile=[(.00,.55),(.00,.33),(.07,.20),(.16,.20),(.19,.04),(.31,.00),(.40,.09),(.48,.01),(.59,.00),(.67,.10),(.77,.04),(.87,.10),(.90,.24),(.98,.30),(1.00,.49),(.97,.70),(.90,.78),(.82,.78),(.78,.95),(.65,1.00),(.56,.92),(.44,1.00),(.32,.96),(.25,.86),(.14,.90),(.05,.80)]
            def cloud(dx,dy,color,outline):
                points=[]
                for px,py in profile:
                    points.extend((self.ox+(left+px*width+dx)*self.scale,self.oy+(top+py*height+dy)*self.scale))
                self.canvas.create_polygon(points,smooth=True,splinesteps=24,fill=color,outline=outline,width=1,tags='moving')
            cloud(1,3,'#b6b5ad','')
            # Thought dots shrink toward the pet instead of a straight speech leader.
            bottom=top+height-2
            head=y-43
            for fraction,radius in ((.27,5),(.58,3.5),(.84,2)):
                cx=x+math.sin(fraction*math.pi)*7
                cy=bottom+(head-bottom)*fraction
                self.canvas.create_oval(self.ox+(cx-radius)*self.scale,self.oy+(cy-radius)*self.scale,self.ox+(cx+radius)*self.scale,self.oy+(cy+radius)*self.scale,fill=fill,outline=border,tags='moving')
            cloud(0,0,fill,border)
            self.canvas.create_text(self.ox+(left+width/2)*self.scale,self.oy+(top+height/2)*self.scale,text=message,fill='#756581' if sleeping else '#526e5c',font=('Malgun Gothic',max(8,int(9*self.scale))),width=(width-22)*self.scale,justify='center',tags='moving')

    def pet_catalog(self):
        window=tk.Toplevel(self.root)
        window.title('펫 도감 · 9 companions')
        window.configure(bg='#192231')
        window.resizable(False,False)
        tk.Label(window,text='MEET YOUR LITTLE TEAM',font=('Consolas',18,'bold'),bg='#192231',fg='#e9eee7').grid(row=0,column=0,columnspan=3,padx=30,pady=(22,5))
        tk.Label(window,text='같은 세션은 같은 펫 · 로컬 이미지가 없으면 로봇 표시',font=('Malgun Gothic',10),bg='#192231',fg='#96a9b5').grid(row=1,column=0,columnspan=3,pady=(0,15))
        for i,pet in enumerate(PETS):
            tile=tk.Frame(window,bg='#263643',width=172,height=132)
            tile.grid(row=2+i//3,column=i%3,padx=9,pady=9)
            tile.grid_propagate(False)
            tk.Label(tile,image=self.pet_frame(pet,0,0,False),bg='#263643').pack(pady=(12,2))
            tk.Label(tile,text=NAMES[i],bg='#263643',fg='#d7e6ce',font=('Consolas',12,'bold')).pack(padx=44,pady=(0,10))
        tk.Label(window,text='Claude: Clawd 스타일 도트 캐릭터 + 6가지 액세서리\n★ 메인 에이전트     S 작은 서브 에이전트',font=('Malgun Gothic',10),bg='#192231',fg='#96a9b5').grid(row=5,column=0,columnspan=3,pady=20)

    def init_office(self):
        self.pet_sheets = {}
        self.pet_frames = {}
        self.seats = {}
        self.confirm_queue = []
        self.scene_size = None
        self.obstacles = self.navigation_obstacles()
        for pet in PETS:
            sheet = load_sheet(pet, self.root)
            if sheet is not None:
                self.pet_sheets[pet] = sheet

    def navigation_obstacles(self):
        obstacles = []
        for i in range(12):
            x,y = self.desk(i)
            obstacles.append((x-49,y-69,x+49,y-23))
        obstacles += [(745,350,936,419),
                           (442,470,641,576), (765,199,925,259),
                           (725,515,960,528), (725,585,960,598), (725,655,960,668),
                           (677,165,685,390), (677,450,685,644)]
        return obstacles

    def desk(self, i):
        pod, seat = divmod(i,4)
        bx,by = [(143,249),(450,249),(143,516)][pod]
        return bx+(seat%2)*118, by+(seat//2)*104

    def room(self):
        r,t = self.rect,self.text
        r(0,0,1000,760,'#26343d')
        r(18,20,964,118,'#526567')
        r(18,138,964,600,'#d5c8ae')
        for y in range(140,738,25):
            r(18,y,964,1,'#c7b99f')
            for x in range(18+(55 if y%2 else 0),980,110): r(x,y,1,25,'#c7b99f')
        # Tall windows with a pixel city skyline.
        for x in (58,235,644,821):
            r(x,40,122,69,'#314650'); r(x+5,45,112,59,'#a7c8c9')
            for j,height in enumerate((18,30,22,40,28)):
                r(x+8+j*21,100-height,17,height,'#87a7ae')
                r(x+12+j*21,105-height,4,4,'#dbe7da')
            r(x+59,44,4,62,'#607a7a'); r(x+5,75,112,4,'#607a7a')
            r(x-5,109,132,8,'#e9dcc1')
        t(500,62,'Agent Office', '#f8efdb',20)
        # Spacious team islands on individual woven rugs.
        for x,y,label,tone in [(70,167,'01   BUILD STUDIO','#8daaa1'),(377,167,'02   RESEARCH LAB','#9daabc'),(70,434,'03   MAKER CORNER','#b4a0a1')]:
            r(x-5,y+9,258,220,'#b6a98f'); r(x,y,248,220,tone)
            r(x+6,y+6,236,208,'', '#c9d1bc')
            self.plant(x+215,y+168)
        # Long bookcase and a glass separator between studio and social area.
        r(677,165,8,479,'#8c9e93')
        for y in range(178,640,72): r(680,y,2,44,'#c4d2bd')
        for y in (177,432): self.plant(650,y)
        # Coffee counter in the middle of the social area.
        t(846,337,'커피','#596d62',11)
        r(749,366,183,53,'#927b60'); r(745,350,191,16,'#eee1c6')
        r(759,325,39,28,'#424e50'); r(764,329,29,13,'#7c9696')
        r(769,343,9,10,'#f5e4c4'); r(808,338,10,15,'#ede8d7')
        r(820,343,8,10,'#e4d8c1'); r(876,333,33,19,'#b7c5a2')
        self.plant(935,355)
        # Three four-seat sofas: every idle pet has its own cushion.
        r(714,475,255,250,'#a6b29a'); r(720,481,243,238,'', '#d3d7bb')
        t(840,493,'라운지','#536b60',11)
        for sofa_y,color in ((515,'#789c9b'),(585,'#8996b5'),(655,'#b09a9d')):
            self.sofa(725,sofa_y,235,color)
            for cushion in (784,843,902): r(cushion,sofa_y+15,2,30,'#c5d1bd')
        # Meeting nook.
        r(403,437,245,203,'#b3b8ab'); r(409,443,233,191,'', '#e2dcc6')
        r(458,490,167,70,'#9d8768'); r(452,481,179,70,'#edd9b4')
        for x in (479,574):
            r(x,464,30,17,'#71858d'); r(x,557,30,19,'#71858d')
        r(478,498,28,19,'#586e7c'); r(481,501,22,13,'#9cc1be')
        r(536,513,34,20,'#f3eed9'); r(540,518,20,2,'#aab6a2')
        r(594,503,10,12,'#f7efe0')
        # User's own desk: the approval queue starts directly in front of it.
        r(726,155,225,127,'#c8baa0')
        r(732,161,213,115,'','#e3d7bc')
        t(840,171,'내 자리','#596d62',11)
        r(816,183,48,41,'#708c91')
        # Seated human avatar, facing the team across the desk.
        r(827,184,26,9,'#51454a'); r(824,191,32,9,'#51454a')
        r(828,193,24,22,'#efd0a7'); r(832,200,3,4,'#4a4547'); r(846,200,3,4,'#4a4547')
        r(837,209,8,2,'#bd8a74'); r(824,215,32,19,'#8a9dc5')
        r(765,231,160,28,'#9b8263'); r(760,222,170,25,'#f1dfbb')
        r(778,207,37,23,'#506875'); r(782,211,29,15,'#abd2c4')
        r(774,230,45,4,'#84999a'); r(862,228,26,12,'#faf3df')
        r(893,220,11,14,'#f6f0dc'); r(900,224,6,7,'','#f6f0dc')
        self.plant(931,200)
        r(71,678,219,35,'#f0e4c9'); r(81,713,9,14,'#917c62')
        self.plant(34,650)
        for i in range(12):
            x,y=self.desk(i)
            r(x-49,y-65,98,44,'#9c8464'); r(x-49,y-70,98,39,'#f0dfbe')
            r(x-43,y-31,6,15,'#8e795e'); r(x+37,y-31,6,15,'#8e795e')
            r(x-26,y-87,46,31,'#354852'); r(x-22,y-83,38,22,'#8fb8b6')
            for k,width in enumerate((22,14,26)): r(x-18,y-79+k*5,width,2,'#d8e8cb')
            r(x-5,y-56,6,9,'#657a7b'); r(x-17,y-43,29,6,'#b4b19c')
            r(x+29,y-52,9,12,'#eaf0d9'); r(x+31,y-54,5,3,'#8b745c')
            r(x-16,y-9,32,20,'#718990'); r(x-12,y+9,24,5,'#546e79')
            t(x-35,y-58,f'{i+1:02}', '#8c927b',8)

    def sofa(self,x,y,w,color):
        self.rect(x,y,w,48,color)
        self.rect(x,y,w,12,'#9db6ab')
        for sx in (x,x+w-12): self.rect(sx,y,12,56,'#648b8c')
        self.rect(x+w/2,y+15,2,29,'#628d8c')
        self.rect(x+19,y+19,21,16,'#dfcfaa')

    def route(self, start, goal):
        # Four-way grid navigation keeps pets out of furniture.
        cell=lambda p:(round(p[0]/10),round(p[1]/10))
        a,b=cell(start),cell(goal)
        def free(p):
            x,y=p[0]*10,p[1]*10
            return 35<=x<=960 and 150<=y<=715 and not any(l-10<x<r+10 and t-7<y<bt+7 for l,t,r,bt in self.obstacles)
        frontier=[(0,a)]; cost={a:0}; prev={}
        while frontier:
            _,u=heapq.heappop(frontier)
            if u==b: break
            for v in ((u[0]+1,u[1]),(u[0]-1,u[1]),(u[0],u[1]+1),(u[0],u[1]-1)):
                if not free(v): continue
                c=cost[u]+1
                if c<cost.get(v,100000):
                    cost[v]=c; prev[v]=u
                    heapq.heappush(frontier,(c+abs(v[0]-b[0])+abs(v[1]-b[1]),v))
        if b not in cost: return []
        path=[goal]; p=b
        while p!=a:
            path.append((p[0]*10,p[1]*10)); p=prev[p]
        return list(reversed(path))

    def lounge_position(self, seat):
        return (748+(seat%4)*59,550+(seat//4)*70)

    def queue_position(self, index):
        positions=[(840,300),(770,300),(710,320),(710,390),(640,410),(570,410),
                   (500,410),(430,410),(350,410),(350,480),(350,550),(350,620)]
        return positions[index]

    def sync_queue(self, states):
        pending={s['id'] for s in states if s['state'] in NEEDS_INPUT}
        previous=list(self.confirm_queue)
        self.confirm_queue=[key for key in previous if key in pending]
        # Once queued, list reordering or status polling cannot change their turn.
        for s in sorted(states,key=lambda s:s['updated']):
            if s['id'] in pending and s['id'] not in self.confirm_queue:
                self.confirm_queue.append(s['id'])
        for key in set(previous)-pending:
            if key in self.characters: self.characters[key]['returning']=True

    def draw_queue(self):
        if not self.confirm_queue:return
        for i,key in enumerate(self.confirm_queue):
            x,y=self.queue_position(i)
            self.canvas.create_oval(self.ox+(x-18)*self.scale,self.oy+(y+6)*self.scale,self.ox+(x+18)*self.scale,self.oy+(y+17)*self.scale,fill='',outline='#ac967b',dash=(2,3),tags='moving')
            self.text(x+28,y+10,f'{i+1}', '#8b7563',8)
        self.text(840,145,f'확인 대기 {len(self.confirm_queue)}명','#8c684c',10)

    def move_pet(self,a,s,seat,now):
        working=s['state'] in ('working','thinking','compacting') or s['state'] in RESTING | NEEDS_INPUT
        target=self.desk(seat)
        routine=self.routine_target(a,s,seat,now)
        if s['id'] in self.confirm_queue:
            target=self.queue_position(self.confirm_queue.index(s['id']))
            a['returning']=False
        elif routine is not None:
            target=routine
        elif a.get('returning'):
            if math.hypot(a['x']-target[0],a['y']-target[1])<3:
                a['returning']=False
        elif not working:
            target=self.lounge_position(seat)
        if a.get('destination')!=target:
            a['path']=self.route((a['x'],a['y']),target)
            a['destination']=target
        walking=bool(a.get('path'))
        if walking:
            tx,ty=a['path'][0]; dx,dy=tx-a['x'],ty-a['y']; dist=math.hypot(dx,dy)
            step=min(dist,2.5)
            if dist:
                a['x']+=dx/dist*step; a['y']+=dy/dist*step
                if dx: a['left']=dx<0
            if dist<=2.5: a['path'].pop(0)
        return walking

    def draw_team(self):
        for key in self.team_ids:
            child=self.characters.get(key)
            parent_id=self.scene_states.get(key,{}).get('parent_id')
            parent=self.characters.get(parent_id)
            if child and parent and parent_id in self.team_ids:
                self.canvas.create_line(self.ox+parent['x']*self.scale,self.oy+parent['y']*self.scale,self.ox+child['x']*self.scale,self.oy+child['y']*self.scale,fill='#75c4ab',width=2,dash=(5,5),arrow='last',tags='moving')

    def pet_frame(self,pet,row,frame,sub):
        if pet not in self.pet_sheets:
            key = (pet, row, frame, sub)
            if key not in self.pet_frames:
                self.pet_frames[key] = robot_frame(PETS.index(pet), row, frame, sub)
            return self.pet_frames[key]
        # Tk handles atlas cropping and nearest-neighbour scaling without extra dependencies.
        divisor=4 if sub else 3
        key=(pet,row,frame,divisor)
        if key not in self.pet_frames:
            crop=tk.PhotoImage(width=192,height=208)
            crop.tk.call(str(crop),'copy',str(self.pet_sheets[pet]),'-from',frame*192,row*208,(frame+1)*192,(row+1)*208,'-to',0,0)
            self.pet_frames[key]=crop.subsample(divisor,divisor)
        return self.pet_frames[key]

    def sprite(self,a,s,index,now):
        seat=self.seats[s['id']]
        walking=self.move_pet(a,s,seat,now)
        x,y=a['x'],a['y']; pet,variant=identity(s)
        lounging=s['state'] not in RESTING | NEEDS_INPUT | {'working','thinking','compacting'} and not walking and not a.get('returning') and not a.get('routine_label')
        if lounging: y += 4
        sleeping=s['state'] in RESTING and not walking
        if sleeping: y += 7 + math.sin(now*1.7)*1.5
        sub=s['subagent']; accent=ACCENTS[variant]
        r,t=self.rect,self.text
        if s['id'] in self.team_ids:
            self.canvas.create_oval(self.ox+(x-32)*self.scale,self.oy+(y-51)*self.scale,self.ox+(x+32)*self.scale,self.oy+(y+16)*self.scale,fill='',outline='#93dfb1',width=3 if s['id']==self.team_root else 2,tags='moving')
            if s['id']==self.team_root:t(x,y-60,'리드','#437c66',9)
        r(x-19,y+8,38,5,'#a49f8c')
        if s['provider']=='Codex':
            row=(2 if a.get('left') else 1) if walking else {'working':7,'thinking':8,'done':3,'error':5,'unknown':6,'idle':0}.get(s['state'],0)
            frame=int(now*7+pet)%COUNTS[row]
            if sleeping: row,frame=0,1
            elif lounging: row,frame=0,int(now*2+pet)%6
            picture=self.pet_frame(PETS[pet],row,frame,sub)
            self.canvas.create_image(self.ox+x*self.scale,self.oy+(y-18)*self.scale,image=picture,tags='moving')
            name=NAMES[pet]
        else:
            # Clawd-inspired native pixel crab, with six wardrobe variations.
            unit=2 if sub else 2.6
            shade=['#d58c6e','#d49c7c','#ce997e','#e2aa88','#bc8b78','#d99d86'][variant]
            bounce=(int(now*8)%2)*2 if walking else math.sin(now*3)*1
            def px(l,top,w,h,c): r(x+l*unit,y+(top-12)*unit-bounce,w*unit,h*unit,c)
            px(-8,-2,16,11,shade); px(-10,0,2,7,shade); px(8,0,2,7,shade)
            px(-6,-4,12,2,shade); px(-5,1,2,3,'#322e32'); px(3,1,2,3,'#322e32')
            if sleeping:
                px(-5,1,2,3,shade); px(3,1,2,3,shade)
                px(-6,3,3,1,'#554039'); px(3,3,3,1,'#554039')
            px(-12,4,3,3,shade); px(9,4,3,3,shade)
            for leg in (-7,-3,2,6): px(leg,9,2,3+(int(now*8+leg)%2 if walking else 0),shade)
            if variant==0: # headphones
                px(-9,-4,18,2,'#596879'); px(-11,-2,3,7,'#596879'); px(8,-2,3,7,'#596879')
            elif variant==1: # glasses
                px(-7,0,6,1,'#4c5059'); px(1,0,6,1,'#4c5059'); px(-1,2,2,1,'#4c5059'); px(-7,4,6,1,'#4c5059'); px(1,4,6,1,'#4c5059')
            elif variant==2: px(5,-6,4,4,accent); px(9,-7,3,5,accent)
            elif variant==3: px(-6,-6,12,3,accent); px(-8,-3,19,2,accent)
            elif variant==4: px(-8,7,16,2,accent); px(4,9,3,5,accent)
            else: px(8,2,4,7,accent)
            name='Clawd'
        # Side accessories don't obscure the official pet artwork.
        r(x+23,y-14,13,14,accent)
        t(x+29,y-7,['♫','⌕','✦','▰','≈','▣'][variant],'#344b50',9)
        if not sub:
            r(x-27,y-46,16,14,'#e8cc80'); t(x-19,y-39,'★','#77613a',9)
        else:
            r(x-26,y-41,15,13,accent); t(x-19,y-35,'S','#344b50',8)
        status={'working':'#9fd8b4','thinking':'#a6c9ef','done':'#cedd94','error':'#e49d91','unknown':'#a3acb5','idle':'#a6beb6','paused':'#b8ace2','quota_limited':'#e8cc80','rate_limited':'#e8cc80'}.get(s['state'],'#e8cc80')
        r(x+18,y-44,6,6,status)
        if a.get('coffee_phase')=='drinking' and not walking:
            cup_y=y-5-int(math.sin(now*2)>0)*5
            r(x+13,cup_y,9,10,'#f8efdc');r(x+21,cup_y+2,4,5,'','#f8efdc')
            t(x+18,cup_y-8,'~','#e8e5d5',9)
        if a.get('report_parent'):
            r(x+12,y-4,12,15,'#f7edcd');r(x+15,y,6,2,'#93a79b')
        if not walking and s['state']=='working':
            r(x-15,y+4,30,5,'#64777b')
            for n in range(4): r(x-11+n*6,y+5,3,2,'#c9dfc3' if int(now*8+n)%2 else '#9bab9a')
        if lounging:
            sofa_color=['#789c9b','#8996b5','#b09a9d'][seat//4]
            r(x-21,y+7,42,8,sofa_color)
        r(x-27,y+17,54,15,'#34494e')
        t(x,y+25,f'{name if len(name)<10 else name[:8]} {seat+1:02}', '#e5ecdc',8)
        if sleeping:
            drift=(now*8)%12
            t(x+36,y-51-drift,'z Z', '#85749e',12)
        if a.get('report_parent') or s['state']=='compacting' or (a.get('routine_label') and s['state']=='thinking'):
            self.bubbles.append((x,y,a.get('routine_label') or '컨텍스트 압축 중',False))
        elif s['state'] in ('working','thinking'):
            self.bubbles.append((x,y,s.get('activity') or ('다음 작업 검토 중' if s['state']=='thinking' else '작업 진행 중'),False))
        elif s['state'] in NEEDS_INPUT:
            heading='? 답변 기다리는 중' if s['state']=='needs_answer' else '! 승인 기다리는 중'
            rank=self.confirm_queue.index(s['id']) if s['id'] in self.confirm_queue else 0
            hint=s.get('attention_hint') or ('확인받으러 가는 중이에요' if walking else '잠깐 확인해 주세요!' if rank==0 else f'{rank+1}번째로 기다리고 있어요')
            self.bubbles.append((x,y,heading+'\n'+hint,False))
            t(x+28,y-38,'?' if s['state']=='needs_answer' else '!','#a56a38',17)
        elif self.pet_hovered(s['id'],x,y):
            message=a.get('routine_label') or (wake_message(s,time.time()) if s['state'] in RESTING else LABELS[s['state']]+'\n새 작업 기다리는 중')
            self.bubbles.append((x,y,message,True))
