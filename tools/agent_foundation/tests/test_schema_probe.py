from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('probe',ROOT/'tools/probe_package_schema.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
from launchlens.offline_fixtures import package_cases
import json
class ProbeTests(unittest.TestCase):
    def test_actual_schema_and_constraints(self):
        p=probe.request(probe.MODELS[1])
        self.assertEqual(p['response_format'],probe.response_format(probe.package_schema()))
        self.assertNotIn('uniqueItems',json.dumps(p['response_format']))
        self.assertEqual(p['max_completion_tokens'],8192)
        self.assertEqual(p['response_format']['type'],'json_schema')
    def test_nested_pass_strings_and_empty_references_fail(self):
        value={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(package_cases()['initial_package'])}}]}
        self.assertTrue(probe.inspect(value)['structure_pass'])
        candidate=package_cases()['initial_package'];candidate['linkedin']=json.dumps(candidate['linkedin'])
        value['choices'][0]['message']['content']=json.dumps(candidate)
        self.assertFalse(probe.inspect(value)['structure_pass'])
        candidate=package_cases()['initial_package'];candidate['linkedin']['claim_references'][0]['claim_ids']=[]
        value['choices'][0]['message']['content']=json.dumps(candidate)
        self.assertFalse(probe.inspect(value)['structure_pass'])
    def test_default_request_preparation_has_no_network(self):
        with patch('socket.socket.connect',side_effect=AssertionError('offline')):
            for m in probe.MODELS:probe.request(m)
if __name__=='__main__':unittest.main()

class ProbeSpendingTests(unittest.TestCase):
    def test_http_error_keeps_receipt_and_stops_all_further_models(self):
        import tempfile
        from launchlens.writer_comparison import WireResponse
        with tempfile.TemporaryDirectory() as tmp, patch.object(probe,'OUTPUT',Path(tmp)/'probe'), patch.object(probe,'read_selected_keys',return_value={'NEBIUS_API_KEY':'SAFE-TEST-KEY-ONLY'}), patch.object(probe,'ProviderHTTP') as http:
            http.return_value.return_value=WireResponse(400,b'{"error":"unsupported schema"}',{})
            with patch('builtins.print'):probe.execute()
            self.assertEqual(http.call_count,1)
            self.assertTrue((probe.OUTPUT/'probe-01-response.bin').exists())
            self.assertEqual(json.loads((probe.OUTPUT/'stopped.json').read_text())['reason'],'unknown_transport_or_billing')
            self.assertFalse((probe.OUTPUT/'probe-02-request.json').exists())
            with self.assertRaises(FileExistsError):probe.execute()
            self.assertEqual(http.call_count,1)


