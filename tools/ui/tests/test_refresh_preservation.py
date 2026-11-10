"""Refresh only Home data; active runs and rebuild execution stay protected."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os,socket,sys,unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.gtm_registry import HarnessError
from launchlens.inventory_ui import refresh,refresh_blocked,REFRESH_BLOCKED_MESSAGE
from launchlens.package_presentation import approval_matches
from launchlens.review_decisions import decision_book

class RefreshTests(unittest.TestCase):
 def setUp(self):
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
  p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
 def app(self,market='US'):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  a.button(key='open-'+market).click().run();a.button(key='prepare-start').click().run()
  self.assertFalse(a.exception);return a
 def test_refresh_preserves_same_run_evidence_decisions_approval_notes_and_counters(self):
  a=self.app();run=a.session_state['offline_run'];s=run.snapshot();rid=s['run_id']
  next(c for c in a.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
  a.button(key='approve-package').click().run()
  keys=['run-review-decisions-'+rid,'run-internal-approval-'+rid,'selected_request','preparation_notes']
  saved={k:deepcopy(a.session_state[k]) for k in keys};before=run.snapshot();capture=deepcopy(run.capture())
  a.button(key='home').click().run();a.button(key='refresh').click().run()
  self.assertFalse(a.exception);self.assertIs(a.session_state['offline_run'],run)
  for k,v in saved.items():self.assertEqual(a.session_state[k],v)
  self.assertEqual(run.snapshot(),before);self.assertEqual(run.capture(),capture)
  self.assertTrue(approval_matches(before,saved[keys[0]],saved[keys[1]]))
  a.button(key='current').click().run();self.assertFalse(a.exception)
  self.assertIn('Package approved for internal use',' '.join(x.proto.body for x in a.get('html')))
 def test_waiting_clarification_blocks_refresh_and_mode_switch_without_losing_run(self):
  a=self.app('UK');run=a.session_state['offline_run'];before=run.snapshot()
  self.assertEqual(before['status'],'needs_clarification')
  a.button(key='home').click().run()
  self.assertTrue(a.button(key='refresh').disabled);self.assertEqual(a.button(key='refresh').proto.help,REFRESH_BLOCKED_MESSAGE)
  self.assertTrue(a.selectbox(key='ui-mode').disabled)
  self.assertTrue(a.button(key='refresh').disabled);self.assertEqual(run.snapshot(),before)
 def test_created_running_pending_revision_queued_command_and_locked_harness_block_handler(self):
  for state,command,locked in [({'status':'created'},None,False),({'status':'running'},None,False),
    ({'status':'needs_clarification'},None,False),({'status':'awaiting_human_review','revision_request':{'pending':True}},None,False),
    ({'status':'awaiting_human_review'},'execute',False),({'status':'running'},None,True)]:
   run=SimpleNamespace(snapshot=Mock(side_effect=HarnessError('busy') if locked else None,return_value=state),reset=Mock())
   session={'offline_run':run,'inventory':{'old':True},'run-command':command,'selected_request':{'kept':True}}
   with self.subTest(state=state,command=command,locked=locked),patch('launchlens.inventory_ui.st.session_state',session),patch('launchlens.inventory_ui.st.warning') as warning,patch('launchlens.inventory_ui.fetch_inventory') as fetch:
    self.assertTrue(refresh_blocked());self.assertFalse(refresh({}));fetch.assert_not_called();run.reset.assert_not_called()
    self.assertEqual(session['inventory'],{'old':True});warning.assert_called_once_with(REFRESH_BLOCKED_MESSAGE)
 def test_finished_or_stopped_refresh_updates_only_inventory_even_if_sources_fail(self):
  for status in ['awaiting_human_review','held','failed','draft_incomplete','stopped','research_complete']:
   run=SimpleNamespace(snapshot=Mock(return_value={'status':status}),reset=Mock())
   old={'markets':{'old':True}};new={'status':'unavailable','markets':{}}
   kept={'offline_run':run,'screen':'run','run-review-decisions-1':{'keep':True},'run-internal-approval-1':{'approved':True},'selected_request':{'id':1},'prepare-date-US':'kept'}
   session={**kept,'inventory':old,'ui-mode':'Live agent'}
   with self.subTest(status=status),patch('launchlens.inventory_ui.st.session_state',session),patch('launchlens.inventory_ui.fetch_inventory',return_value=new) as fetch:
    self.assertTrue(refresh({}));self.assertIs(session['inventory'],new)
    for k,v in kept.items():self.assertIs(session[k],v)
    run.reset.assert_not_called();fetch.assert_called_once_with({},verify_documents=True)
 def test_changed_source_warning_and_disabled_rebuild_card_have_no_execution(self):
  a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
  snap=deepcopy(a.session_state['inventory']);snap['source_access']={
    'Product Brief':{'status':'changed','detail':'content_mismatch','checked_at':'2026-11-10T20:00:00+00:00','sha256':'a'*64,'indexed_sha256':'b'*64},
    'Synthetic PRD':{'status':'changed','checked_at':'2026-11-10T20:00:00+00:00'}}
  a.session_state['inventory']=snap;a.run();self.assertFalse(a.exception)
  html=' '.join(x.proto.body for x in a.get('html'))
  self.assertIn('Product brief changed — evidence not re-indexed',html)
  self.assertIn('Synthetic PRD changed — evidence not re-indexed',html)
  self.assertNotIn('source-access good',html)
  self.assertFalse(any(b.key=='rebuild' for b in a.button))
  self.assertIn('Product brief changed · evidence not re-indexed',' '.join(x.proto.body for x in a.get('html')));self.assertTrue(a.button(key='source-rebuild'))
  self.assertNotIn('offline_run',a.session_state)
 def test_two_page_nav_preserves_run_and_does_not_fetch(self):
  a=self.app();run=a.session_state['offline_run'];before=run.snapshot();capture=deepcopy(run.capture())
  a.button(key='home').click().run()
  self.assertEqual([b.label for b in a.button[:2]],['GTM launches','Current run'])
  self.assertFalse(any(b.key=='rebuild' for b in a.button))
  with patch('launchlens.inventory_ui.fetch_inventory',side_effect=AssertionError('Navigation only')):
   a.button(key='current').click().run();self.assertFalse(a.exception)
  self.assertIs(a.session_state['offline_run'],run);self.assertEqual(run.snapshot(),before);self.assertEqual(run.capture(),capture)

class RefreshResultTests(unittest.TestCase):
 def setUp(self):
  from launchlens.inventory import load_display
  from launchlens.offline_ui_run import fixture_inventory
  self.old=fixture_inventory(load_display())
  # Successful live-access fixtures; no actual source reads.
  self.old.pop('data_mode')
  self.old['source_access']={'Product Brief':{'status':'accessible','sha256':'a'*64}}
  self.old['fetched_at']='2026-11-10T18:26:00+00:00'
 def test_no_changes_ignores_check_times_and_record_order(self):
  from launchlens.inventory_ui import refresh_changes
  new=deepcopy(self.old);new['fetched_at']='2026-11-10T18:27:00+00:00'
  new['source_access']['Product Brief']['checked_at']=new['fetched_at']
  for row in new['markets'].values():row['context']['readiness'].reverse()
  self.assertEqual(refresh_changes(self.old,new),{'changes':[],'incomplete':[],'fetched_at':new['fetched_at']})
 def test_india_authorization_date_and_blocker_changes_are_reported_without_mutation(self):
  from launchlens.inventory_ui import refresh_changes
  before=deepcopy(self.old);new=deepcopy(self.old)
  new['markets']['IN']['planned_launch_date']='2027-01-25'
  row=next(r['values'] for r in new['markets']['IN']['context']['readiness'] if r['values']['Readiness Area']=='Marketing communication authorization')
  row['Status']='Approved';row['Blocker / Missing Information']='None'
  result=refresh_changes(self.old,new)
  self.assertIn('India · Marketing authorization: Pending → Approved',result['changes'])
  self.assertIn('India · Launch date: Jan 18, 2027 → Jan 25, 2027',result['changes'])
  self.assertIn('India · Marketing authorization: blocker / missing information updated',result['changes'])
  self.assertFalse(result['incomplete']);self.assertEqual(self.old,before)
 def test_incomplete_reads_and_document_changes_never_say_no_changes(self):
  from launchlens.inventory_ui import refresh_changes
  for invalid in [True,False]:
   new=deepcopy(self.old)
   if invalid:new['markets']['UK']['context']['readiness']=[]
   else:new['markets']['UK']['source_status']='unavailable'
   new['source_access']['Product Brief']['status']='unavailable'
   result=refresh_changes(self.old,new)
   self.assertIn('UK',result['incomplete']);self.assertIn('Product Brief',result['incomplete'])
  new=deepcopy(self.old);new['source_access']['Product Brief']['sha256']='b'*64
  self.assertIn('Product Brief · Document changed — evidence not re-indexed',refresh_changes(self.old,new)['changes'])
 def test_refresh_result_and_last_checked_render_and_navigation_does_not_refetch(self):
  from launchlens.inventory import load_display,market_row
  new=deepcopy(self.old);new['fetched_at']='2026-11-10T18:27:00+00:00'
  context=new['markets']['IN']['context']
  row=next(r['values'] for r in context['readiness'] if r['values']['Readiness Area']=='Marketing communication authorization')
  row['Status']='Approved';row['Blocker / Missing Information']='None'
  new['markets']['IN']=market_row(context,'IN')
  with patch.object(socket.socket,'connect',side_effect=AssertionError('No network')) as net,patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'}):
   a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20)
   for k,v in {'inventory':deepcopy(self.old),'ui-mode':'Live agent','_data_mode':'Live agent'}.items():a.session_state[k]=v
   a.run();self.assertFalse(a.exception);self.assertFalse(a.success)
   with patch('launchlens.inventory_ui.fetch_inventory',return_value=new) as fetch:
    a.button(key='refresh').click().run();self.assertFalse(a.exception)
    self.assertIn('India · Marketing authorization: Pending → Approved',a.success[0].value)
    self.assertTrue(any('Last checked 10:27 AM' in c.value for c in a.caption))
    a.button(key='archives').click().run();a.button(key='home').click().run();self.assertEqual(fetch.call_count,1)
   same=deepcopy(new);same['fetched_at']='2026-11-10T18:28:00+00:00'
   with patch('launchlens.inventory_ui.fetch_inventory',return_value=same):a.button(key='refresh').click().run()
   self.assertEqual(a.info[0].value,'Updated · No changes');self.assertFalse(a.success)
   failed=deepcopy(same);failed['markets']['IN']['source_status']='unavailable'
   with patch('launchlens.inventory_ui.fetch_inventory',return_value=failed):a.button(key='refresh').click().run()
   self.assertTrue(any('Refresh incomplete' in w.value for w in a.warning));self.assertFalse(a.info)
   self.assertEqual(net.call_count,0)

if __name__=='__main__':unittest.main()
