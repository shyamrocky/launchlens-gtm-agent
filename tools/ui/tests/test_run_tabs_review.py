"""D030: three run tabs and review controls, all providers blocked."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.review_decisions import grouped_findings
from ui_review_helpers import finish_stack,show_card

class RunTabsTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-US').click().run();a.button(key='prepare-start').click().run();self.assertFalse(a.exception);return a
 def test_tabs_select_review_on_handoff_and_navigation_never_executes(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot();key='run-tabs-'+s['run_id']
  self.assertEqual([t.label for t in a.tabs if t.label in {'Activity','Review','Package'}],['Activity','Review','Package'])
  self.assertEqual(a.session_state[key],'Review');before=deepcopy(run.capture())
  a.session_state[key]='Package';a.run();self.assertEqual(a.session_state[key],'Package')
  a.session_state[key]='Activity';a.run();self.assertEqual(run.capture(),before);self.assertEqual(run.snapshot(),s)
 def test_single_occurrence_has_no_override_buttons_and_decision_labels_are_clear(self):
  a=self.app();s=a.session_state['offline_run'].snapshot();groups=grouped_findings(s)
  for g in groups:
   if not g['needs_attention']:continue
   show_card(a,g)
   for o in g['occurrences']:
    keys=[b.key for b in a.button]
    self.assertEqual('change-'+o['id'] in keys,len(g['occurrences'])>1)
    self.assertEqual('keep-'+o['id'] in keys,len(g['occurrences'])>1)
  g=next(g for g in groups if g['needs_attention']);show_card(a,g)
  a.button(key='changes-'+g['id']).click().run();self.assertEqual(a.session_state['run-review-position-'+s['run_id']],1);show_card(a,g)
  a.button(key='keep-'+g['id']).click().run();show_card(a,g);self.assertIn('Your choice: Kept as is',[c.value for c in a.caption]);a.button(key='review-summary').click().run()
  self.assertTrue(any(b.label=='Create Version 2' for b in a.button));self.assertFalse(any(b.label=='Request revision' for b in a.button))
 def test_missing_safe_hint_always_displays_fallback_and_raw_review_is_retained(self):
  a=self.app();run=a.session_state['offline_run'];before=deepcopy(run.snapshot()['review'])
  with patch('launchlens.review_decisions.safe_hints',return_value=[]):a.run()
  groups=[g for g in grouped_findings(run.snapshot()) if g['needs_attention']]
  self.assertTrue(any('No scan-safe suggestion' in c.value for c in a.caption));self.assertEqual(len([b for b in a.button if (b.key or '').startswith('changes-phrase-')]),1)
  self.assertEqual(run.snapshot()['review'],before)
 def test_two_occurrences_allow_a_single_override_without_another_model_call(self):
  a=self.app();run=a.session_state['offline_run'];state=run.snapshot();groups=grouped_findings(state)
  group=next(g for g in groups if g['needs_attention']);other=deepcopy(group['occurrences'][0]);other['id']='occ-explicit-second-fixture'
  group['occurrences'].append(other);calls=deepcopy(run.capture())
  with patch('launchlens.review_decisions.grouped_findings',return_value=groups):
   a.run();a.button(key='changes-'+group['id']).click().run();show_card(a,group)
   a.button(key='keep-'+other['id']).click().run()
   book=a.session_state['run-review-decisions-'+state['run_id']]
   from launchlens.review_decisions import effective_choice
   self.assertEqual(effective_choice(book,group,other),'keep_wording')
   self.assertEqual(effective_choice(book,group,group['occurrences'][0]),'request_changes')
  self.assertEqual(run.capture(),calls);self.assertEqual(run.snapshot(),state)
 def test_saved_v2_stopped_screen_offers_review_only_recovery(self):
  a=self.app();run=a.session_state['offline_run'];state=run.snapshot()
  run.revise(state['run_id'],'Keep evidence, remove unsupported wording.',1,state['package']['package_sha256'])
  state=run.snapshot();state.update(status='stopped',review={},review_attempts=1)
  state['reviews']=state['reviews'][:1];state['ledger'].pop('harness-review-v2')
  run.reviewer.calls=run.reviewer.calls[:1]
  run.session._graph.update_state(run.session._config(),state,as_node='dispatch')
  before=len(run.reviser.calls);a.run();self.assertFalse(a.exception)
  self.assertTrue(any(b.label=='Review Version 2' for b in a.button))
  a.button(key='run-recover-review').click().run();self.assertFalse(a.exception)
  self.assertEqual(len(run.reviser.calls),before);self.assertEqual(run.snapshot()['review']['binding']['draft_version'],2)
  self.assertFalse(any(b.label=='Review Version 2' for b in a.button))
 def test_invalid_finding_count_visible_without_global_incomplete_or_model_calls(self):
  a=self.app();run=a.session_state['offline_run'];state=run.snapshot()
  from launchlens.package_content import validate_package_review
  raw=deepcopy(state['review']['raw_response'])
  raw['linkedin']['findings'].append({'dimension':'tone','content_field':'body','quote':'NOT_IN_CURRENT_DRAFT',
   'severity':'advisory','rationale':'Obsolete quote.','suggested_change':'No replacement','claim_ids':[],'scan_hit_ids':[]})
  state['review']=validate_package_review(raw,state);state['reviews'][-1]=deepcopy(state['review'])
  for f,item in state['review']['format_reviews'].items():state['drafts'][f]['review_status']=item['review_status']
  run.session._graph.update_state(run.session._config(),state,as_node='dispatch');before=deepcopy(run.capture())
  a.run();self.assertFalse(a.exception)
  self.assertTrue(any("1 findings couldn't be verified" in w.value for w in a.warning))
  self.assertFalse(any('Review incomplete' in w.value for w in a.warning))
  self.assertEqual(run.capture(),before);self.assertTrue(run.snapshot()['review']['review_complete'])

class ActivityCopyTests(unittest.TestCase):
 def test_defaults_are_plain_and_why_is_capped_and_recheck_labeled(self):
  from launchlens.agent_run_ui import short_why,timeline
  self.assertLessEqual(len(short_why('word '*50,'read_pmm_brief').split()),20)
  self.assertNotIn('omitted',short_why('Registry purpose (agent omitted explanation): any','read_pmm_brief'))
  state={'events':[{'action':'review_package','outcome':'completed','origin':'owner_command','why':None}],
   'reviews':[{'binding':{'draft_version':2}}],'status':'awaiting_human_review','pending':None}
  html=timeline(state);self.assertIn('Re-check (requested by you)',html);self.assertNotIn('Registry purpose',html)

if __name__=='__main__':unittest.main()
