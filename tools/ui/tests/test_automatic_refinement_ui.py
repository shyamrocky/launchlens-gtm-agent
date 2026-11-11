"""Revision attribution and truthful Activity text; no provider calls."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.agent_run_ui import revision_usage,activity_phases
class AutoRefineUITests(unittest.TestCase):
 def test_each_revision_has_its_actual_actor_in_order(self):
  state={'revision_attempts':1,'events':[{'action':'revise_package','origin':'agent','outcome':'completed'}]}
  self.assertEqual(revision_usage(state),'1 of 3 used · by agent')
  state['revision_attempts']=2;state['events'].insert(0,{'action':'revise_package','origin':'human','outcome':'completed'})
  self.assertEqual(revision_usage(state),'2 of 3 used · 1: you · 2: agent')
 def test_fix_count_is_from_fresh_review_not_assumed_from_revision(self):
  s={'revision_attempts':1,'package':{'version':2},'status':'awaiting_human_review','reviews':[],
   'events':[{'action':'automatic_refinement','outcome':'completed','origin':'agent','fixed_count':2,
     'attempted_count':3,'why':'Fresh review checked the changes.'}]}
  self.assertEqual(activity_phases(s)[0]['steps'][0]['title'],'Agent changed 2 flagged phrases')
  s['events'][0]['fixed_count']=0
  self.assertEqual(activity_phases(s)[0]['steps'][0]['title'],'Agent refinement checked')
if __name__=='__main__':unittest.main()
