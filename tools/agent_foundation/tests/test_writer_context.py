"""Offline context selection and independent authority tests; no private inputs/keys."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
for part in ['src','tools']:sys.path.insert(0,str(ROOT/part))
from launchlens.linkedin_drafting import LinkedInWriter,admit_output,digest,evidence_records,writer_request
from launchlens.live_research import PROMPTS,ResearchError,dumps
from launchlens.model_context import build_context,structured_packet_text,CSV_TEXT_FIELDS
from launchlens.evidence_payload import storage_fields
from launchlens.writer_context import ProjectionError,identity,project_writer_input
from prepare_writer_context import baseline_identity
import test_linkedin_drafting as helpers
Chat=helpers.Chat
draft=helpers.draft


def fixture(qualifier='SAFE FIXTURE: audience unvalidated; availability unknown; no ingredient claim.'):
    _,_,_,previous,_=helpers.LinkedInTests().execute()
    inputs=deepcopy(previous.calls[0]['input']);context=inputs['research_context']
    pmm=deepcopy(context['pmm'])
    pmm['blocks']=[{'block_id':'safe1','type':'paragraph','content':{'rich_text':[{'text':qualifier}]},'children':[]},
                   {'block_id':'safe2','type':'paragraph','content':{'rich_text':[{'text':'SAFE unrelated campaign'}]},'children':[]}]
    launch=deepcopy(context['launch'])
    launch['calendar_evidence']['values']['Notes']='SAFE FIXTURE: schedule is not permission.'
    rows=evidence_records(inputs)
    for row in rows:
        p=row['evidence_payload']
        p['claim_source_mappings']=[{k:'SAFE FIXTURE' for k in CSV_TEXT_FIELDS}]
        p['claim_source_mappings'][0]['claim_id']=p['unit_id']
        p['text']=structured_packet_text(p)
        row['evidence_sha256']=storage_fields(p)['evidence_sha256']
    inputs['research_context']=build_context({'pmm':pmm,'launch':launch,'evidence':[{'records':rows}]})
    policy={'version':'safe-fixture','pmm_sha256':identity(pmm),'launch_sha256':identity(launch),
        'pmm_selection':[{'source':'research_context.pmm.blocks.0.content.rich_text','purpose':'Preserve caveats',
                          'spans':[[0,len(qualifier),'Preserve entire caveat/conflict field']]}],
        'evidence_sha256':{r['unit_id']:r['evidence_sha256'] for r in rows},'segment_selection':{},
        'launch_fields':['authority','decision','product_id','market_id','evaluation_date',
                         'promotional_draft_allowed','publishing_allowed','conditions','notice'],
        'readiness_fields':['Requirement','Status','Blocker / Missing Information','Last Updated'],
        'material_boundaries':['SAFE FIXTURE conflict: PMM is guidance, not permission.']}
    return inputs,policy


class WriterContextTests(unittest.TestCase):
    def setUp(self):
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline network attempt'))
        conn=blocker.start();self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(conn.call_count,0))

    def test_deterministic_projection_keeps_material_text_and_authority_unmodified(self):
        inputs,policy=fixture();before=deepcopy(inputs)
        a=project_writer_input(inputs,policy=policy);b=project_writer_input(inputs,policy=policy)
        self.assertEqual(a,b);self.assertEqual(inputs,before)
        view=a['model_input'];self.assertEqual(set(view),set(inputs))
        for key in inputs:
            if key!='research_context':self.assertEqual(view[key],inputs[key])
        self.assertEqual(view['research_context']['pmm']['guidance'][0]['text'],[
            'SAFE FIXTURE: audience unvalidated; availability unknown; no ingredient claim.'])
        self.assertTrue(any(r['decision']=='exclude' for r in a['manifest']['included_excluded']))
        texts={v['text'] for v in view['research_context']['claim_context'].values()}
        for source in evidence_records(inputs):
            for segment in source['evidence_payload']['segments']:self.assertIn(segment['text'],texts)
        for source,target in zip(evidence_records(inputs),view['research_context']['claims']):
            self.assertEqual(target['source_references'],source['evidence_payload']['source_references'])
            self.assertEqual(target['claim_source_mappings'],source['evidence_payload']['claim_source_mappings'])

    def test_new_caveat_or_conflict_fails_closed_instead_of_being_silently_excluded(self):
        inputs,policy=fixture();inputs['research_context']['pmm']['blocks'][1]['content']['rich_text'][0]['text']='NEW material restriction'
        with self.assertRaisesRegex(ProjectionError,'changed'):project_writer_input(inputs,policy=policy)

    def test_ineligible_id_inside_retained_material_caveat_stops_without_stripping(self):
        inputs,policy=fixture('SAFE mandatory restriction involving PROD-001; must not be lost.')
        before=deepcopy(inputs)
        with self.assertRaisesRegex(ProjectionError,'Ineligible'):project_writer_input(inputs,policy=policy)
        self.assertEqual(inputs,before)

    def test_hold_clarify_missing_and_wrong_scope_cannot_be_projected(self):
        for change in ['Hold','Clarify','missing','scope']:
            inputs,policy=fixture();launch=inputs['research_context']['launch']
            if change in ['Hold','Clarify']:launch['decision']=change
            elif change=='missing':launch['promotional_draft_allowed']=False
            else:launch['market_id']='UK'
            with self.subTest(change=change):
                with self.assertRaises(ProjectionError):project_writer_input(inputs,policy=policy)

    def test_corrupt_or_missing_evidence_stops(self):
        for corrupt in [True,False]:
            inputs,policy=fixture();rows=inputs['research_context']['retrieval_results'][0]['records']
            if corrupt:rows[0]['evidence_sha256']='0'*64
            else:rows.pop()
            with self.subTest(corrupt=corrupt):
                with self.assertRaises(ProjectionError):project_writer_input(inputs,policy=policy)

    def test_projected_writer_sends_selected_context_but_admits_against_original(self):
        inputs,policy=fixture();before=deepcopy(inputs);chat=Chat()
        writer=LinkedInWriter(chat,context_projector=lambda value:project_writer_input(value,policy=policy))
        result=writer(inputs);record=admit_output(result,inputs)
        self.assertEqual(json.loads(chat.payloads[0]['messages'][1]['content']),writer.calls[0]['model_input'])
        self.assertNotEqual(writer.calls[0]['model_input']['research_context'],inputs['research_context'])
        self.assertEqual(writer.calls[0]['input'],before);self.assertEqual(inputs,before)
        self.assertEqual(record['input_sha256'],digest(before))
        self.assertEqual(record['review_status'],'unreviewed');self.assertFalse(record['publishing_allowed'])
        self.assertEqual(chat.writes,1);self.assertEqual(chat.decisions,0)
        baseline=writer_request(inputs)
        for key in baseline:
            if key!='messages':self.assertEqual(chat.payloads[0][key],baseline[key])
        self.assertEqual(chat.payloads[0]['messages'][0],baseline['messages'][0])
        for key in inputs:
            if key!='research_context':self.assertEqual(writer.calls[0]['model_input'][key],inputs[key])
        self.assertEqual(hashlib.sha256(dumps(chat.payloads[0]).encode()).hexdigest(),writer.calls[0]['request_sha256'])

    def test_projection_cannot_change_noncontext_constraints_before_model_call(self):
        inputs,policy=fixture();chat=Chat()
        def bad(value):
            view=project_writer_input(value,policy=policy)
            view['model_input']['draft_constraints']['allowed_claim_ids']=['PROD-001']
            view['manifest']['model_input_sha256']=digest(view['model_input'])
            return view
        writer=LinkedInWriter(chat,context_projector=bad)
        with self.assertRaisesRegex(ResearchError,'non-context'):writer(inputs)
        self.assertEqual(chat.payloads,[])

    def test_backend_does_not_trust_fabricated_evidence_in_model_projection(self):
        inputs,policy=fixture();candidate=draft()
        candidate['claim_references'][0]['claim_ids']=['PROD-001']
        def poisoned(value):
            view=project_writer_input(value,policy=policy)
            view['model_input']['research_context']['claims'].append({'claim_id':'PROD-001','text':'Fabricated'})
            view['manifest']['model_input_sha256']=digest(view['model_input'])
            return view
        chat=Chat(value=candidate);writer=LinkedInWriter(chat,context_projector=poisoned)
        result=writer(inputs)
        from launchlens.linkedin_drafting import DraftValidationError
        with self.assertRaises(DraftValidationError) as error:admit_output(result,inputs)
        self.assertEqual(error.exception.diagnostic['rule'],'invalid_claim_reference')
        self.assertEqual(writer.calls[0]['input_sha256'],digest(inputs))

    def test_default_writer_request_is_unchanged_and_projects_only_when_explicit(self):
        inputs,_=fixture();chat=Chat();writer=LinkedInWriter(chat);writer(inputs)
        self.assertEqual(chat.payloads[0],writer_request(inputs))
        self.assertNotIn('model_input',writer.calls[0])

    def test_full_request_and_assembled_input_hashes_are_distinct_scopes(self):
        inputs,_=fixture();raw=dumps(writer_request(inputs)).encode();sha=hashlib.sha256(raw).hexdigest()
        receipt={'input_sha256':digest(inputs),'prompt_hashes':PROMPTS,
                 'model_http_events':[{'kind':'writing','request_sha256':sha,'request_bytes':len(raw)}]}
        reconstructed,info=baseline_identity(receipt,inputs)
        self.assertEqual(reconstructed,raw);self.assertTrue(info['reconstruction_matches_recorded_full_request'])
        self.assertFalse(info['original_wire_bytes_retained']);self.assertNotEqual(digest(inputs),sha)
        receipt['model_http_events'][0].pop('request_sha256')
        _,info=baseline_identity(receipt,inputs)
        self.assertIsNone(info['reconstruction_matches_recorded_full_request'])
        self.assertFalse(info['recorded_full_request_hash_available'])

    def test_baseline_mismatch_is_reported_not_relabelled_verified(self):
        inputs,_=fixture();receipt={'input_sha256':digest(inputs),'prompt_hashes':PROMPTS,
            'model_http_events':[{'kind':'writing','request_sha256':'0'*64,'request_bytes':1}]}
        with self.assertRaisesRegex(ProjectionError,'differs'):baseline_identity(receipt,inputs)


if __name__=='__main__':unittest.main()
