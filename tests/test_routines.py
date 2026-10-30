import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from office import Office
from monitor import Tail, Monitor, transition

class RoutineTests(unittest.TestCase):
    def office(self):
        o=Office();o.obstacles=o.navigation_obstacles();o.confirm_queue=[];o.characters={}
        return o

    def test_coffee_trip_returns_and_new_work_interrupts(self):
        o=self.office();x,y=o.lounge_position(0)
        a={'x':x,'y':y,'next_coffee':0};o.characters['c']=a
        s={'id':'c','state':'idle'}
        with patch('routines.random.uniform',return_value=8):
            o.move_pet(a,s,0,0)
            self.assertIn('coffee_slot',a)
            drank=False
            for n in range(700):
                o.move_pet(a,s,0,n*.04)
                drank=drank or a.get('coffee_phase')=='drinking'
                if drank and 'coffee_slot' not in a:break
            self.assertTrue(drank)
            a['next_coffee']=float('inf')
            for n in range(700):o.move_pet(a,s,0,40+n*.04)
            self.assertEqual((a['x'],a['y']),o.lounge_position(0))
            a['coffee_slot']=0;s['state']='working';o.move_pet(a,s,0,80)
            self.assertNotIn('coffee_slot',a)
            self.assertEqual(a['destination'],o.desk(0))

    def test_compaction_started_and_completed_are_distinct(self):
        self.assertEqual(transition('Codex',{'type':'event_msg','payload':{'type':'context_compaction_started'}}),'compacting')
        self.assertEqual(transition('Codex',{'type':'compacted','payload':{}}),'thinking')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.jsonl';p.write_text(json.dumps({'type':'compacted','timestamp':'2026-10-30T05:00:00Z','payload':{}})+'\n')
            t=Tail(p,'Codex');t.read();self.assertGreater(t.compacted_at,0)
        o=self.office();a={'x':143,'y':249};o.characters['c']=a
        o.move_pet(a,{'id':'c','state':'compacting'},0,0)
        self.assertIn('coffee_slot',a)
        self.assertIn('압축 중',a['routine_label'])

    def test_report_only_to_known_parent_once(self):
        o=self.office()
        parent={'id':'p','state':'working','updated':1}
        child={'id':'c','state':'working','updated':1,'parent_id':'p'}
        px,py=o.desk(0);cx,cy=o.desk(1)
        o.characters={'p':{'x':px,'y':py},'c':{'x':cx,'y':cy}}
        o.sync_routines([parent,child]);child['state']='done';o.sync_routines([child,parent])
        a=o.characters['c'];self.assertEqual(a['report_parent'],'p')
        arrived=False
        for n in range(1500):
            o.move_pet(a,child,1,n*.04)
            arrived=arrived or a.get('report_until') is not None
        self.assertTrue(arrived);self.assertNotIn('report_parent',a)
        o.sync_routines([parent,child]);self.assertNotIn('report_parent',a)

    def test_compaction_coffee_stays_until_completion_then_returns_immediately(self):
        for seat in range(12):
            o=self.office();x,y=o.desk(seat)
            a={'x':x,'y':y};o.characters['c']=a
            s={'id':'c','state':'compacting'}
            drank=False
            for n in range(1500):
                o.move_pet(a,s,seat,n*.04)
                drank=drank or a.get('coffee_phase')=='drinking'
            self.assertTrue(drank,seat)
            self.assertEqual(a.get('coffee_phase'),'drinking')
            s.update(state='thinking',compacted_at=time.time())
            o.move_pet(a,s,seat,61)
            self.assertNotIn('coffee_slot',a)
            self.assertEqual(a['destination'],o.desk(seat))
            for n in range(1000):o.move_pet(a,s,seat,62+n*.04)
            self.assertEqual((a['x'],a['y']),o.desk(seat))

    def test_completed_only_does_not_start_coffee_and_short_compaction_turns_back(self):
        o=self.office();x,y=o.desk(0);a={'x':x,'y':y};o.characters['c']=a
        s={'id':'c','state':'thinking','compacted_at':time.time()}
        o.move_pet(a,s,0,0)
        self.assertNotIn('coffee_slot',a)
        s['state']='compacting';o.move_pet(a,s,0,1)
        self.assertEqual(a['coffee_phase'],'going')
        s['state']='working';o.move_pet(a,s,0,1.04)
        self.assertNotIn('coffee_slot',a)
        self.assertEqual(a['destination'],o.desk(0))

    def test_approval_interrupts_compaction_coffee(self):
        o=self.office();a={'x':143,'y':249};o.characters['c']=a
        s={'id':'c','state':'compacting'}
        o.routine_target(a,s,0,0)
        self.assertIn('coffee_slot',a)
        s['state']='needs_approval'
        self.assertIsNone(o.routine_target(a,s,0,1))
        self.assertNotIn('coffee_slot',a)
        self.assertNotIn('compact_break_until',a)

    def test_large_rotated_compaction_survives_tail_cutoff(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.jsonl'
            events=[{'type':'session_meta','payload':{'id':'session'}},
                    {'type':'compacted','payload':{'replacement_history':'x'*600000}},
                    {'type':'response_item','payload':{'type':'function_call','name':'Read','arguments':'{}'}}]
            p.write_text(''.join(json.dumps(e)+'\n' for e in events))
            t=Tail(p,'Codex');t.read()
            self.assertGreater(t.compacted_at,0)
            self.assertEqual(t.state,'working')
        self.assertEqual(transition('Codex',{'type':'response_item','payload':{'type':'compaction'}}),'thinking')

    def test_codex_parent_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in [('parent','cli'),('child',{'subagent':{'thread_spawn':{'parent_thread_id':'parent'}}})]:
                (root/(name+'.jsonl')).write_text(json.dumps({'type':'session_meta','payload':{'id':name,'source':source}})+'\n')
            states=Monitor({'Codex':root}).scan()
            c=next(s for s in states if s['session_id']=='child')
            self.assertEqual(c['parent_id'],str(root/'parent.jsonl'))
