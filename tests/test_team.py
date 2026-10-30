import unittest
from team import selected_team

class TeamTests(unittest.TestCase):
    def test_parent_child_and_nested_subagents(self):
        states=[{'id':'a'},{'id':'b','parent_id':'a'},{'id':'c','parent_id':'b'},{'id':'other'}]
        self.assertEqual(selected_team(states,'a'),('a',{'a','b','c'}))
        self.assertEqual(selected_team(states,'c'),('a',{'a','b','c'}))
        self.assertEqual(selected_team(states,None),(None,set()))

    def test_missing_parent_never_guesses_other_leader(self):
        states=[{'id':'a'},{'id':'b','parent_id':'missing'}]
        self.assertEqual(selected_team(states,'b'),('b',{'b'}))
        root,members=selected_team([{'id':'a','parent_id':'b'},{'id':'b','parent_id':'a'}],'a')
        self.assertEqual(members,{'a','b'})
