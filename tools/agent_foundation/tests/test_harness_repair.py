"""Focused H-01/H-02/H-03 regression tests: no keys, generated inputs or network."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
for folder in ['src','tools','tests']:sys.path.insert(0,str(ROOT/folder))
from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import HarnessError
from launchlens.live_research import ResearchModel,LiveResearchTools,NebiusHTTP
from launchlens.model_context import (ContextError,build_context,expand_packet,canonical,
    normalize_content,native_history,structured_packet_text)
from launchlens.notion_tools import NotionHTTP,NotionReader
from launchlens.retrieval import PineconeHTTP
from launchlens.evidence_payload import storage_fields
from foundation_fixtures import FixtureTools,ScriptedModel,action,request,research_script
from test_live_research import MockChat
from test_launch_checks import FakeNotion
from test_retrieval import Fake,packet,record


def base_state(result=None):
    return {'pmm':None,'launch':None,'ledger':{},'evidence':[] if result is None else [result]}


def structured_fixture():
    value=FixtureTools().search('safe fixture','public_product_facts')
    for row in value['records']:
        p=row['evidence_payload']
        p['segments']=[{'role':'primary','text':p['primary_text'],'page_number':2},
            {'role':'required_context','text':'SAFE FIXTURE: retain market and serving qualifications','page_number':3},
            {'role':'source_reference','text':'SAFE FIXTURE source URL https://example.com/fixture','page_number':3}]
        p['claim_source_mappings']=[{'claim_id':p['unit_id'],'source_id':'TEST-SOURCE',
            'verification_status':'SAFE_FIXTURE','market_scope':'SAFE US original serving',
            'temporal_scope':'SAFE retrospective scope','source_locator':'SAFE label',
            'notes_or_limitations':'SAFE publisher label, not independent testing',
            'source_url':'https://example.com/fixture','other_field':'SAFE retained extra'}]
        p['source_references'][0]['roles']=['claim_support']
        p['links']=[{'uri':'https://example.com/extra-reference'}]
        p['text']=structured_packet_text(p)
        row['evidence_sha256']=storage_fields(p)['evidence_sha256']
    return value


class HarnessRepairTests(unittest.TestCase):
    def setUp(self):
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Unexpected offline network'))
        connection=blocker.start();self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))

    def test_projection_exactly_roundtrips_packets_roles_qualifiers_and_extra_fields(self):
        result=structured_fixture();state=base_state(result);before=canonical(state)
        view=build_context(state)
        restored={p['chunk_id']:expand_packet(view,alias) for alias,p in view['packets'].items()}
        self.assertEqual(restored,{r['chunk_id']:r['evidence_payload'] for r in result['records']})
        self.assertEqual(canonical(state),before)
        for p in restored.values():
            self.assertEqual({s['role'] for s in p['segments']},{'primary','required_context','source_reference'})
            self.assertIn('not independent testing',p['claim_source_mappings'][0]['notes_or_limitations'])

    def test_shared_context_is_deduplicated_with_passage_bindings(self):
        view=build_context(base_state(structured_fixture()));passages=list(view['packets'].values())
        self.assertEqual(passages[0]['document_ref'],passages[1]['document_ref'])
        self.assertEqual(passages[0]['segment_refs'][1:],passages[1]['segment_refs'][1:])
        self.assertNotIn('text',passages[0])
        self.assertEqual(passages[0]['text_representation'],'segments_and_mappings')
        self.assertEqual(len([v for v in view['shared'].values() if v['kind']=='document']),1)

    def test_repeated_packets_pool_once_without_losing_per_search_partial_flags(self):
        result=structured_fixture();state=base_state(result)
        again=deepcopy(result);again['records'][0]['usable_as_complete_evidence']=False
        again['records'][0]['reference_status']='incomplete';again['status']='incomplete'
        again['issues']=[{'code':'reference_limit','message':'SAFE missing reference'}]
        state['evidence'].append(again);view=build_context(state)
        self.assertEqual(len(view['packets']),2)
        self.assertTrue(view['retrieval_results'][0]['records'][0]['usable_as_complete_evidence'])
        self.assertFalse(view['retrieval_results'][1]['records'][0]['usable_as_complete_evidence'])
        self.assertEqual(view['retrieval_results'][1]['issues'],again['issues'])

    def test_conflicting_same_packet_id_is_rejected_instead_of_overwritten(self):
        state=base_state(structured_fixture());other=deepcopy(state['evidence'][0])
        other['records'][0]['evidence_payload']['primary_text']='SAFE conflicting content'
        state['evidence'].append(other)
        with self.assertRaises(ContextError):build_context(state)

    def test_nonredundant_unrecognized_full_text_is_preserved(self):
        result=structured_fixture();result['records'][0]['evidence_payload']['text']+='\nSAFE extra qualification only in text'
        view=build_context(base_state(result));alias=next(iter(view['packets']))
        self.assertIn('additional_text_ref',view['packets'][alias])
        self.assertEqual(expand_packet(view,alias),result['records'][0]['evidence_payload'])

    def test_projection_preserves_synthetic_authority_and_is_deterministic(self):
        value=FixtureTools().search('safe requirement','synthetic_product_intent')
        state=base_state(value);one=build_context(state);two=build_context(state)
        self.assertEqual(canonical(one),canonical(two))
        alias=next(iter(one['packets']));p=expand_packet(one,alias)
        self.assertEqual(p['authority'],'synthetic_product_intent')
        self.assertEqual(p['source_acceptance']['status'],'OWNER_ACCEPTED')

    def test_pmm_normalization_preserves_order_cells_text_links_and_identifiers(self):
        rich={'type':'text','text':{'content':'SAFE brief','link':{'url':'https://example.com/a'}},
              'plain_text':'SAFE brief','href':'https://example.com/a','annotations':{'bold':True}}
        node={'block_id':'SAFE-ID','type':'table','content':{'table_width':2},'children':[
            {'block_id':'SAFE-ROW','type':'table_row','content':{'cells':[[rich],[dict(rich,plain_text='SAFE other')]]},'children':[]}]}
        result=normalize_content(node)
        self.assertEqual(result['block_id'],'SAFE-ID')
        cells=result['children'][0]['content']['cells']
        self.assertEqual(cells[0][0],{'text':'SAFE brief','urls':['https://example.com/a'],'annotations':{'bold':True}})
        self.assertEqual(cells[1][0]['text'],'SAFE other');self.assertEqual(cells[1][0]['source_text'],'SAFE brief')
        self.assertEqual(node['children'][0]['content']['cells'][0][0],rich)

    def test_meaningful_text_annotations_are_retained(self):
        value={'type':'text','text':{'content':'SAFE superseded wording'},
               'plain_text':'SAFE superseded wording','annotations':{
                   'strikethrough':True,'bold':False,'color':'default','code':True,'custom_flag':False}}
        normalized=normalize_content(value)
        self.assertEqual(normalized['annotations'],{'strikethrough':True,'code':True,'custom_flag':False})

    def test_launch_result_and_restrictions_are_preserved_once_in_context(self):
        state=base_state();state['launch']={'decision':'Clarify','promotional_draft_allowed':False,
             'conditions':[{'message':'SAFE missing availability'}],'publishing_allowed':False}
        result=build_context(state)
        self.assertEqual(result['launch'],state['launch'])
        result['launch']['decision']='HACK';self.assertEqual(state['launch']['decision'],'Clarify')

    @staticmethod
    def restricted_tools():
        tools=FixtureTools();original=tools.search
        def search(query,authority):
            value=original(query,authority)
            if query=='unrelated':
                row=deepcopy(value['records'][0]);p=row['evidence_payload']
                p.update(unit_id='PROD-008',chunk_id=p['chunk_id'].replace(':PROD-002:',':PROD-008:'),
                         claim_ids=['PROD-008'],primary_text='SAFE unrelated nutrition fixture')
                row.update(unit_id=p['unit_id'],chunk_id=p['chunk_id'],evidence_sha256=storage_fields(p)['evidence_sha256'])
                value['records']=[row]
            return value
        tools.search=search;return tools

    def test_unrelated_claim_cannot_finish_and_can_recover_with_bounded_research(self):
        actions=research_script();actions[2]['arguments']['query']='unrelated'
        actions[3]['id']='premature'
        actions += [action('search_product_evidence','recovery',query='flavor recovery',authority='public_product_facts'),action('finish','complete')]
        model=ResearchModel(MockChat(actions));tools=self.restricted_tools()
        session=FoundationSession(model,tools,mode='live_research');state=session.run(session.start(request())['run_id'])
        self.assertEqual(state['status'],'research_complete');self.assertEqual(state['turns'],6)
        attempted=state['ledger']['premature']['result']
        self.assertEqual(attempted['status'],'research_incomplete')
        self.assertEqual(len(attempted['missing_requirements']),2)
        self.assertEqual(state['research_gaps'],[]);self.assertEqual(state['searches'],2)

    def test_repeated_incomplete_finishes_exhaust_budget_without_becoming_permission(self):
        actions=research_script()[:3];actions[2]['arguments']['query']='unrelated'
        actions += [action('finish',f'f{i}') for i in range(9)]
        session=FoundationSession(ResearchModel(MockChat(actions)),self.restricted_tools(),mode='live_research')
        state=session.run(session.start(request())['run_id'])
        self.assertEqual(state['status'],'failed');self.assertEqual(state['turns'],12)
        self.assertEqual(state['drafts'],{});self.assertEqual(len(state['research_gaps']),2)

    def test_partial_or_synthetic_evidence_cannot_satisfy_objective_coverage(self):
        for kind in ['partial','synthetic']:
            tools=FixtureTools();actions=research_script()
            if kind=='partial':tools.partial=True
            else:actions[2]['arguments']['authority']='synthetic_product_intent'
            session=FoundationSession(ResearchModel(MockChat(actions)),tools,mode='live_research')
            state=session.run(session.start(request())['run_id'])
            self.assertNotEqual(state['status'],'research_complete')
            self.assertEqual(state['ledger']['finish']['result']['status'],'research_incomplete')

    def test_outer_unit_identity_spoof_cannot_satisfy_coverage(self):
        tools=self.restricted_tools();original=tools.search
        def spoof(**args):
            value=original(**args);value['records'][0]['unit_id']='PROD-003';return value
        tools.search=spoof;actions=research_script();actions[2]['arguments']['query']='unrelated'
        session=FoundationSession(ResearchModel(MockChat(actions)),tools,mode='live_research')
        self.assertEqual(session.run(session.start(request())['run_id'])['status'],'failed')

    def test_reset_clears_adapter_state_and_replacement_contains_no_old_evidence(self):
        chat=MockChat(research_script()+[action('check_launch','new-launch')]);model=ResearchModel(chat)
        session=FoundationSession(model,FixtureTools(),mode='live_research')
        first=session.run(session.start(request())['run_id']);session.reset()
        self.assertIsNone(session.snapshot());self.assertIsNone(model._run_id);self.assertEqual(model.calls,[])
        self.assertFalse(hasattr(model,'_history'));self.assertFalse(hasattr(model,'_pending'))
        with self.assertRaises(HarnessError):session.run(first['run_id'])
        second=session.run(session.start(request('IN'))['run_id'])
        self.assertEqual(second['status'],'held')
        fresh=json.loads(chat.payloads[-1]['messages'][-1]['content'])['research_context']
        self.assertEqual(fresh['packets'],{});self.assertIsNone(fresh['pmm'])
        self.assertFalse(any(m['role']=='tool' for m in chat.payloads[-1]['messages']))

    def test_reset_refreshes_model_and_source_attempt_budgets_without_network(self):
        chat=NebiusHTTP('SAFE-fixture-key');chat.events.extend([{}]*12)
        notion=NotionHTTP('SAFE-fixture-key');notion.events.extend([{}]*60)
        pine=PineconeHTTP('SAFE-fixture-key');pine.events.append({'SAFE':'event'})
        model=ResearchModel(chat);model.calls.append({'SAFE':'old-action'})
        session=FoundationSession(model,LiveResearchTools(NotionReader(notion),pine),mode='live_research')
        session.start(request());session.reset()
        self.assertEqual(chat.events,[]);self.assertEqual(notion.events,[]);self.assertEqual(pine.events,[])
        self.assertEqual(model.calls,[])

    def test_invalid_replacement_keeps_model_context_and_current_run(self):
        chat=MockChat();model=ResearchModel(chat);session=FoundationSession(model,FixtureTools(),mode='live_research')
        state=session.run(session.start(request())['run_id']);old=deepcopy(model.calls)
        bad=request();bad['product_id']='NIKE'
        with self.assertRaises(HarnessError):session.generate_again(bad)
        self.assertEqual(session.snapshot(),state);self.assertEqual(model.calls,old)

    def test_cleanup_failure_discards_task_without_exposing_raw_error(self):
        tools=FixtureTools()
        def broken():raise TimeoutError('SECRET error body')
        tools.reset_run=broken
        session=FoundationSession(ScriptedModel(research_script()),tools)
        old=session.start(request())
        with self.assertRaises(HarnessError) as caught:session.reset()
        self.assertNotIn('SECRET',str(caught.exception));self.assertIsNone(session.snapshot())
        with self.assertRaises(HarnessError):session.run(old['run_id'])

    def test_native_history_rejects_tampered_action_and_never_returns_full_packets(self):
        session=FoundationSession(ScriptedModel(research_script()),FixtureTools())
        state=session.run(session.start(request())['run_id']);history=native_history(state)
        messages=[json.loads(m['content']) for m in history if m['role']=='tool']
        self.assertTrue(all('evidence_payload' not in str(m) for m in messages))
        state['ledger']['facts']['action']['arguments']['query']='tampered'
        with self.assertRaises(ContextError):native_history(state)

    def test_real_adapter_composition_for_three_offline_scenarios(self):
        for market,outcome,actions in [('US','research_complete',research_script()),
             ('UK','needs_clarification',[action('check_launch','launch'),action('finish','finish')]),
             ('IN','held',[action('check_launch','launch')])]:
            pine=Fake([record(packet('PROD-002')),record(packet('PROD-003'))])
            session=FoundationSession(ResearchModel(MockChat(actions)),
                LiveResearchTools(NotionReader(FakeNotion()),pine),mode='live_research')
            state=session.run(session.start(request(market))['run_id'])
            self.assertEqual(state['status'],outcome);self.assertFalse(state['launch']['publishing_allowed'])


if __name__=='__main__':unittest.main()
