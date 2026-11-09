"""Nebius-only mocked comparison invariants; no live inference or paid API calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from threading import Barrier,Lock
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
for p in ['src','tools']:sys.path.insert(0,str(ROOT/p))
import test_writer_context as helpers
import compare_writers as cli
from launchlens import writer_comparison as c
from launchlens import writer_providers as providers
from launchlens.live_research import dumps
from launchlens.writer_context import project_writer_input


MOCK_MODELS={'a':'SAFE_FIXTURE_MODEL_A','b':'SAFE_FIXTURE_MODEL_B','c':'SAFE_FIXTURE_MODEL_C'}


def setup():
    original,policy=helpers.fixture();count=[]
    def projector(value):count.append(1);return project_writer_input(value,policy=policy)
    bundle=c.assemble(original,projector=projector)
    config=c.load_config();base=deepcopy(config['models'][0]);models=[]
    # Explicit fake profiles/prices registered only within a network-blocked test.
    # None of these is an operational model, quote or authorization.
    for key,model_id in MOCK_MODELS.items():
        row=deepcopy(base);row.update(key=key,model_id=model_id,name='SAFE fixture '+key)
        row['pricing'].update(input_per_million_usd='1.00',output_per_million_usd='1.00',status='published')
        models.append(row)
    config['models']=models;config['single_selected_model']='a'
    return bundle,config,count


def approval_for(prepared):
    return {'owner_authorized':True,'authorization_reference':'SAFE MOCK AUTHORIZATION — NOT LIVE PERMISSION',
        'config_sha256':prepared['config_sha256'],'logical_input_sha256':prepared['logical_input_sha256'],
        'mode':prepared['mode'],'selected_models':[e['model']['key'] for e in prepared['entries']],
        'aggregate_cost_ceiling_usd':prepared['aggregate_cost_ceiling_usd'],'acknowledge_setting_differences':True,
        'models':{e['model']['key']:{'provider_request_sha256':e['provider_request_sha256'],
            'access_confirmed':True,'source_permissions_confirmed':True,'input_token_upper_bound':32768,
            'token_bound_evidence':'SAFE MOCK TOKEN BOUND — NOT REAL PROVIDER QUALIFICATION',
            'per_model_cost_ceiling_usd':e['model']['per_model_cost_ceiling_usd']} for e in prepared['entries']}}


def wire(model,candidate=None, *, usage=True,text=None):
    text=json.dumps(helpers.draft() if candidate is None else candidate) if text is None else text
    value={'model':model['model_id'],'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':text}}],
        'usage':{'prompt_tokens':1000,'completion_tokens':100,'total_tokens':1100}}
    if not usage:value.pop('usage')
    return c.WireResponse(200,json.dumps(value).encode(),{'x-request-id':'SAFE FIXTURE'})


class WriterComparisonTests(unittest.TestCase):
    def setUp(self):
        registry=patch.dict(c.REGISTERED_MODELS,MOCK_MODELS)
        registry.start();self.addCleanup(registry.stop)
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline test attempted network'))
        conn=blocker.start();self.addCleanup(blocker.stop);self.addCleanup(lambda:self.assertEqual(conn.call_count,0))

    def invoke(self,mutate=None,selected=None,mode='comparison'):
        bundle,config,count=setup();prepared=c.plan(bundle,config,mode=mode,selected=selected)
        calls=[];lock=Lock();barrier=Barrier(len(prepared['entries']))
        def factory(model):
            def transport(payload):
                with lock:calls.append((deepcopy(model),deepcopy(payload)))
                barrier.wait(timeout=3)
                return wire(model) if mutate is None else mutate(model,payload)
            return transport
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);out=Path(temp.name)/'result'
        result=c.run(bundle,config,mode=mode,selected=selected,execute=True,transport_kind='mock',approval=approval_for(prepared),transport_factory=factory,output=out)
        return result,calls,bundle,out,count

    def test_three_parallel_models_share_exact_task_but_distinct_provider_hashes(self):
        report,calls,bundle,out,count=self.invoke()
        self.assertEqual(len(calls),3);self.assertEqual(count,[1])
        self.assertEqual({r['logical_input_sha256'] for r in report['results']},{bundle['logical_input_sha256']})
        self.assertEqual(len({r['provider_request_sha256'] for r in report['results']}),3)
        for model,payload in calls:
            self.assertEqual(c.normalized_logical(payload,model['provider']),bundle['logical'])
            self.assertFalse(set(payload)&{'response_format','output_config','tools','tool_choice'})
        self.assertTrue(all(r['contract_status']=='accepted_unreviewed' for r in report['results']))
        self.assertTrue(all(not r['draft']['human_accepted'] and not r['draft']['publishing_allowed'] for r in report['results']))
        self.assertTrue((out/'report.json').exists());self.assertTrue((out/'review.md').exists())

    def test_single_default_and_disabled_selection_do_not_fan_out(self):
        bundle,config,_=setup()
        self.assertEqual([e['model']['key'] for e in c.plan(bundle,config)['entries']],['a'])
        config['models'][2]['enabled']=False
        self.assertEqual(len(c.plan(bundle,config,mode='comparison')['entries']),2)
        with self.assertRaises(c.ComparisonError):c.plan(bundle,config,mode='comparison',selected=['c'])
        with self.assertRaises(c.ComparisonError):c.plan(bundle,config,mode='single',selected=['a','b'])
        report,calls,_,_,_=self.invoke(selected=['b'],mode='single')
        self.assertEqual([m['key'] for m,p in calls],['b'])

    def test_offline_and_refresh_never_construct_transport(self):
        bundle,config,_=setup();calls=[]
        for _ in range(3):
            result=c.run(bundle,config,mode='comparison',transport_factory=lambda m:calls.append(m))
            self.assertEqual(result['provider_calls'],0)
        self.assertEqual(calls,[])

    def test_unresolved_quote_blocks_every_model_before_any_artifact_or_transport(self):
        bundle,config,_=setup();config['models'][1]['pricing'].update(status='unresolved',input_per_million_usd=None,output_per_million_usd=None)
        p=c.plan(bundle,config,mode='comparison');calls=[]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never'
            with self.assertRaisesRegex(c.ComparisonError,'pricing unresolved'):
                c.run(bundle,config,mode='comparison',execute=True,transport_kind='mock',approval=approval_for(p),transport_factory=lambda m:calls.append(m),output=out)
            self.assertFalse(out.exists());self.assertEqual(calls,[])

    def test_atomic_aggregate_reservation_and_no_duplicate_claims_under_contention(self):
        bundle,config,_=setup();p=c.plan(bundle,config,mode='comparison');a=approval_for(p);ledger=c.Reservation()
        def reserve():
            try:return ledger.reserve(p,a)
            except c.ComparisonError:return None
        with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:reserve(),range(6)))
        self.assertEqual(sum(v is not None for v in results),1)
        self.assertEqual(ledger.total,Decimal('0.10444800'))
        def claim():
            try:ledger.claim('a');return True
            except c.ComparisonError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:claim(),range(8)))
        self.assertEqual(sum(results),1)

    def test_missing_permission_bounds_or_ceiling_denies_whole_run(self):
        bundle,config,_=setup();p=c.plan(bundle,config,mode='comparison')
        changes=[lambda a:a.update(owner_authorized=False),lambda a:a.update(aggregate_cost_ceiling_usd='0.01'),
            lambda a:a['models']['a'].update(per_model_cost_ceiling_usd='0.01'),
            lambda a:a['models']['a'].update(input_token_upper_bound=None),
            lambda a:a['models']['b'].update(source_permissions_confirmed=False),
            lambda a:a['models']['b'].update(access_confirmed=False),
            lambda a:a.update(acknowledge_setting_differences=False),lambda a:a.update(logical_input_sha256='wrong')]
        for change in changes:
            a=approval_for(p);change(a)
            with self.subTest(change=changes.index(change)),self.assertRaises(c.ComparisonError):c.Reservation().reserve(p,a)

    def test_rejection_and_transport_failure_preserve_other_outputs(self):
        bad=helpers.draft();bad['claim_references'].append({'content_field':'cta','claim_ids':[]})
        def provider(model,payload):
            if model['key']=='c':raise RuntimeError('SECRET_EXCEPTION_SHOULD_NOT_APPEAR')
            return wire(model,bad if model['key']=='b' else None)
        report,calls,bundle,out,_=self.invoke(provider)
        rows={r['key']:r for r in report['results']}
        self.assertEqual(rows['a']['contract_status'],'accepted_unreviewed')
        self.assertEqual(rows['b']['diagnostic']['field_path'],'claim_references.1.claim_ids')
        self.assertEqual(rows['b']['citation_findings']['empty_entry_indexes'],[1])
        self.assertEqual(rows['c']['execution_status'],'failed_or_unknown')
        self.assertEqual(rows['c']['billing_status'],'unknown_reservation_retained')
        self.assertEqual(len(calls),3)
        self.assertTrue(all((out/(k+'-result.json')).exists() for k in rows))
        self.assertNotIn('SECRET_EXCEPTION_SHOULD_NOT_APPEAR',''.join(p.read_text() for p in out.iterdir()))

    def test_malformed_candidate_preserved_before_parsing_without_repair(self):
        report,_,_,out,_=self.invoke(lambda m,p:wire(m,text='not JSON'))
        for r in report['results']:
            self.assertEqual(r['response_content'],'not JSON');self.assertEqual(r['contract_status'],'invalid_json')
            self.assertEqual(r['diagnostic']['stage'],'candidate_json')
            self.assertIn(b'not JSON',(out/(r['key']+'-response.bin')).read_bytes())

    def test_original_authority_rejects_valid_but_ineligible_claim(self):
        bad=helpers.draft();bad['claim_references'][0]['claim_ids'].append('PROD-001')
        report,_,_,_,_=self.invoke(lambda m,p:wire(m,bad))
        for r in report['results']:
            self.assertEqual(r['diagnostic']['rule'],'invalid_claim_reference')
            self.assertEqual(r['citation_findings']['ineligible_ids'],['PROD-001'])

    def test_usage_missing_reasoning_or_over_budget_is_fail_closed_and_raw_retained(self):
        for kind in ['missing','over','reasoning']:
            def provider(m,p):
                response=wire(m,usage=kind!='missing')
                if kind!='missing':
                    v=json.loads(response.body)
                    if kind=='over':v['usage']['prompt_tokens']=32769
                    else:v['usage']['completion_tokens_details']={'reasoning_tokens':2}
                    response=replace(response,body=json.dumps(v).encode())
                return response
            report,_,_,out,_=self.invoke(provider)
            for r in report['results']:
                self.assertEqual(r['billing_status'],'unknown_reservation_retained')
                self.assertNotIn('draft',r);self.assertTrue((out/(r['key']+'-response.bin')).exists())

    def test_consumed_output_blocks_all_requests_on_second_execution(self):
        report,calls,bundle,out,_=self.invoke();config=setup()[1];p=c.plan(bundle,config,mode='comparison')
        with self.assertRaises(FileExistsError):
            c.run(bundle,config,mode='comparison',execute=True,transport_kind='mock',approval=approval_for(p),transport_factory=lambda m:self.fail('retry'),output=out)
        self.assertEqual(len(calls),3)

    def test_config_credentials_unknown_fields_and_duplicate_selection_rejected(self):
        bundle,config,_=setup();config['api_key']='DO_NOT_STORE'
        with self.assertRaises(c.ComparisonError):c.check_config(config)
        with self.assertRaises(c.ComparisonError):c.plan(bundle,setup()[1],mode='comparison',selected=['a','a'])
        config=setup()[1];config['models'][0]['model_id']='silent-substitute'
        with self.assertRaises(c.ComparisonError):c.check_config(config)

    def test_logical_binding_mutation_fails_before_dispatch(self):
        bundle,config,_=setup();bundle['logical']['user']='Changed evidence'
        with self.assertRaises(c.ComparisonError):c.plan(bundle,config)

    def test_actual_raw_response_modes_and_provider_prompt_translation(self):
        _,calls,_,out,_=self.invoke()
        self.assertEqual(out.stat().st_mode&0o777,0o700)
        for p in out.iterdir():self.assertEqual(p.stat().st_mode&0o777,0o600)
        for model,payload in calls:
            self.assertEqual(model['provider'],'nebius')
            self.assertEqual(payload['max_tokens'],2048);self.assertEqual(payload['temperature'],0)
            self.assertFalse(payload['stream']);self.assertFalse(payload['store'])
            self.assertEqual(set(payload),{'model','messages','max_tokens','temperature','stream','store'})

    def test_http_transport_one_attempt_no_credentials_in_captured_bytes(self):
        config=c.load_config();model=config['models'][0];key='SAFE_SECRET_KEY_123456'
        class Reply:
            status=200;headers={'x-request-id':'SAFE request'}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return ('echo '+key).encode()
        class Opener:
            def __init__(self):self.calls=[]
            def open(self,request,timeout):self.calls.append(request);return Reply()
        opener=Opener()
        with patch.object(providers.urllib.request,'build_opener',return_value=opener):
            payload=c.translate(setup()[0]['logical'],model)
            http=providers.ProviderHTTP(model,key);response=http(payload)
            with self.assertRaises(c.ComparisonError):http(payload)
        self.assertEqual(len(opener.calls),1);self.assertTrue(response.credential_redacted)
        self.assertNotIn(key.encode(),response.body);self.assertEqual(response.headers,{'x-request-id':'SAFE request'})

    def test_offline_cli_refresh_reads_no_credentials_or_providers(self):
        bundle,_,_=setup()
        args=['--input','UNUSED','--source-state','UNUSED','--mode','comparison']
        with patch.object(cli,'verified_inputs',return_value=bundle['authoritative']),patch.object(cli,'assemble',return_value=bundle), \
             patch.object(cli,'read_provider_keys') as keys,patch.object(cli,'ProviderHTTP') as http,patch('sys.stdout',io.StringIO()):
            cli.main(args);cli.main(args)
            keys.assert_not_called();http.assert_not_called()

    def test_keys_are_selected_only_and_never_written_to_configuration(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{},clear=True):
            path=Path(d)/'.env';path.write_text('NEBIUS_API_KEY=SAFE_NEBIUS_KEY_12345\nUNRELATED_SECRET=HIDDEN\n');path.chmod(0o600)
            values=providers.read_provider_keys([c.load_config()['models'][0]],path)
            self.assertEqual(set(values),{'NEBIUS_API_KEY'})
            self.assertNotIn(values['NEBIUS_API_KEY'],c.CONFIG.read_text())
            path.chmod(0o644)
            with self.assertRaises(c.ComparisonError):providers.read_provider_keys([c.load_config()['models'][0]],path)

    def test_disabled_model_is_never_constructed_or_called_in_executing_mock_mode(self):
        bundle,config,_=setup();config['models'][2]['enabled']=False
        prepared=c.plan(bundle,config,mode='comparison');calls=[]
        def factory(m):
            calls.append(m['key']);return lambda p:wire(m)
        with tempfile.TemporaryDirectory() as d:
            result=c.run(bundle,config,mode='comparison',execute=True,transport_kind='mock',approval=approval_for(prepared),
                transport_factory=factory,output=Path(d)/'run')
        self.assertEqual(sorted(calls),['a','b']);self.assertEqual(len(result['results']),2)

    def test_duplicate_citation_remains_rejected_without_merging(self):
        bad=helpers.draft();bad['claim_references'].append(deepcopy(bad['claim_references'][0]))
        report,_,_,_,_=self.invoke(lambda m,p:wire(m,bad))
        for row in report['results']:
            self.assertEqual(row['diagnostic']['rule'],'duplicate_field_reference')
            self.assertEqual(row['citation_findings']['duplicate_fields'],['body'])
            self.assertEqual(row['candidate'],bad)

    def test_non_json_provider_body_and_error_status_are_preserved(self):
        for response in [c.WireResponse(200,b'broken JSON',{}),c.WireResponse(429,b'{"error":"SAFE rate limit"}',{})]:
            report,_,_,out,_=self.invoke(lambda m,p:response)
            for row in report['results']:
                self.assertEqual((out/(row['key']+'-response.bin')).read_bytes(),response.body)
                self.assertNotIn('draft',row);self.assertIsNone(row['estimated_cost_usd'])

    def test_fake_model_evidence_does_not_replace_original_authority(self):
        bundle,config,_=setup()
        bundle['projected']['research_context']['claims'].append({'claim_id':'PROD-001','authority':'public_product_facts','text':'FORGED model view'})
        bundle['logical']['user']=dumps(bundle['projected'])
        bundle['logical_input_sha256']=c.digest(bundle['logical'])
        bundle['projection_manifest']['model_input_sha256']=c.digest(bundle['projected'])
        prepared=c.plan(bundle,config,mode='single');bad=helpers.draft()
        bad['claim_references'][0]['claim_ids']=['PROD-001']
        with tempfile.TemporaryDirectory() as d:
            result=c.run(bundle,config,mode='single',execute=True,transport_kind='mock',approval=approval_for(prepared),
                transport_factory=lambda m:lambda p:wire(m,bad),output=Path(d)/'run')
        self.assertEqual(result['results'][0]['diagnostic']['rule'],'invalid_claim_reference')
        self.assertEqual(set(bundle['authoritative']['draft_constraints']['allowed_claim_ids']),{'PROD-002','PROD-003'})

    def test_provider_refuses_unreviewed_payload_before_open(self):
        model=c.load_config()['models'][0];payload=c.translate(setup()[0]['logical'],model)
        payload['response_format']={'type':'json_object'}
        with patch.object(providers.urllib.request,'build_opener') as opener:
            http=providers.ProviderHTTP(model,'SAFE_SECRET_KEY_123456')
            with self.assertRaises(c.ComparisonError):http(payload)
            opener.return_value.open.assert_not_called()

    def test_production_registry_is_nebius_only_existing_baseline(self):
        config=c.load_config()
        self.assertEqual(config['version'],'2.0')
        self.assertEqual(len(config['models']),1)
        self.assertEqual(config['models'][0]['key'],'qwen30')
        self.assertEqual(config['models'][0]['provider'],'nebius')
        self.assertEqual(config['models'][0]['model_id'],'Qwen/Qwen3-30B-A3B-Instruct-2507')
        self.assertEqual(config['models'][0]['pricing']['status'],'unresolved')
        bundle=setup()[0]
        for key in ['gpt','sonnet','llama','qwen235','gptoss']:
            with self.subTest(key=key),self.assertRaises(c.ComparisonError):
                c.plan(bundle,config,mode='comparison',selected=[key])

    def test_old_approval_cannot_authorize_nebius_model(self):
        bundle,config,_=setup();prepared=c.plan(bundle,config,mode='single')
        old=approval_for(prepared)
        old.update(config_sha256='5f281da145008946cb8c168ac714711ba3b6f3ed785c8dbf530d719425cc4785')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'must-not-exist'
            with self.assertRaises(c.ComparisonError):
                c.run(bundle,config,mode='single',execute=True,transport_kind='mock',approval=old,
                    transport_factory=lambda m:self.fail('Old approval reached transport'),output=out)
            self.assertFalse(out.exists())

    def test_removed_cli_routes_fail_before_inputs_credentials_or_transport(self):
        args=['--input','UNUSED','--source-state','UNUSED','--mode','comparison','--select','gpt','sonnet']
        with patch.object(cli,'verified_inputs') as source,patch.object(cli,'read_provider_keys') as keys, \
             patch.object(cli,'ProviderHTTP') as http,patch('sys.stderr',io.StringIO()):
            with self.assertRaises(SystemExit):cli.main(args)
            source.assert_not_called();keys.assert_not_called();http.assert_not_called()
