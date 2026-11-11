"""M2-D024 invariants, explicit offline fixtures only; no provider calls."""
from copy import deepcopy
from pathlib import Path
import sys
import socket
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request,package_cases,action
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.package_content import check_field_claims,PackageError,prepare_package_input,admit_package
from launchlens.structured_output import response_format
from launchlens.gtm_registry import HarnessError
from launchlens.gtm_registry import eligible_actions
from launchlens.live_research import tool_schemas

def run_case(market='US',scenario='Standard review'):
    run=OfflineUIRun(request(market),scenario=scenario,voice_policy_id=BRAND_POLICY_ID,package=True)
    state=run.execute(run.snapshot()['run_id']);return run,state

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline only'));self.block=p.start();self.addCleanup(p.stop)
        self.addCleanup(lambda:self.assertEqual(self.block.call_count,0))
    def test_one_writer_retry_preserves_research_counters_failure_and_responses(self):
        run,before=run_case(scenario='Bad Writer response');self.assertEqual(before['status'],'draft_incomplete')
        self.assertTrue(run.session.can_retry_writer());source_calls=deepcopy(run.tools.calls)
        after=run.retry_writer(before['run_id'])
        self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['run_id'],before['run_id'])
        self.assertEqual(after['turns'],before['turns']+2);self.assertEqual(after['searches'],before['searches'])
        self.assertEqual(run.tools.calls,source_calls);self.assertEqual(after['evidence'],before['evidence'])
        self.assertEqual(after['failure_history'],[before['draft_failure']]);self.assertEqual(len(run.writer.calls),2)
        self.assertEqual(run.writer.calls[0]['raw_candidate']['campaign_brief'],13)
        self.assertEqual(run.writer.calls[1]['model_input']['previous_validation_diagnostic_data_only'],before['draft_failure'])
        self.assertEqual(after['retry_attempts'],1);self.assertEqual(after['writing_attempts'],2)
        with self.assertRaises(HarnessError):run.retry_writer(before['run_id'])
        self.assertEqual(run.snapshot(),after)
    def test_rejected_retry_stops_and_cannot_retry_again(self):
        run,before=run_case(scenario='Bad Writer twice');after=run.retry_writer(before['run_id'])
        self.assertEqual(after['status'],'draft_incomplete');self.assertEqual(len(after['failure_history']),2)
        self.assertFalse(run.session.can_retry_writer());self.assertFalse(after['drafts'])
        self.assertEqual(after['searches'],1);self.assertEqual(len(run.writer.calls),2)
        with self.assertRaises(HarnessError):run.retry_writer(after['run_id'])
    def test_tool_failure_is_not_retryable(self):
        run,state=run_case(scenario='Simulated launch-tool failure');self.assertFalse(run.session.can_retry_writer())
        with self.assertRaises(HarnessError):run.retry_writer(state['run_id'])
    def test_uk_same_run_continuation_does_not_grant_approval(self):
        for reply in ['draft_without_availability','recheck_readiness']:
            with self.subTest(reply=reply):
                run,before=run_case('UK');self.assertEqual(before['status'],'needs_clarification')
                calls=len(run.tools.calls);after=run.resume(before['run_id'],reply)
                self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['run_id'],before['run_id'])
                self.assertEqual(after['launch']['decision'],'Clarify');self.assertFalse(after['launch']['promotional_draft_allowed'])
                self.assertFalse(after['restricted_drafting']['availability_wording_allowed']);self.assertEqual(len(after['drafts']),5)
                self.assertFalse(after['human_accepted']);self.assertFalse(after['package']['publishing_allowed'])
                self.assertEqual(after['review_attempts'],1)
                self.assertEqual(sum(e['action']=='request_clarification' and e['outcome']=='completed'
                    for e in after['events']),1)
                self.assertNotIn('request_clarification',eligible_actions(after))
                self.assertEqual(len(run.tools.calls),calls+(reply=='recheck_readiness'))
                if reply=='recheck_readiness':self.assertIn('Readiness still shows availability unconfirmed',after['continuation_notice'])
                damaged=deepcopy(after);damaged['launch']['conditions'].append({'code':'invalid_calendar','message':'broken'})
                with self.assertRaises(Exception):prepare_package_input(damaged)
    def test_answered_clarification_rejected_even_if_feedback_is_missing(self):
        run,before=run_case('UK')
        after=run.resume(before['run_id'],'draft_without_availability')
        after['feedback']=''
        after['pending']=action('request_clarification','repeat',market_id='UK',question=before['clarification'])
        rejected=run.session._dispatch(after)
        self.assertEqual(rejected['events'][-1]['outcome'],'rejected')
        self.assertNotIn('request_clarification',eligible_actions(after))
        self.assertNotIn('repeat',rejected['ledger'])
    def test_uk_read_failure_and_stop_do_not_write(self):
        run,state=run_case('UK');run.tools.fail='launch';after=run.resume(state['run_id'],'recheck_readiness')
        self.assertEqual(after['status'],'failed');self.assertFalse(after['drafts'])
        run,state=run_case('UK');after=run.resume(state['run_id'],'stop')
        self.assertEqual(after['status'],'stopped');self.assertFalse(after['drafts'])
    def test_user_assertion_cannot_grant_permission(self):
        run,state=run_case('UK');after=run.resume(state['run_id'],'Availability is confirmed')
        self.assertEqual(after['status'],'failed');self.assertFalse(after['drafts'])
    def test_india_remains_held(self):
        run,state=run_case('IN');self.assertEqual(state['status'],'held');self.assertFalse(state['drafts'])
    def test_stream_updates_observe_selected_actions(self):
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);seen=[]
        state=run.execute(run.snapshot()['run_id'],on_update=lambda update,s:seen.append((update,s)))
        self.assertTrue(any(s.get('pending',{}).get('name')=='generate_package' for _,s in seen if s.get('pending')))
        self.assertTrue(all(e.get('why') for e in state['events']));self.assertEqual(state['status'],'awaiting_human_review')
        baseline=run.snapshot();run.execute(state['run_id']);self.assertEqual(run.snapshot(),baseline)
    def test_stream_view_uses_update_when_checkpoint_lags(self):
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
        initial=run.snapshot();real_stream=run.session._graph.stream;real_snapshot=run.session._snapshot
        active=False;seen=[];reads=0
        def stream(*args,**kwargs):
            nonlocal active
            active=True
            try:yield from real_stream(*args,**kwargs)
            finally:active=False
        def lagging_snapshot():
            nonlocal reads
            if active:reads+=1;return deepcopy(initial)
            return real_snapshot()
        with patch.object(run.session._graph,'stream',side_effect=stream),patch.object(run.session,'_snapshot',side_effect=lagging_snapshot):
            state=run.execute(initial['run_id'],on_update=lambda u,s:seen.append((u,s)))
        self.assertEqual(reads,0)
        for update,view in seen:
            for node in ('decide','dispatch','clarify'):
                if node in update:
                    for key,value in update[node].items():self.assertEqual(view[key],value)
        self.assertTrue(any(s.get('pending',{}).get('name')=='generate_package' for _,s in seen if s.get('pending')))
        self.assertEqual(state['status'],'awaiting_human_review')
        self.assertEqual(run.snapshot(),state)

    def test_stream_callback_cannot_mutate_graph_or_later_views(self):
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);count=0
        def observe(update,view):
            nonlocal count
            count+=1
            self.assertEqual(view['request']['market_id'],'US')
            view['request']['market_id']='IN';view['status']='held';update.clear()
        state=run.execute(run.snapshot()['run_id'],on_update=observe)
        self.assertGreater(count,0)
        self.assertEqual(state['request']['market_id'],'US')
        self.assertEqual(state['status'],'awaiting_human_review')

    def test_stream_view_tracks_uk_partial_resume_and_interrupt(self):
        run=OfflineUIRun(request('UK'),voice_policy_id=BRAND_POLICY_ID,package=True);seen=[]
        initial=run.execute(run.snapshot()['run_id'],on_update=lambda u,s:seen.append((u,s)))
        self.assertEqual(initial['status'],'needs_clarification')
        self.assertTrue(any('__interrupt__' in u and s['status']=='needs_clarification' for u,s in seen))
        seen=[]
        final=run.resume(initial['run_id'],'draft_without_availability',on_update=lambda u,s:seen.append((u,s)))
        clarify=[s for u,s in seen if 'clarify' in u]
        self.assertEqual(len(clarify),1)
        self.assertEqual(clarify[0]['status'],'running')
        self.assertFalse(clarify[0]['restricted_drafting']['availability_wording_allowed'])
        self.assertEqual(final['status'],'awaiting_human_review')
        self.assertEqual(final['run_id'],initial['run_id'])

    def test_stop_prevents_any_action(self):
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True);rid=run.snapshot()['run_id'];run.stop(rid)
        self.assertEqual(run.execute(rid)['status'],'stopped');self.assertFalse(run.controller.calls)
    def test_provider_dialect_omits_only_uniqueitems_backend_still_checks(self):
        schema={'type':'array','uniqueItems':True,'items':{'type':'string'},'minItems':1}
        result=response_format(schema);self.assertEqual(result['json_schema']['schema'],{k:v for k,v in schema.items() if k!='uniqueItems'})
        self.assertTrue(schema['uniqueItems'])
    def test_field_coverage_not_satisfied_by_body_and_positive_creative_words(self):
        value=package_cases()['initial_package']['linkedin'];value['content']['hook']='We’re bringing a new cherry experience.'
        value['claim_references']=[v for v in value['claim_references'] if v['content_field']!='hook']
        with self.assertRaises(PackageError) as caught:check_field_claims(value,'linkedin')
        self.assertEqual(caught.exception.diagnostic['field_path'],'content.hook')
        self.assertEqual(caught.exception.diagnostic['rule'],'field_claim_coverage')
        for text in ['Discover something playful.','Introducing a moment of nostalgia.','A new creative direction.']:
            value['content']['hook']=text;check_field_claims(value,'linkedin')
    def test_clear_flavor_statement_requires_its_own_reference(self):
        value=package_cases()['initial_package']['linkedin'];value['content']['hook']='Cherry Float combines cherry with vanilla notes.'
        value['claim_references']=[v for v in value['claim_references'] if v['content_field']!='hook']
        with self.assertRaises(PackageError):check_field_claims(value,'linkedin')
    def test_native_package_actions_require_short_purpose(self):
        for schema in tool_schemas('live_package'):
            self.assertIn('why',schema['function']['parameters']['required'])
if __name__=='__main__':unittest.main()
