import unittest
from office import Office

class QueueTests(unittest.TestCase):
    def test_idle_pet_reaches_sofa_and_stays_until_work(self):
        office=self.office()
        for seat in range(12):
            target=office.lounge_position(seat)
            self.assertTrue(office.route(office.desk(seat),target))
            s={'id':str(seat),'state':'idle','updated':1}
            x,y=office.desk(seat)
            a={'x':x,'y':y,'next':0,'target':(720,275),'next_coffee':float('inf')}
            for n in range(1200):office.move_pet(a,s,seat,n*.04)
            self.assertEqual((a['x'],a['y']),target)
            for n in range(50):self.assertFalse(office.move_pet(a,s,seat,100+n))
            s['state']='working'
            for n in range(1200):office.move_pet(a,s,seat,200+n*.04)
            self.assertEqual((a['x'],a['y']),office.desk(seat))

    def office(self):
        office=Office()
        office.obstacles=office.navigation_obstacles()
        office.confirm_queue=[]
        office.characters={}
        return office

    def test_every_desk_reaches_every_queue_slot(self):
        office=self.office()
        for seat in range(12):
            for slot in range(12):
                self.assertTrue(office.route(office.desk(seat),office.queue_position(slot)),(seat,slot))

    def test_queue_stable_order_and_advances_on_resolution(self):
        office=self.office()
        first={'id':'a','state':'needs_answer','updated':1}
        second={'id':'b','state':'needs_approval','updated':2}
        office.sync_queue([second,first])
        self.assertEqual(office.confirm_queue,['a','b'])
        first['updated']=3
        office.sync_queue([second,first])
        self.assertEqual(office.confirm_queue,['a','b'])
        office.characters['a']={'x':840,'y':660}
        first['state']='thinking'
        office.sync_queue([second,first])
        self.assertEqual(office.confirm_queue,['b'])
        self.assertTrue(office.characters['a']['returning'])

    def test_pet_walks_to_user_then_returns_to_original_desk(self):
        office=self.office()
        s={'id':'a','state':'needs_answer','updated':1}
        x,y=office.desk(0)
        a={'x':x,'y':y,'next':0,'target':(720,275)}
        office.characters['a']=a
        office.sync_queue([s])
        for n in range(1200): office.move_pet(a,s,0,n*.04)
        self.assertEqual((a['x'],a['y']),office.queue_position(0))
        s['state']='thinking';office.sync_queue([s])
        for n in range(1200): office.move_pet(a,s,0,n*.04)
        self.assertEqual((a['x'],a['y']),office.desk(0))
        self.assertFalse(a['returning'])
