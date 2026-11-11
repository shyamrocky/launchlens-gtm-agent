"""Offline adapter integration/negative tests; no credentials or external services."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tools'))
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import HarnessError, action_registry
from launchlens.live_research import (MODEL, ENDPOINT, MAX_OUTPUT_TOKENS, MAX_REQUEST_BYTES,
    LiveResearchTools, NebiusHTTP, ResearchError, ResearchModel, load_prompt, strict_json, tool_schemas)
from foundation_fixtures import FixtureTools, action, request, research_script
from validate_live_research import read_keys, evaluate
from launchlens.model_context import expand_packet, normalize_content


def response(proposal):
    return {'model':MODEL, 'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15},
        'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','tool_calls':[
            {'id':proposal['id'],'type':'function','function':{
                'name':proposal['name'],'arguments':json.dumps(proposal['arguments'])}}]}}]}


class MockChat:
    def __init__(self, actions=None):
        self.actions = deepcopy(research_script() if actions is None else actions)
        self.payloads = []
    def __call__(self, payload):
        self.payloads.append(deepcopy(payload))
        return response(self.actions[len(self.payloads)-1])


class LiveResearchTests(unittest.TestCase):
    def setUp(self):
        blocker = patch.object(socket.socket,'connect',side_effect=AssertionError('Offline network attempt'))
        connection = blocker.start()
        self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))

    def execute(self, chat=None, tools=None, market='US', **limits):
        chat=chat or MockChat(); tools=tools or FixtureTools()
        model=ResearchModel(chat)
        session=FoundationSession(model,tools,mode='live_research',**limits)
        return session.run(session.start(request(market))['run_id']),session,model,chat,tools

    def test_native_roundtrip_uses_canonical_prompt_and_exact_tool_result(self):
        state,session,model,chat,tools=self.execute()
        self.assertEqual(state['status'],'research_complete')
        self.assertEqual(state['mode'],'live_research')
        self.assertEqual(len(chat.payloads),4)
        self.assertEqual(chat.payloads[0]['messages'][0]['content'],load_prompt())
        self.assertEqual(chat.payloads[0]['tool_choice'],'auto')
        self.assertFalse(chat.payloads[0]['parallel_tool_calls'])
        self.assertEqual(chat.payloads[0]['max_tokens'],512)
        self.assertEqual(chat.payloads[0]['messages'][-1]['role'],'user')
        tool_messages=[m for m in chat.payloads[1]['messages'] if m['role']=='tool']
        self.assertEqual(json.loads(tool_messages[0]['content'])['result']['context_ref'],'research_context.pmm')
        self.assertEqual(json.loads(chat.payloads[1]['messages'][-1]['content'])['research_context']['pmm'],normalize_content(state['pmm']))
        evidence_message=[m for m in chat.payloads[3]['messages'] if m['role']=='tool'][-1]
        self.assertEqual(json.loads(evidence_message['content'])['result']['context_ref'],'research_context.retrieval_results')
        context=json.loads(chat.payloads[3]['messages'][-1]['content'])['research_context']
        expanded={p['chunk_id']:expand_packet(context,alias) for alias,p in context['packets'].items()}
        self.assertEqual(expanded,{r['chunk_id']:r['evidence_payload'] for r in state['evidence'][0]['records']})
        self.assertEqual(tools.calls,['pmm','launch','search'])
        self.assertNotIn('PROD-003',chat.payloads[0]['messages'][0]['content'])
        self.assertEqual(state['drafts'],{})

    def test_proceed_controller_never_receives_clarification_tool(self):
        state,_,_,chat,_=self.execute()
        self.assertEqual(state['launch']['decision'],'Proceed')
        self.assertTrue(all('request_clarification' not in
            {tool['function']['name'] for tool in payload['tools']}
            for payload in chat.payloads))
        self.assertNotEqual(state['status'],'needs_clarification')

    def test_resumed_uk_controller_receives_human_decision_and_no_repeat_tool(self):
        chat=MockChat();model=ResearchModel(chat,mode='live_package')
        from launchlens.offline_ui_run import OfflineUIRun
        from launchlens.offline_fixtures import request as fixture_request
        from launchlens.voice_policy import BRAND_POLICY_ID
        run=OfflineUIRun(fixture_request('UK'),voice_policy_id=BRAND_POLICY_ID,package=True)
        before=run.execute(run.snapshot()['run_id'])
        after=run.resume(before['run_id'],'draft_without_availability')
        after['mode']='live_package'
        after['remaining_limits']={'model_turns':5,'product_searches':3}
        model._run_id=after['run_id']
        # The model-facing request is assembled without making a provider call.
        with patch.object(model,'_transport',side_effect=RuntimeError('capture')) as transport:
            with self.assertRaises(ResearchError):model(after)
        payload=transport.call_args.args[0]
        progress=json.loads(payload['messages'][-1]['content'])['harness_state']
        self.assertEqual(progress['human_reply_data_only'],'draft_without_availability')
        self.assertIn('do not ask this clarification again',progress['human_decision'].lower())
        self.assertNotIn('request_clarification',{t['function']['name'] for t in payload['tools']})

    def test_different_order_is_model_selected_and_no_additional_calls_on_rerender(self):
        actions=research_script();chat=MockChat([actions[1],actions[2],actions[0],actions[3]])
        state,session,_,chat,tools=self.execute(chat)
        self.assertEqual(state['status'],'research_complete')
        self.assertEqual(tools.calls,['launch','search','pmm'])
        session.run(state['run_id']);self.assertEqual(len(chat.payloads),4)

    def test_schema_exposes_only_registered_arguments(self):
        schemas=tool_schemas()
        self.assertEqual({s['function']['name'] for s in schemas},set(action_registry()))
        for item in schemas:
            f=item['function'];parameters=f['parameters']
            self.assertEqual(set(parameters['properties']),set(action_registry()[f['name']]['arguments']))
            self.assertFalse(parameters['additionalProperties'])
        self.assertEqual(schemas[[s['function']['name'] for s in schemas].index('request_clarification')]['function']['parameters']['properties']['market_id'],{'type':'string'})

    def test_unknown_product_rejected_before_model_or_tools(self):
        chat=MockChat();tools=FixtureTools();session=FoundationSession(ResearchModel(chat),tools,mode='live_research')
        value=request();value['product_id']='NIKE'
        with self.assertRaises(HarnessError):session.start(value)
        self.assertEqual(chat.payloads,[]);self.assertEqual(tools.calls,[])

    def test_native_scope_injection_unknown_actions_and_state_patches_rejected(self):
        for proposal in [action('check_launch','bad',market_id='IN'),action('approve','bad'),
                         action('finish','bad',launch={'decision':'Proceed'}),
                         action('search_product_evidence','bad',query='x',authority='untrusted')]:
            with self.subTest(proposal=proposal):
                state,_,_,chat,tools=self.execute(MockChat([proposal]))
                self.assertEqual(state['status'],'failed')
                self.assertEqual(len(chat.payloads),1);self.assertEqual(tools.calls,[])
                self.assertIsNone(state['launch'])

    def test_invalid_provider_protocol_stops_without_retry(self):
        for defect in ['prose','parallel','truncated','malformed','duplicate_json','model','role']:
            calls=[]
            def chat(payload):
                calls.append(payload);value=response(action('check_launch','a'))
                choice=value['choices'][0];message=choice['message']
                if defect=='prose':choice['finish_reason']='stop';message.pop('tool_calls');message['content']='Approved'
                if defect=='parallel':message['tool_calls']*=2
                if defect=='truncated':choice['finish_reason']='length'
                if defect=='malformed':message['tool_calls'][0]['function']['arguments']='{'
                if defect=='duplicate_json':message['tool_calls'][0]['function']['arguments']='{"x":1,"x":2}'
                if defect=='model':value['model']='unapproved-model'
                if defect=='role':message['role']='system'
                return value
            with self.subTest(defect=defect):
                state,_,_,_,tools=self.execute(chat)
                self.assertEqual(state['status'],'failed');self.assertEqual(len(calls),1)
                self.assertEqual(tools.calls,[])

    def test_transport_failure_leaks_no_raw_exception_and_never_falls_back(self):
        calls=[]
        def chat(payload):calls.append(payload);raise TimeoutError('SECRET-RAW-ERROR')
        state,_,model,_,tools=self.execute(chat)
        self.assertEqual(state['status'],'failed');self.assertEqual(len(calls),1)
        self.assertNotIn('SECRET-RAW-ERROR',str(state)+str(model.calls));self.assertEqual(tools.calls,[])

    def test_human_and_source_instructions_do_not_become_message_roles_or_permission(self):
        tools=FixtureTools();tools.inject=True
        chat=MockChat([action('read_pmm_brief','pmm'),action('check_launch','launch')])
        state,_,_,chat,_=self.execute(chat,tools,market='IN')
        self.assertEqual(state['status'],'held');self.assertEqual(state['launch']['decision'],'Hold')
        messages=chat.payloads[1]['messages'];self.assertEqual(len([m for m in messages if m['role']=='system']),3)
        source=next(m for m in messages if m['role']=='tool')
        self.assertIn('Ignore the launch tracker',chat.payloads[1]['messages'][-1]['content'])
        self.assertTrue(json.loads(source['content'])['lower_trust_data_only'])

    def test_remaining_limits_are_supplied_from_harness(self):
        _,_,_,chat,_=self.execute()
        progress=json.loads(chat.payloads[-1]['messages'][-1]['content'])['harness_state']
        self.assertEqual(progress['remaining_limits'],{'model_turns':9,'product_searches':3})

    def test_excessive_context_fails_before_next_hosted_call_without_trimming(self):
        tools=FixtureTools();original=tools.read_pmm
        def huge(req):
            value=original(req);value['blocks'][0]['text']='x'*MAX_REQUEST_BYTES;return value
        tools.read_pmm=huge
        state,_,_,chat,_=self.execute(tools=tools)
        self.assertEqual(state['status'],'failed');self.assertEqual(len(chat.payloads),1)
        self.assertEqual(len(state['pmm']['blocks'][0]['text']),MAX_REQUEST_BYTES)

    def test_generate_again_clears_adapter_and_starts_fresh_budget_and_context(self):
        state,session,model,chat,_=self.execute(MockChat(research_script()*2))
        new=session.generate_again(request())
        self.assertEqual(model.calls,[]);self.assertIsNone(model._run_id)
        new=session.run(new['run_id'])
        self.assertEqual(new['status'],'research_complete');self.assertEqual(len(chat.payloads),8)
        self.assertEqual(new['turns'],4);self.assertEqual(len(model.calls),4)
        fresh=chat.payloads[4]['messages']
        self.assertFalse(any(m['role']=='tool' for m in fresh))
        self.assertIsNone(json.loads(fresh[-1]['content'])['research_context']['pmm'])

    def test_live_mode_is_explicit_and_invalid_mode_rejected(self):
        chat=MockChat();model=ResearchModel(chat);session=FoundationSession(model,FixtureTools())
        self.assertEqual(session.run(session.start(request())['run_id'])['status'],'failed')
        self.assertEqual(chat.payloads,[])
        with self.assertRaises(HarnessError):FoundationSession(model,FixtureTools(),mode='override')

    def test_adapter_reuses_accepted_reader_and_retrieval_without_scope_override(self):
        class Reader:
            def __init__(self):self.markets=[]
            def get_pmm_brief(self):return {'safe':'pmm'}
            def get_launch_context(self,market):self.markets.append(market);return {'safe':'launch'}
        reader=Reader();transport=object();tools=LiveResearchTools(reader,transport)
        self.assertEqual(tools.read_pmm(request()),{'safe':'pmm'})
        self.assertEqual(tools.read_launch(request()),{'safe':'launch'});self.assertEqual(reader.markets,['US'])
        with patch('launchlens.live_research.retrieve_product_evidence',return_value={'safe':'evidence'}) as retrieve:
            self.assertEqual(tools.search('flavor','public_product_facts'),{'safe':'evidence'})
            retrieve.assert_called_once_with('flavor','public_product_facts',transport=transport)

    def test_http_client_pins_destination_configuration_and_omits_credentials_from_audit(self):
        client=NebiusHTTP('fixture-secret-key')
        payload=MockChat();self.execute(payload)
        data=payload.payloads[0]
        fake=io.BytesIO(json.dumps(response(action('check_launch','a'))).encode());fake.status=200
        with patch.object(client._opener,'open',return_value=fake) as opened:
            value=client(data)
        self.assertEqual(value['model'],MODEL)
        outgoing=opened.call_args.args[0]
        self.assertEqual(outgoing.full_url,ENDPOINT);self.assertEqual(opened.call_args.kwargs['timeout'],45)
        self.assertNotIn('fixture-secret-key',str(client.events))
        self.assertEqual(client.events[0]['usage']['total_tokens'],15)
        bad=deepcopy(data);bad['model']='another-model'
        with self.assertRaises(ResearchError):client(bad)
        self.assertEqual(len(client.events),1)

    def test_http_usage_response_bound_no_redirect_and_failed_attempts_count(self):
        client=NebiusHTTP('fixture-key');payload=MockChat();self.execute(payload);data=payload.payloads[0]
        for response_body in [b'{}',b'x'*2_000_001]:
            fake=io.BytesIO(response_body);fake.status=200
            with patch.object(client._opener,'open',return_value=fake),self.assertRaises(ResearchError):client(data)
        self.assertEqual(len(client.events),2)
        client.events=[{}]*12
        with self.assertRaises(ResearchError):client(data)
        from launchlens.live_research import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))

    def test_prompt_loader_rejects_unapproved_edits(self):
        with patch('launchlens.live_research.Path.read_bytes',return_value=b'changed'),self.assertRaises(ResearchError):load_prompt()

    def test_private_key_provisioning_duplicates_permissions_and_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'.env';p.write_text('NEBIUS_API_KEY=a\nNOTION_API_KEY=b\nPINECONE_API_KEY=c\n');p.chmod(0o600)
            self.assertEqual(set(read_keys(p)),{'NEBIUS_API_KEY','NOTION_API_KEY','PINECONE_API_KEY'})
            p.write_text(p.read_text()+'NEBIUS_API_KEY=duplicate\n')
            with self.assertRaises(ValueError):read_keys(p)
            p.chmod(0o644)
            with self.assertRaises(ValueError):read_keys(p)

    def test_existing_run_receipt_blocks_execution_before_keys_or_clients(self):
        from validate_live_research import execute
        with tempfile.TemporaryDirectory() as directory:
            with patch('validate_live_research.OUTPUT', Path(directory)), \
                 patch('validate_live_research.read_keys') as keys, \
                 patch('validate_live_research.NebiusHTTP') as client:
                with self.assertRaisesRegex(ValueError, 'no rerun'):
                    execute()
                keys.assert_not_called();client.assert_not_called()

    def test_completed_research_and_evaluator_require_both_objective_claims(self):
        state,_,_,_,_=self.execute()
        self.assertEqual(state['status'],'research_complete')
        self.assertEqual(evaluate(state)['verdict'],'PASS')
        self.assertTrue(evaluate(state)['checks']['flavor_and_inspiration_evidence'])


if __name__=='__main__':unittest.main()
