"""One Hermes diagnostic prepared offline; all provider calls are safe mocks."""
from copy import deepcopy
from decimal import Decimal
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import test_writer_comparison as shared
from launchlens import writer_comparison as c
from launchlens import writer_providers as providers
import compare_writers as cli


class HermesPreparationTests(unittest.TestCase):
    def setUp(self):
        registry=patch.dict(c.REGISTERED_MODELS,shared.MOCK_MODELS)
        registry.start();self.addCleanup(registry.stop)
        blocked=patch.object(socket.socket,'connect',side_effect=AssertionError('No network in offline tests'))
        connection=blocked.start();self.addCleanup(blocked.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))
        self.bundle=shared.setup()[0]
        self.config=c.load_config(c.HERMES_CONFIG)

    def attempt(self,candidate=None,response=None):
        prepared=c.plan(self.bundle,self.config);approval=shared.approval_for(prepared)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        out=Path(temporary.name)/'run';calls=[]
        def factory(model):
            def transport(payload):
                calls.append(deepcopy(payload))
                return response if response is not None else shared.wire(model,candidate)
            return transport
        result=c.run(self.bundle,self.config,execute=True,transport_kind='mock',approval=approval,
                     transport_factory=factory,output=out)
        return result,calls,out,approval

    def test_candidate_is_explicit_single_profile_and_default_stays_qwen(self):
        baseline=c.load_config()
        self.assertEqual(baseline['single_selected_model'],'qwen30')
        self.assertEqual([m['key'] for m in baseline['models']],['qwen30'])
        self.assertEqual(self.config['max_requests'],1)
        self.assertEqual(self.config['single_selected_model'],'hermes')
        self.assertEqual([m['key'] for m in self.config['models']],['hermes'])
        self.assertEqual(self.config['aggregate_cost_ceiling_usd'],'0.05')
        with self.assertRaises(c.ComparisonError):c.plan(self.bundle,baseline,selected=['hermes'])
        with self.assertRaises(c.ComparisonError):c.plan(self.bundle,self.config,selected=['qwen30'])

    def test_only_model_changes_in_provider_body(self):
        before=c.translate(self.bundle['logical'],c.load_config()['models'][0])
        after=c.translate(self.bundle['logical'],self.config['models'][0])
        self.assertEqual(after['model'],'NousResearch/Hermes-4-405B')
        self.assertEqual({k:v for k,v in before.items() if k!='model'},
                         {k:v for k,v in after.items() if k!='model'})
        self.assertEqual(c.normalized_logical(after,'nebius'),self.bundle['logical'])
        self.assertNotIn('response_format',after)
        self.assertNotIn('reasoning_effort',after)
        self.assertNotIn('extra_body',after)

    def test_one_request_limit_rejects_mixed_config_and_selection(self):
        bad=deepcopy(self.config);bad['models'].append(deepcopy(c.load_config()['models'][0]))
        with self.assertRaises(c.ComparisonError):c.check_config(bad)
        with self.assertRaises(c.ComparisonError):c.plan(self.bundle,self.config,selected=['hermes','qwen30'])
        bad=deepcopy(self.config);bad['max_requests']=True
        with self.assertRaises(c.ComparisonError):c.check_config(bad)

    def test_offline_refresh_never_calls_keys_or_provider(self):
        args=['--profile','hermes','--input','UNUSED','--source-state','UNUSED','--select','hermes']
        with patch.object(cli,'verified_inputs',return_value=self.bundle['authoritative']), \
             patch.object(cli,'assemble',return_value=self.bundle),patch.object(cli,'read_provider_keys') as keys, \
             patch.object(cli,'ProviderHTTP') as http,patch('sys.stdout',io.StringIO()):
            for _ in range(2):
                result=cli.main(args)
                self.assertEqual(result['provider_calls'],0)
                self.assertEqual([row['key'] for row in result['results']],['hermes'])
            keys.assert_not_called();http.assert_not_called()

    def test_cli_rejects_mixed_or_comparison_mode_before_inputs_or_keys(self):
        for tail in [['--mode','comparison'],['--select','qwen30'],['--select','hermes','qwen30']]:
            with patch.object(cli,'verified_inputs') as inputs,patch.object(cli,'read_provider_keys') as keys:
                with self.assertRaises(c.ComparisonError):
                    cli.main(['--profile','hermes','--input','UNUSED','--source-state','UNUSED']+tail)
                inputs.assert_not_called();keys.assert_not_called()

    def test_one_accepted_mock_stays_unreviewed_with_original_authority(self):
        result,calls,out,_=self.attempt()
        self.assertEqual(len(calls),1)
        self.assertEqual(result['attempted_models'],['hermes'])
        row=result['results'][0]
        self.assertEqual(row['contract_status'],'accepted_unreviewed')
        self.assertFalse(row['draft']['human_accepted']);self.assertFalse(row['draft']['publishing_allowed'])
        self.assertTrue((out/'hermes-response.bin').is_file())
        bad=shared.helpers.draft();bad['claim_references'][0]['claim_ids']=['PROD-001']
        rejected,_,_,_=self.attempt(candidate=bad)
        self.assertEqual(rejected['results'][0]['diagnostic']['rule'],'invalid_claim_reference')

    def test_empty_citation_is_preserved_and_never_repaired_or_retried(self):
        bad=shared.helpers.draft();bad['claim_references'].append({'content_field':'cta','claim_ids':[]})
        result,calls,out,approval=self.attempt(candidate=bad);row=result['results'][0]
        self.assertEqual(len(calls),1);self.assertEqual(row['candidate'],bad)
        self.assertEqual(row['diagnostic']['field_path'],'claim_references.1.claim_ids')
        self.assertEqual(row['diagnostic']['rule'],'array_length_invalid')
        self.assertEqual(result['automatic_retries'],0);self.assertEqual(result['automatic_repairs'],0)
        with self.assertRaises(FileExistsError):
            c.run(self.bundle,self.config,execute=True,transport_kind='mock',approval=approval,
                  transport_factory=lambda m:self.fail('No second call'),output=out)

    def test_reservation_is_0038912_and_missing_access_or_approval_blocks(self):
        p=c.plan(self.bundle,self.config);approval=shared.approval_for(p);ledger=c.Reservation()
        ledger.reserve(p,approval);self.assertEqual(ledger.total,Decimal('0.038912'))
        changes=[lambda a:a.update(owner_authorized=False),
                 lambda a:a['models']['hermes'].update(access_confirmed=False),
                 lambda a:a['models']['hermes'].update(input_token_upper_bound=None),
                 lambda a:a.update(config_sha256='OLD_APPROVAL')]
        for change in changes:
            a=deepcopy(approval);change(a)
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'never'
                with self.assertRaises(c.ComparisonError):
                    c.run(self.bundle,self.config,execute=True,transport_kind='mock',approval=a,
                          transport_factory=lambda m:self.fail('No transport'),output=out)
                self.assertFalse(out.exists())

    def test_reasoning_deviation_and_transport_failure_preserve_full_raw_response(self):
        model=self.config['models'][0]
        value=json.loads(shared.wire(model).body)
        value['usage']['completion_tokens_details']={'reasoning_tokens':8}
        value['choices'][0]['message']['reasoning_content']='SAFE MOCK REASONING'
        raw=json.dumps(value).encode();response=c.WireResponse(200,raw,{})
        result,calls,out,_=self.attempt(response=response)
        self.assertEqual(len(calls),1)
        self.assertEqual((out/'hermes-response.bin').read_bytes(),raw)
        self.assertEqual(result['results'][0]['diagnostic']['stage'],'usage_qualification')
        self.assertNotIn('draft',result['results'][0])
        error=c.WireResponse(429,b'{"error":"SAFE MOCK rate limit"}',{})
        result,calls,out,_=self.attempt(response=error)
        self.assertEqual(len(calls),1);self.assertEqual((out/'hermes-response.bin').read_bytes(),error.body)
        self.assertNotIn('draft',result['results'][0])

    def test_hermes_transport_uses_existing_envelope_once(self):
        model=self.config['models'][0];payload=c.translate(self.bundle['logical'],model)
        class Reply:
            status=200;headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,bound):return b'{"SAFE":"MOCK"}'
        with patch.object(providers.urllib.request,'build_opener') as build:
            build.return_value.open.return_value=Reply()
            http=providers.ProviderHTTP(model,'SAFE_TEST_KEY_NEVER_REAL_123')
            http(payload)
            with self.assertRaises(c.ComparisonError):http(payload)
            self.assertEqual(build.return_value.open.call_count,1)
            actual=build.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(actual.data),payload)
            self.assertEqual(actual.full_url,providers.ENDPOINT)
            self.assertEqual(build.return_value.open.call_args.kwargs['timeout'],45)

    def test_execute_without_authorization_is_blocked_before_credentials(self):
        with tempfile.TemporaryDirectory() as d,patch.object(cli,'HERMES_OUTPUT',Path(d)/'unused'), \
             patch.object(cli,'verified_inputs',return_value=self.bundle['authoritative']), \
             patch.object(cli,'assemble',return_value=self.bundle),patch.object(cli,'read_provider_keys') as keys:
            with self.assertRaisesRegex(c.ComparisonError,'Separate owner authorization'):
                cli.main(['--profile','hermes','--input','UNUSED','--source-state','UNUSED','--execute'])
            keys.assert_not_called()


if __name__=='__main__':unittest.main()