class AuditedProbeTests(unittest.TestCase):
    def setup_run(self,tmp,http):
        from launchlens.writer_comparison import WireResponse
        old=Path(tmp)/'old';old.mkdir()
        (old/'stopped.json').write_text(json.dumps({'reason':'unknown_transport_or_billing','reservation_retained_usd':'0.0278528'}))
        self.enterContext(patch.object(probe,'OUTPUT',old))
        self.enterContext(patch.object(probe,'AUTHORIZED_OUTPUT',Path(tmp)/'new'))
        self.enterContext(patch.object(probe,'schema_audit',return_value={'offline_pass':True}))
        self.enterContext(patch.object(probe,'read_selected_keys',return_value={'NEBIUS_API_KEY':'SAFE-TEST-KEY-ONLY'}))
        self.enterContext(patch.object(probe,'ProviderHTTP',side_effect=lambda *a,**k:http))
        self.enterContext(patch('builtins.print'))
        return WireResponse

    def test_two_independent_models_no_fallback_and_prior_hold_retained(self):
        import tempfile
        calls=[]
        def http(payload):
            calls.append(payload)
            return response(200,json.dumps({'model':payload['model'],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(package_cases()['initial_package'])}}],
                'usage':{'prompt_tokens':100,'completion_tokens':100,'total_tokens':200}}).encode(),{})
        with tempfile.TemporaryDirectory() as tmp:
            response=self.setup_run(tmp,http)
            with patch.object(probe,'inspect',return_value={'structure_pass':True}):probe.execute(audited=True)
            self.assertEqual([p['model'] for p in calls],[m[1] for m in probe.MODELS])
            summary=json.loads((probe.AUTHORIZED_OUTPUT/'summary.json').read_text())
            self.assertEqual(summary['prior_reservation_retained_usd'],'0.0278528')
            self.assertLessEqual(probe.Decimal(summary['total_accounted_usd']),probe.CAP)
            self.assertTrue((probe.AUTHORIZED_OUTPUT/'probe-02-response.bin').exists())
            with self.assertRaises(FileExistsError):probe.execute(audited=True)
            self.assertEqual(len(calls),2)

    def test_conditional_single_channel_and_independent_failed_result(self):
        import tempfile
        calls=[]
        def http(payload):
            calls.append(payload)
            return response(200,json.dumps({'model':payload['model'],'usage':{'prompt_tokens':100,'completion_tokens':100,'total_tokens':200}}).encode(),{})
        with tempfile.TemporaryDirectory() as tmp:
            response=self.setup_run(tmp,http)
            with patch.object(probe,'inspect',side_effect=[{'structure_pass':True},{'structure_pass':False,'provider_schema_pass':False},{'structure_pass':True}]):probe.execute(audited=True)
            self.assertEqual(len(calls),3)
            self.assertEqual(calls[2]['response_format'],probe.response_format(probe.model_output_schema('linkedin')))
            self.assertFalse(json.loads((probe.AUTHORIZED_OUTPUT/'probe-02-result.json').read_text())['structure_pass'])
            self.assertTrue((probe.AUTHORIZED_OUTPUT/'probe-02-response.bin').exists())

    def test_old_reserve_can_block_second_model(self):
        import tempfile
        calls=[]
        def http(payload):
            calls.append(payload)
            return response(200,json.dumps({'model':payload['model'],'usage':{'prompt_tokens':253952,'completion_tokens':8192,'total_tokens':262144}}).encode(),{})
        with tempfile.TemporaryDirectory() as tmp:
            response=self.setup_run(tmp,http)
            with patch.object(probe,'inspect',return_value={'structure_pass':True}):probe.execute(audited=True)
            self.assertEqual(len(calls),1)
            self.assertEqual(json.loads((probe.AUTHORIZED_OUTPUT/'stopped.json').read_text())['reason'],'insufficient_remaining_reservation')

    def test_audit_failure_happens_before_credentials_or_http(self):
        with patch.object(probe,'schema_audit',side_effect=ValueError('schema invalid')),patch.object(probe,'read_selected_keys') as keys,patch.object(probe,'ProviderHTTP') as http:
            with self.assertRaises(ValueError):probe.execute(audited=True)
            keys.assert_not_called();http.assert_not_called()


class IndependentSchemaTests(unittest.TestCase):
    def test_metaschema_and_provider_backend_gap(self):
        try:import jsonschema
        except ImportError:self.skipTest('Independent audit uses existing tools/ui environment; no new dependency')
        with patch('socket.socket.connect',side_effect=AssertionError('offline')):
            audit=probe.schema_audit()
        self.assertEqual(len(audit['schemas']),7)
        self.assertTrue(all(s['metaschema_pass'] for s in audit['schemas'].values()))
        self.assertTrue(all('uniqueItems' not in s['provider_keywords'] for s in audit['schemas'].values()))
        backend=probe.package_schema();projected=probe.response_format(backend)['json_schema']['schema']
        original=deepcopy(backend);candidate=package_cases()['initial_package']
        self.assertTrue(jsonschema.Draft202012Validator(projected).is_valid(candidate))
        candidate['linkedin']['claim_references'][0]['claim_ids']=['PROD-002','PROD-002']
        self.assertTrue(jsonschema.Draft202012Validator(projected).is_valid(candidate))
        self.assertFalse(jsonschema.Draft202012Validator(backend).is_valid(candidate))
        self.assertEqual(backend,original)
        for mutate in ('empty','string'):
            bad=package_cases()['initial_package']
            if mutate=='empty':bad['linkedin']['claim_references'][0]['claim_ids']=[]
            else:bad['linkedin']=json.dumps(bad['linkedin'])
            self.assertFalse(jsonschema.Draft202012Validator(projected).is_valid(bad))


class ReviewerProbeTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        if not importlib.util.find_spec('jsonschema'):self.skipTest('Independent schema checks use existing UI environment')
        self.enterContext(patch('socket.socket.connect',side_effect=AssertionError('offline')))
        self.candidate=package_cases()['initial_package']
        self.source_request=probe.request(probe.MODELS[1])
        self.source_response={'model':probe.MODELS[1][1],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.candidate)}}]}
        self.payload,self.inputs=probe.reviewer_request(self.source_request,self.source_response)

    def valid_review(self):
        from launchlens.content_review import DIMENSIONS
        return {name:{'assessments':[{'dimension':d,'status':'pass'} for d in DIMENSIONS],'findings':[]} for name in probe.FORMATS}

    def test_production_prompt_schema_original_package_and_no_target_hints(self):
        self.assertEqual(self.payload['messages'][0]['content'],(ROOT/'src/launchlens/prompts/package_reviewer_v2.txt').read_text())
        self.assertEqual(self.payload['response_format'],probe.response_format(probe.historical_review_schema()))
        self.assertEqual(self.payload['max_completion_tokens'],4096)
        self.assertEqual(self.inputs['package'],self.candidate)
        self.assertEqual(self.inputs['writing_instructions'],probe.load_package_prompt('package_writer'))
        self.assertNotIn('requested_phrase_coverage',self.payload['messages'][1]['content'])
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(self.payload['response_format']['json_schema']['schema'])
        self.assertEqual(self.inputs['writer_brief']['claims'],json.loads(self.source_request['messages'][1]['content'])['claims'])

    def test_independent_backend_checks_and_raw_finding_capture(self):
        result=self.valid_review()
        result['linkedin']['assessments'][0]['status']='needs_changes'
        result['linkedin']['findings']=[{'dimension':'grounding','content_field':'hook',
            'quote':self.candidate['linkedin']['content']['hook'],'severity':'blocking','rationale':'SAFE fixture observation',
            'suggested_change':'SAFE fixture correction','claim_ids':[]}]
        response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}]}
        checked=probe.inspect_review(response,self.inputs)
        self.assertTrue(checked['schema_pass']);self.assertTrue(checked['backend_pass'])
        self.assertEqual(checked['findings_by_severity'],{'blocking':1})
        self.assertFalse(checked['content_accepted'])
        result['linkedin']['findings'][0]['quote']='not in the original draft'
        response['choices'][0]['message']['content']=json.dumps(result)
        rejected=probe.inspect_review(response,self.inputs)
        self.assertTrue(rejected['schema_pass']);self.assertFalse(rejected['backend_pass'])
        self.assertEqual(rejected['backend_diagnostic']['code'],'invalid_quote')
        self.assertEqual(len(rejected['findings']),1)

    def test_one_request_receipt_retained_cap_and_guard(self):
        import tempfile
        from launchlens.writer_comparison import WireResponse
        with tempfile.TemporaryDirectory() as tmp:
            previous=Path(tmp)/'previous';previous.mkdir()
            (previous/'summary.json').write_text(json.dumps({'requests_attempted':2,'total_accounted_usd':'0.0335936'}))
            self.enterContext(patch.object(probe,'AUTHORIZED_OUTPUT',previous))
            self.enterContext(patch.object(probe,'REVIEWER_OUTPUT',Path(tmp)/'reviewer'))
            self.enterContext(patch.object(probe,'reviewer_request',return_value=(self.payload,self.inputs)))
            self.enterContext(patch.object(probe,'read_selected_keys',return_value={'NEBIUS_API_KEY':'SAFE-TEST-KEY-ONLY'}))
            wire=self.enterContext(patch.object(probe,'ProviderHTTP'))
            response={'model':probe.MODELS[1][1],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.valid_review())}}],
                'usage':{'prompt_tokens':100,'completion_tokens':100,'total_tokens':200}}
            wire.return_value.return_value=WireResponse(200,json.dumps(response).encode(),{})
            with patch('builtins.print'):probe.execute_reviewer()
            self.assertEqual(wire.call_count,1);self.assertEqual(wire.return_value.call_count,1)
            self.assertEqual(wire.call_args.kwargs['timeout_seconds'],120)
            data=json.loads((probe.REVIEWER_OUTPUT/'result.json').read_text())
            self.assertTrue(data['backend_pass']);self.assertEqual(data['total_accounted_usd'],'0.0339936')
            self.assertEqual(data['prior_unknown_reservation_retained_usd'],'0.0278528')
            self.assertTrue((probe.REVIEWER_OUTPUT/'response.bin').exists())
            with self.assertRaises(FileExistsError):probe.execute_reviewer()
            self.assertEqual(wire.call_count,1)

    def test_default_transport_deadline_unchanged_and_override_bounded(self):
        from launchlens.writer_providers import ProviderHTTP
        m={'provider':'nebius','model_id':probe.MODELS[1][1]}
        self.assertEqual(ProviderHTTP(m,'SAFE-TEST-KEY-ONLY').timeout_seconds,45)
        self.assertEqual(ProviderHTTP(m,'SAFE-TEST-KEY-ONLY',timeout_seconds=120).timeout_seconds,120)
        for bad in [0,-1,181,float('inf'),float('nan'),True]:
            with self.assertRaises(Exception):ProviderHTTP(m,'SAFE-TEST-KEY-ONLY',timeout_seconds=bad)
