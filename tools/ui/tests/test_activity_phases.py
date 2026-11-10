"""Activity-only projection: no state mutation, source reads or provider calls."""
from copy import deepcopy
from html.parser import HTMLParser
import unittest
from launchlens.agent_run_ui import activity_phases,timeline


def event(action,outcome='completed',**kwargs):
 return dict(action=action,outcome=outcome,why='Use verified inputs.',**kwargs)


def state(events,version=None,status='awaiting_human_review'):
 return dict(events=events,status=status,pending=None,package={'version':version} if version else None,
  reviews=[],draft_history=[],revision_feedback='Owner requested changes.')


class ActivityPhasesTests(unittest.TestCase):
 def test_saved_heading_recovery_is_one_success_with_note_and_preserves_state(self):
  s=state([event('read_pmm_brief'),event('generate_package','failed_safely'),
    event('generate_package','revalidated_saved_candidate'),event('review_package',action_id='harness-review-v1')],1)
  s['failure_history']=[{'rule':'field_claim_coverage'}];before=deepcopy(s)
  phases=activity_phases(s);steps=phases[1]['steps']
  self.assertEqual([p['label'] for p in phases],['Research','Version 1'])
  self.assertEqual(len(steps),2);self.assertEqual(steps[0]['title'],'Wrote Version 1')
  self.assertIn('heading-citation rule update; no rewrite',steps[0]['recovery_note'])
  self.assertNotIn('step-icon hold',timeline(s));self.assertEqual(s,before)
 def test_only_current_version_expands_and_human_revision_step_is_retained(self):
  s=state([event('check_launch'),event('generate_package'),event('review_package',action_id='harness-review-v1'),
   event('revise_package',action_id='human-revision-v2-abc'),event('review_package',action_id='harness-review-v2')],2)
  phases=activity_phases(s)
  self.assertEqual([(p['label'],p['expanded']) for p in phases],[('Research',False),('Version 1',False),('Version 2',True)])
  self.assertEqual([r['title'] for r in phases[2]['steps']],['You reviewed and asked for changes','Wrote Version 2','Reviewer checked Version 2'])
  class Details(HTMLParser):
   opened=[]
   def handle_starttag(self,tag,attrs):
    if tag=='details':self.opened.append('open' in dict(attrs))
  parser=Details();parser.feed(timeline(s));self.assertEqual(parser.opened,[False,False,True])
 def test_successful_retry_collapses_failure_but_does_not_claim_no_rewrite(self):
  s=state([event('generate_package','failed_safely'),event('generate_package')],1)
  row=activity_phases(s)[0]['steps'][0]
  self.assertFalse(row['failed']);self.assertIn('later attempt',row['recovery_note']);self.assertNotIn('no rewrite',timeline(s))
 def test_unresolved_failure_and_different_action_failure_stay_visible(self):
  s=state([event('check_launch','failed_safely'),event('generate_package')],1)
  self.assertIn('step-icon hold',timeline(s))
  s=state([event('generate_package'),event('revise_package','failed_safely',action_id='human-revision-v2-x')],1,'failed')
  phases=activity_phases(s);self.assertTrue(phases[-1]['expanded']);self.assertTrue(phases[-1]['steps'][0]['failed'])
 def test_success_in_another_version_does_not_clear_previous_failure(self):
  s=state([event('generate_package'),event('review_package','failed_safely',action_id='harness-review-v1'),
    event('revise_package',action_id='human-revision-v2-x'),event('review_package',action_id='harness-review-v2')],2)
  phases=activity_phases(s);self.assertTrue(phases[0]['steps'][-1]['failed']);self.assertIn('step-icon hold',timeline(s))
 def test_pending_revision_expands_new_phase_and_research_only_expands_research(self):
  s=state([event('read_pmm_brief'),event('generate_package')],1,'running')
  s['pending']={'name':'revise_package','why':'Apply your feedback.'}
  phases=activity_phases(s);self.assertEqual(phases[-1]['label'],'Version 2');self.assertTrue(phases[-1]['expanded'])
  self.assertTrue(phases[-1]['steps'][-1]['pending']);self.assertFalse(phases[1]['expanded'])
  self.assertTrue(activity_phases(state([event('check_launch')],status='held'))[0]['expanded'])
 def test_owner_recheck_label_and_escaped_copy_are_preserved(self):
  s=state([event('review_package',action_id='harness-review-v2',origin='owner_command',)],2)
  s['events'][0]['why']='<unsafe> & words'
  html=timeline(s);self.assertIn('Re-check (requested by you)',html);self.assertIn('&lt;unsafe&gt; &amp;',html)
  self.assertIn('not executed',timeline(state([],status='created')))

if __name__=='__main__':unittest.main()
