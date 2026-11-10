"""Prepared live wiring exercised entirely with fake responses; zero socket attempts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from launchlens.gtm_registry import HarnessError
from launchlens.live_package import (LiveGateError,LivePackageRun,RunBudget,LiveTransport,
    authorization_template,validate_authorization,preflight,profile,read_authorization,readiness,
    create_live_run,redact)
from launchlens.offline_fixtures import ReviewFixtureTools,package_cases,request,action
from launchlens.linkedin_drafting import digest
from launchlens.package_content import load_package_prompt
from launchlens.writer_comparison import WireResponse,ProtectedStore

KEYS={'NEBIUS_API_KEY':'TEST-NEBIUS-CREDENTIAL','NOTION_API_KEY':'TEST-NOTION-CREDENTIAL','PINECONE_API_KEY':'TEST-PINECONE-CREDENTIAL'}
NOW=datetime.fromisoformat(profile()['checked_utc'])+timedelta(minutes=1)


def permission():
    value=authorization_template()
    value.update(owner_authorized=True,authorization_id='MOCK-TEST-ONLY',authorization_reference='MOCK permission, not owner approval',
        source_permissions_confirmed=True,acknowledge_catalog_not_entitlement=True,
        acknowledge_context_reservation_and_cap_assumptions=True,expires_utc=(NOW+timedelta(hours=1)).isoformat())
    return value


def project(inputs):
    return {'model_input':deepcopy(inputs),'manifest':{'authoritative_input_sha256':digest(inputs),'model_input_sha256':digest(inputs),
        'note':'Identity fixture projection for mock wiring; real adapter defaults to the unchanged reviewed projector'}}


class Wire:
    def __init__(self, override=None):self.calls=[];self.controller=0;self.override=override
    def __call__(self,model,validator):
        def http(payload):
            if not validator(payload):raise AssertionError('Translation mismatch')
            self.calls.append(deepcopy(payload))
            if self.override is not None:return self.override(payload)
            stage=next(k for k in ['package_controller','package_writer','package_reviewer','package_revision']
                if payload['messages'][0]['content']==load_package_prompt(k))
            data=package_cases()
            if stage=='package_controller':
                actions=[action('read_pmm_brief','pmm'),action('check_launch','launch'),
                    action('search_product_evidence','facts',query='Flavor and float inspiration',authority='public_product_facts'),
                    action('generate_package','write'),
                    action('revise_package','revise-v2')]
                chosen=actions[self.controller];self.controller+=1
                choice={'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[
                    {'id':chosen['id'],'type':'function','function':{'name':chosen['name'],'arguments':json.dumps({**chosen['arguments'],'why':'MOCK: collect scoped information for this campaign.'})}}]}}
            else:
                inputs=json.loads(payload['messages'][1]['content'])
                if stage=='package_writer':candidate=data['initial_package']
                elif stage=='package_revision':candidate=data['revision_package']
                else:
                    from launchlens.offline_fixtures import fixture_package_review
                    candidate=fixture_package_review(data['initial_review' if inputs['binding']['draft_version']==1 else 'revision_review'],inputs['package'])
                choice={'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(candidate)}}
            value={'model':model['model_id'],'choices':[choice],'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}}
            return WireResponse(200,json.dumps(value).encode(),{'request-id':'MOCK'})
        return http


class FrozenDateTime(datetime):
    @classmethod
    def now(cls,tz=None):return NOW if tz is not None else NOW.replace(tzinfo=None)


class LivePreparationTests(unittest.TestCase):
    def setUp(self):
        self.clock=patch('launchlens.live_package.datetime',FrozenDateTime)
        self.clock.start();self.addCleanup(self.clock.stop)
        self.block=patch.object(socket.socket,'connect',side_effect=AssertionError('No live network in prep tests'))
        self.network=self.block.start();self.addCleanup(self.block.stop)
        self.addCleanup(lambda:self.assertEqual(self.network.call_count,0))
        self.project=patch('launchlens.live_package.project_writer_input',side_effect=project)
        self.project.start();self.addCleanup(self.project.stop)
        qualified=profile();qualified['hosted_schema_qualified']=True
        q=patch('launchlens.live_package.profile',return_value=qualified);q.start();self.addCleanup(q.stop)
        self.env=patch.dict('os.environ',{'LANGSMITH_TRACING':'true'})
        self.env.start();self.addCleanup(self.env.stop)

    def run_case(self, *, wire=None, permission_value=None, tools=None, store=None):
        wire=wire or Wire()
        run=LivePackageRun(permission() if permission_value is None else permission_value,KEYS,
            tools=tools or ReviewFixtureTools(),wire_factory=wire,store=store,now=NOW)
        return run,wire,run.execute(run.snapshot()['run_id'])

    def test_default_preflight_and_authorization_template_cannot_spend(self):
        plan=preflight();self.assertEqual(plan['generation_calls'],0);self.assertFalse(plan['credentials_read'])
        self.assertFalse(authorization_template()['owner_authorized'])
        self.assertEqual(plan['reservation_total_usd'],'0.6402048')
        self.assertEqual(sum(v['max_attempts'] for v in plan['roles'].values() if v['max_attempts'] is not None),17)
        self.assertEqual(plan['max_model_calls'],12);self.assertIsNone(plan['max_required_review_calls']) # Separate required reviews; no USD reset.
        with self.assertRaises(LiveGateError):validate_authorization(authorization_template(),now=NOW)

    def test_missing_invalid_scope_and_lower_ceiling_fail_before_credentials(self):
        for field,value in [('owner_authorized',False),('scope_sha256','0'*64),('aggregate_ceiling_usd','0.50'),
                            ('source_permissions_confirmed',False),('acknowledge_catalog_not_entitlement',False)]:
            bad=permission();bad[field]=value
            with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'authorization.json';path.write_text(json.dumps(bad));path.chmod(0o600)
                with patch('launchlens.live_package.read_selected_keys',side_effect=AssertionError('No credentials')) as keys:
                    with self.assertRaises(Exception):create_live_run(request(),authorization_path=path)
                    self.assertEqual(keys.call_count,0)

    def test_expired_profile_or_authorization_blocks(self):
        bad=permission();bad['expires_utc']=(NOW-timedelta(seconds=1)).isoformat()
        with self.assertRaises(LiveGateError):validate_authorization(bad,now=NOW)
        with self.assertRaises(LiveGateError):validate_authorization(permission(),now=NOW+timedelta(days=2))
        with self.assertRaises(LiveGateError):validate_authorization({**permission(),'aggregate_ceiling_usd':'1.01'},now=NOW)

    def test_private_authorization_permissions_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'authorization.json';p.write_text(json.dumps(permission()));p.chmod(0o644)
            with self.assertRaises(LiveGateError):read_authorization(p)
            p.chmod(0o600);alias=Path(tmp)/'alias';alias.symlink_to(p)
            with self.assertRaises(LiveGateError):read_authorization(alias)

    def test_full_live_profile_mocked_native_controller_writer_reviewer_revision(self):
        run,wire,state=self.run_case()
        self.assertEqual(state['mode'],'live_package');self.assertEqual(state['status'],'awaiting_human_review')
        self.assertEqual(set(state['drafts']),{'campaign_brief','linkedin','email','blog','ads'})
        self.assertEqual(len(wire.calls),6);self.assertEqual(len(run.guard.events),6)
        self.assertEqual(run.guard.counts,{'controller':4,'package_writer':1,'package_reviewer':1,'package_revision':0})
        after=run.revise(state['run_id'],'Remove unsupported intensity.',1,state['package']['package_sha256'])
        self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['package']['version'],2)
        self.assertEqual(len(wire.calls),8);self.assertEqual(after['turns'],8)
        self.assertEqual(run.guard.counts,{'controller':4,'package_writer':1,'package_reviewer':2,'package_revision':1})
        self.assertFalse(after['human_accepted']);self.assertFalse(after['package']['publishing_allowed'])
        self.assertLess(run.guard.cost,Decimal(run.guard.plan['reservation_total_usd']))

    def test_same_prompts_context_contract_and_added_completion_cap_only(self):
        run,wire,state=self.run_case()
        writer=next(c for c in wire.calls if c['messages'][0]['content']==load_package_prompt('package_writer'))
        self.assertEqual(writer['max_tokens'],8192);self.assertEqual(writer['max_completion_tokens'],8192)
        self.assertEqual(json.loads(writer['messages'][1]['content']),run.writer.calls[0]['model_input'])
        self.assertEqual(writer['response_format']['type'],'json_schema')
        self.assertNotIn('uniqueItems',json.dumps(writer['response_format']))
        self.assertEqual(run.writer.calls[0]['input']['writer_brief']['draft_constraints']['allowed_claim_ids'],['PROD-002','PROD-003'])

    def test_replay_refresh_and_snapshot_never_dispatch_again(self):
        run,wire,state=self.run_case()
        for _ in range(3):self.assertEqual(run.execute(state['run_id']),state)
        exposed=run.snapshot();exposed['request']['market_id']='IN'
        self.assertEqual(run.snapshot()['request']['market_id'],'US');self.assertEqual(len(wire.calls),6)

    def test_whole_run_and_role_caps_atomic_without_overlapping_calls(self):
        budget=RunBudget(permission(),now=NOW);budget.arm(request())
        def claim(_):
            try:return budget.claim('controller','0'*64)
            except LiveGateError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,[0,1]))
        self.assertEqual(sum(v is not None for v in results),1);self.assertEqual(budget.counts['controller'],1)
        event=next(v for v in results if v)
        value={'model':profile()['roles']['controller']['model_id'],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
        budget.complete(event,value)
        for _ in range(11):budget.complete(budget.claim('controller','1'*64),value)
        with self.assertRaises(LiveGateError):budget.claim('controller','2'*64)
        self.assertEqual(budget.counts['controller'],12)

    def test_reset_cannot_rearm_or_reuse_spending_authorization(self):
        run,wire,state=self.run_case();run.reset()
        self.assertTrue(run.guard.closed);self.assertIsNone(run.snapshot())
        with self.assertRaises(LiveGateError):run.guard.arm(request())
        with self.assertRaises(HarnessError):run.execute(state['run_id'])
        self.assertEqual(len(wire.calls),6)

    def test_revision_requires_both_owner_permission_and_feedback(self):
        approval=permission();approval['allow_explicit_revisions']=False
        run,wire,state=self.run_case(permission_value=approval)
        with self.assertRaises(LiveGateError):run.revise(state['run_id'],'Fix',1,state['package']['package_sha256'])
        self.assertEqual(len(wire.calls),6)

    def test_http_failure_raw_capture_and_no_retry_unknown_billing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ProtectedStore(Path(tmp)/'protected')
            wire=Wire(lambda p:WireResponse(429,b'{"error":"MOCK rate limit"}',{'request-id':'MOCK'}))
            run,wire,state=self.run_case(wire=wire,store=store)
            self.assertEqual(state['status'],'failed');self.assertTrue(run.guard.closed)
            self.assertEqual(len(wire.calls),1);self.assertEqual((store.path/'call-01-response.bin').read_bytes(),b'{"error":"MOCK rate limit"}')
            run.execute(state['run_id']);self.assertEqual(len(wire.calls),1)
            for p in store.path.iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
            self.assertEqual(store.path.stat().st_mode&0o777,0o700)

    def test_malformed_json_missing_usage_or_wrong_model_stops_without_retry(self):
        for body in [b'not json',b'{"model":"wrong","usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}',
                     b'{"model":"Qwen/Qwen3-30B-A3B-Instruct-2507"}']:
            wire=Wire(lambda p:WireResponse(200,body,{}));run,wire,state=self.run_case(wire=wire)
            self.assertEqual(state['status'],'failed');self.assertTrue(run.guard.closed);self.assertEqual(len(wire.calls),1)

    def test_reported_usage_above_reservation_stops(self):
        def excess(payload):
            n=profile()['roles']['controller']['context_tokens']+1
            return WireResponse(200,json.dumps({'model':payload['model'],'usage':{'prompt_tokens':n,'completion_tokens':1,'total_tokens':n+1}}).encode(),{})
        run,wire,state=self.run_case(wire=Wire(excess))
        self.assertEqual(state['status'],'failed');self.assertTrue(run.guard.closed)

    def test_transport_timeout_is_one_consumed_attempt(self):
        def timeout(_):raise TimeoutError('MOCK failure, never raw-logged')
        run,wire,state=self.run_case(wire=Wire(timeout))
        self.assertEqual(state['status'],'failed');self.assertEqual(len(wire.calls),1)
        self.assertTrue(run.guard.closed);self.assertEqual(run.guard.events[0]['status'],'stopped_no_retry')

    def test_credential_echo_redacted_in_raw_body_headers_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ProtectedStore(Path(tmp)/'protected')
            secret=KEYS['NOTION_API_KEY']
            run,wire,state=self.run_case(wire=Wire(lambda p:WireResponse(200,secret.encode(),{'request-id':secret})),store=store)
            self.assertEqual(state['status'],'failed')
            for p in store.path.iterdir():self.assertNotIn(secret.encode(),p.read_bytes())
            self.assertIn(b'REDACTED_CREDENTIAL',(store.path/'call-01-response.bin').read_bytes())

    def test_prompts_settings_models_and_action_registry_are_role_pinned(self):
        budget=RunBudget(permission(),now=NOW);budget.arm(request())
        transport=LiveTransport('controller',budget,KEYS,wire_factory=lambda *a:self.fail('No dispatch'))
        for payload in [{'model':'not-approved'}, {'model':profile()['roles']['controller']['model_id'],'temperature':1}]:
            with self.assertRaises(LiveGateError):transport(payload)
        self.assertFalse(budget.events)

    def test_tools_failure_cannot_turn_into_generation_or_demo_fallback(self):
        tools=ReviewFixtureTools();tools.fail='launch'
        run,wire,state=self.run_case(tools=tools)
        self.assertEqual(state['status'],'failed');self.assertFalse(state['drafts'])
        self.assertEqual(run.guard.counts['package_writer'],0)
        self.assertEqual(len(wire.calls),2);self.assertTrue(run.guard.closed)

    def test_factory_consumption_is_durable_and_no_provider_call_at_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'authorization.json';p.write_text(json.dumps(permission()));p.chmod(0o600)
            with patch('launchlens.live_package.ROOT',root),patch('launchlens.live_package.read_selected_keys',return_value=KEYS):
                run=create_live_run(request(),authorization_path=p)
                self.assertEqual(run.snapshot()['status'],'created');self.assertFalse(run.guard.events)
                with self.assertRaises(LiveGateError):create_live_run(request(),authorization_path=p)
                self.assertEqual(run.guard.counts['controller'],0)

    def test_revision_is_not_offered_without_budget_for_revision_and_review(self):
        run,wire,state=self.run_case();self.assertTrue(run.guard.can_revise())
        value={'model':profile()['roles']['controller']['model_id'],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
        # Consume task-call capacity while retaining the separate review reservation.
        for _ in range(7):run.guard.complete(run.guard.claim('controller','3'*64),value)
        self.assertTrue(run.guard.can_revise()) # Human commands do not need another controller call.
        run.guard.cost=Decimal(run.guard.permission['aggregate_ceiling_usd'])-Decimal('0.01')
        self.assertFalse(run.guard.can_revise());before=run.snapshot()
        with self.assertRaises(LiveGateError):run.revise(state['run_id'],'Fix',1,state['package']['package_sha256'])
        self.assertEqual(run.snapshot(),before);self.assertEqual(len(wire.calls),6)

    def test_reasoning_tokens_are_inside_completion_cap_not_added_twice(self):
        budget=RunBudget(permission(),now=NOW);budget.arm(request())
        event=budget.claim('package_writer','4'*64)
        value={'model':profile()['roles']['package_writer']['model_id'],'usage':{
            'prompt_tokens':100,'completion_tokens':50,'total_tokens':150,
            'completion_tokens_details':{'reasoning_tokens':20}}}
        budget.complete(event,value)
        self.assertEqual(budget.cost,Decimal('0.00025'))

    def test_inconsistent_reasoning_usage_stops_the_transport(self):
        def bad(payload):
            value={'model':payload['model'],'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150,
                'completion_tokens_details':{'reasoning_tokens':51}}}
            return WireResponse(200,json.dumps(value).encode(),{})
        run,wire,state=self.run_case(wire=Wire(bad))
        self.assertEqual(state['status'],'failed');self.assertTrue(run.guard.closed);self.assertEqual(len(wire.calls),1)

    def test_existing_http_transport_sends_one_exact_capped_request(self):
        run,wire,_=self.run_case();payload=deepcopy(wire.calls[0]);payload.pop('max_completion_tokens')
        budget=RunBudget(permission(),now=NOW);budget.arm(request())
        value={'model':payload['model'],'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}}
        class Response:
            status=200;headers={'request-id':'MOCK-HTTP'}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return json.dumps(value).encode()
        with patch('urllib.request.OpenerDirector.open',return_value=Response()) as open_request:
            answer=LiveTransport('controller',budget,KEYS)(payload)
        self.assertEqual(answer,value);self.assertEqual(open_request.call_count,1)
        req=open_request.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.tokenfactory.nebius.com/v1/chat/completions')
        sent=json.loads(req.data);self.assertEqual(sent['max_completion_tokens'],512)
        self.assertEqual(sent['messages'],payload['messages']);self.assertFalse(sent['store'])

    def test_identity_scope_and_private_notes_cannot_expand_authorization(self):
        with self.assertRaises(LiveGateError):
            LivePackageRun({**permission(),'request':{**request(),'product_id':'NIKE'}},KEYS,now=NOW)
        self.assertEqual(redact({'a':[KEYS['NEBIUS_API_KEY']]},tuple(KEYS.values())),{'a':['[REDACTED_CREDENTIAL]']})

    def test_attempt_without_an_execution_guard_is_rejected(self):
        from launchlens.agent_foundation import FoundationSession
        from launchlens.offline_fixtures import ScriptedReviewController,package_adapters
        writer,reviewer,reviser=package_adapters()
        with self.assertRaises(HarnessError):FoundationSession(ScriptedReviewController(),ReviewFixtureTools(),mode='live_package',
            writer=writer,reviewer=reviewer,revision_writer=reviser,voice_policy_id='simulated_brand_v1')


if __name__=='__main__':unittest.main()


class LiveRecoveryTests(unittest.TestCase):
    setUp = LivePreparationTests.setUp
    def test_known_usage_validation_failure_then_one_retry_retains_cost_and_searches(self):
        wire=Wire();original_factory=wire.__call__
        def factory(model,validator):
            http=original_factory(model,validator)
            def call(payload):
                response=http(payload)
                if payload['messages'][0]['content']==load_package_prompt('package_writer') and sum(c['messages'][0]['content']==load_package_prompt('package_writer') for c in wire.calls)==1:
                    value=json.loads(response.body);candidate=json.loads(value['choices'][0]['message']['content'])
                    candidate['linkedin']=13
                    value['choices'][0]['message']['content']=json.dumps(candidate)
                    return WireResponse(200,json.dumps(value).encode(),{})
                return response
            return call
        run=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=factory,now=NOW)
        state=run.execute(run.snapshot()['run_id']);self.assertEqual(state['status'],'draft_incomplete')
        self.assertTrue(run.session.can_retry_writer());self.assertFalse(run.guard.closed)
        cost=run.guard.cost;calls=deepcopy(run.tools.calls)
        after=run.retry_writer(state['run_id'])
        self.assertEqual(after['status'],'awaiting_human_review',str((after['draft_failure'],after['review_failure'],after['events'])));self.assertEqual(after['turns'],7)
        self.assertEqual(run.tools.calls,calls);self.assertGreater(run.guard.cost,cost)
        self.assertEqual(run.guard.counts['package_writer'],2);self.assertEqual(len(after['failure_history']),1)
        with self.assertRaises(HarnessError):run.retry_writer(state['run_id'])
        version=after['package']['version'];sha=after['package']['package_sha256']
        final=run.revise(state['run_id'],'Remove unsupported intensity',version,sha)
        self.assertEqual(final['turns'],9);self.assertEqual(final['review']['review_status'],'human_clearance_required')
        self.assertEqual(run.guard.counts['controller'],4);self.assertFalse(final['human_accepted'])
    def test_retry_requires_explicit_permission_and_known_billing(self):
        p=permission();p['allow_one_explicit_writer_retry']=False
        budget=RunBudget(p,now=NOW);budget.arm(request())
        event=budget.claim('package_writer','0'*64)
        budget.complete(event,{'model':profile()['roles']['package_writer']['model_id'],'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
        self.assertFalse(budget.can_retry_writer())
        with self.assertRaises(LiveGateError):budget.claim('package_writer','1'*64)
        p=permission();budget=RunBudget(p,now=NOW);budget.arm(request());budget.claim('package_writer','0'*64)
        self.assertFalse(budget.can_retry_writer());budget.stop();self.assertFalse(budget.can_retry_writer())
