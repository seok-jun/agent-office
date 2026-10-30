"""Visual routines only: no agent commands or external side effects."""
import math
import random
from attention import NEEDS_INPUT

class Routines:
    def sync_routines(self,states):
        self.scene_states={s['id']:s for s in states}
        if not hasattr(self,'last_states'):self.last_states={}
        for s in states:
            a=self.characters.get(s['id'])
            old=self.last_states.get(s['id'])
            parent=s.get('parent_id')
            if a and old in ('working','thinking','compacting') and s['state']=='done' and parent in self.scene_states and parent!=s['id']:
                a['report_parent']=parent
                a['report_until']=None
            self.last_states[s['id']]=s['state']
        self.last_states={k:v for k,v in self.last_states.items() if k in self.scene_states}

    def coffee_position(self,slot):return (780+slot*60,450)

    def coffee_slot(self,key):
        occupied={a['coffee_slot'] for k,a in self.characters.items() if k!=key and 'coffee_slot' in a}
        return next((i for i in range(3) if i not in occupied),None)

    def clear_coffee(self,a,now):
        for key in ('coffee_slot','coffee_phase','coffee_until'):a.pop(key,None)
        a['next_coffee']=now+random.uniform(55,110)

    def routine_target(self,a,s,seat,now):
        state=s['state'];a['routine_label']=''
        compressing=state=='compacting'
        was_compressing=a.get('was_compacting',False)
        a['was_compacting']=compressing
        if compressing and not was_compressing:
            a.pop('returning',None)
            a.pop('report_parent',None)
        if was_compressing and not compressing:
            self.clear_coffee(a,now)
            a['returning']=True
        if state in NEEDS_INPUT or state in ('paused','quota_limited','rate_limited','error') or state=='working':
            self.clear_coffee(a,now)
            a.pop('report_parent',None)
            return None
        if a.get('report_parent'):
            parent=self.characters.get(a['report_parent'])
            if state!='done' or not parent:
                a.pop('report_parent',None)
            else:
                candidates=[(round(parent['x']/10)*10+dx,round(parent['y']/10)*10+dy) for dx,dy in ((40,0),(-40,0),(0,40),(0,-40))]
                target=next((p for p in candidates if self.route((a['x'],a['y']),p)),None)
                if target:
                    arrived=math.hypot(a['x']-target[0],a['y']-target[1])<5
                    a['routine_label']='작업 완료! 보고드려요' if arrived else '오케스트레이터에게 보고하러 가요'
                    if arrived and a.get('report_until') is None:a['report_until']=now+5
                    if a.get('report_until') and now>=a['report_until']:
                        a.pop('report_parent',None);a['returning']=True
                        return self.desk(seat)
                    return target
                a.pop('report_parent',None)
        if a.get('returning'):return None
        idle=state in ('idle','done','unknown')
        at_sofa=math.hypot(a['x']-self.lounge_position(seat)[0],a['y']-self.lounge_position(seat)[1])<4
        if idle and 'next_coffee' not in a:a['next_coffee']=now+random.uniform(45,90)
        wants_coffee=compressing or (idle and at_sofa and now>=a.get('next_coffee',float('inf')))
        if wants_coffee and 'coffee_slot' not in a:
            slot=self.coffee_slot(s['id'])
            if slot is not None:
                a['coffee_slot']=slot;a['coffee_phase']='going'
        if 'coffee_slot' in a:
            if not (idle or compressing):
                self.clear_coffee(a,now);return None
            target=self.coffee_position(a['coffee_slot'])
            arrived=math.hypot(a['x']-target[0],a['y']-target[1])<4
            if arrived and a['coffee_phase']=='going':
                a['coffee_phase']='drinking';a['coffee_until']=now+random.uniform(7,12)
            if not compressing and now>=a.get('coffee_until',float('inf')):
                self.clear_coffee(a,now)
                return self.lounge_position(seat) if idle else self.desk(seat)
            a['routine_label']='컨텍스트 압축 중' if compressing else '커피 한 잔 마시는 중' if arrived else '커피 마시러 가요'
            return target
        return None
