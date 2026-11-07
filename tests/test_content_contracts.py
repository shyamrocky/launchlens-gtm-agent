"""M2.3a: independent safe fixtures; no GTM generation, credentials or network."""
from copy import deepcopy
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from launchlens.content_contracts import (ContractError, TEMPLATES, COMMON_REVIEW_CRITERIA,
    load_template, model_output_schema, validate_draft)
from launchlens.evidence_payload import storage_fields
from test_retrieval import packet


def evidence(authority='public_product_facts', unit='PROD-002'):
    p = packet(unit, authority)
    return {'chunk_id':p['chunk_id'], 'unit_id':p['unit_id'], 'authority':authority,
        'evidence_sha256':storage_fields(p)['evidence_sha256'], 'evidence_payload':p,
        'usable_as_complete_evidence':True, 'reference_status':'resolved'}


def value(schema):
    if schema['type']=='string':return 'SAFE FIXTURE: independently authored structural example.'
    if schema['type']=='array':return [value(schema['items']) for _ in range(schema.get('minItems',0))]
    return {k:value(v) for k,v in schema['properties'].items() if k in schema['required']}


def draft(fmt='linkedin'):
    return {'format':fmt, 'content':value(load_template(fmt)['content_schema']), 'claim_references':[]}


class ContentContractTests(unittest.TestCase):
    def setUp(self):
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline network attempt'))
        connection=blocker.start();self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))

    def test_all_five_contracts_load_and_validate_with_one_shared_envelope(self):
        self.assertEqual(len(TEMPLATES),5)
        for fmt in TEMPLATES:
            with self.subTest(format=fmt):
                template=load_template(fmt);schema=model_output_schema(fmt)
                self.assertEqual(set(schema['properties']),{'format','content','claim_references'})
                self.assertEqual(template['shared_contract'],'launchlens.content_contracts/v1')
                self.assertEqual(template['editorial_guidelines']['enforcement'],'advisory_only')
                self.assertTrue(template['review_criteria']);self.assertTrue(COMMON_REVIEW_CRITERIA)
                result=validate_draft(draft(fmt),format_name=fmt,evidence_records=[])
                self.assertEqual(result['structural_validation'],'passed');self.assertTrue(result['semantic_review_required'])

    def test_required_channel_fields_cannot_be_missing_empty_or_wrong_type(self):
        for fmt,fields in [('linkedin',['hook','body','cta']),('email',['subject','preview_text','headline','body','cta'])]:
            for field in fields:
                for mode in ['missing','empty','wrong_type']:
                    with self.subTest(format=fmt,field=field,mode=mode):
                        d=draft(fmt)
                        if mode=='missing':del d['content'][field]
                        else:d['content'][field]='   ' if mode=='empty' else 42
                        with self.assertRaises(ContractError):validate_draft(d,format_name=fmt,evidence_records=[])

    def test_ads_require_exactly_three_complete_concepts(self):
        for count in [0,2,4]:
            d=draft('ads');one=d['content']['concepts'][0];d['content']['concepts']=[deepcopy(one) for _ in range(count)]
            with self.assertRaises(ContractError):validate_draft(d,format_name='ads',evidence_records=[])
        d=draft('ads');del d['content']['concepts'][1]['cta']
        with self.assertRaises(ContractError):validate_draft(d,format_name='ads',evidence_records=[])

    def test_nested_blog_sections_and_three_messaging_pillars_are_structural(self):
        d=draft('blog');del d['content']['sections'][0]['heading']
        with self.assertRaises(ContractError):validate_draft(d,format_name='blog',evidence_records=[])
        d=draft('campaign_brief');d['content']['messaging_pillars'].pop()
        with self.assertRaises(ContractError):validate_draft(d,format_name='campaign_brief',evidence_records=[])

    def test_length_and_hashtag_preferences_are_warnings_not_rejection(self):
        d=draft();d['content']['body']=' '.join(['SAFE']*250);d['content']['hashtags']=[]
        result=validate_draft(d,format_name='linkedin',evidence_records=[])
        self.assertEqual(result['structural_validation'],'passed')
        self.assertEqual({w['metric'] for w in result['editorial_warnings']},{'words','items'})
        d=draft('email');d['content']['subject']='S'*100
        self.assertTrue(any(w['metric']=='characters' for w in validate_draft(d,format_name='email',evidence_records=[])['editorial_warnings']))

    def test_model_cannot_supply_approval_version_review_or_unknown_fields(self):
        for field in ['review_status','human_approved','review_findings','draft_version','launch_permission']:
            for place in ['outer','content']:
                d=draft();(d if place=='outer' else d['content'])[field]='approved'
                with self.assertRaises(ContractError):validate_draft(d,format_name='linkedin',evidence_records=[])
        d=draft();d['format']='email'
        with self.assertRaises(ContractError):validate_draft(d,format_name='linkedin',evidence_records=[])

    def test_public_claim_reference_must_resolve_to_a_real_text_field(self):
        d=draft();d['claim_references']=[{'content_field':'body','claim_ids':['PROD-002']}]
        self.assertEqual(validate_draft(d,format_name='linkedin',evidence_records=[evidence()])['structural_validation'],'passed')
        for path in ['missing','hashtags','../body','body.0','review_status']:
            changed=deepcopy(d);changed['claim_references'][0]['content_field']=path
            with self.assertRaises(ContractError):validate_draft(changed,format_name='linkedin',evidence_records=[evidence()])
        d['claim_references'].append(deepcopy(d['claim_references'][0]))
        with self.assertRaises(ContractError):validate_draft(d,format_name='linkedin',evidence_records=[evidence()])

    def test_nested_ad_claim_binding_and_unretrieved_or_partial_evidence(self):
        d=draft('ads');d['claim_references']=[{'content_field':'concepts.1.body','claim_ids':['PROD-002']}]
        validate_draft(d,format_name='ads',evidence_records=[evidence()])
        for mode in ['absent','partial','synthetic','unknown_id']:
            d=deepcopy(d);records=[evidence()]
            if mode=='absent':records=[]
            elif mode=='partial':records[0]['usable_as_complete_evidence']=False
            elif mode=='synthetic':records=[evidence('synthetic_product_intent','REQ-007')]
            else:d['claim_references'][0]['claim_ids']=['PROD-999']
            with self.assertRaises(ContractError):validate_draft(d,format_name='ads',evidence_records=records)

    def test_evidence_digest_identity_scope_and_reference_status_are_checked(self):
        d=draft();d['claim_references']=[{'content_field':'body','claim_ids':['PROD-002']}]
        for mode in ['digest','unit','source','reference_status']:
            row=evidence()
            if mode=='digest':row['evidence_sha256']='0'*64
            elif mode=='unit':row['unit_id']='PROD-003'
            elif mode=='source':row['evidence_payload']['product_id']='OTHER'
            else:row['reference_status']='incomplete'
            with self.assertRaises(ContractError):validate_draft(d,format_name='linkedin',evidence_records=[row])

    def test_structural_pass_is_not_a_semantic_or_cta_approval(self):
        # A schema cannot decide whether ordinary words assert unsupported offers.
        # Both examples still REQUIRE the future semantic Reviewer and harness gates.
        for wording in ['SAFE FIXTURE: explore the flavor story','SAFE FIXTURE: Buy now for 20% off']:
            d=draft();d['content']['cta']=wording
            result=validate_draft(d,format_name='linkedin',evidence_records=[])
            self.assertTrue(result['semantic_review_required']);self.assertNotIn('review_status',result)
            self.assertNotIn('human_approved',result)

    def test_templates_load_without_cwd_private_files_and_return_fresh_objects(self):
        original=os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory);one=load_template('linkedin');one['content_schema']['required']=[]
                self.assertIn('body',load_template('linkedin')['content_schema']['required'])
            finally:os.chdir(original)
        for fmt in ['../campaign_brief','nike','linkedin_post',None]:
            with self.assertRaises(ContractError):load_template(fmt)

    def test_malformed_config_duplicate_keys_unknown_schema_and_missing_file_fail(self):
        import launchlens.content_contracts as contracts
        with tempfile.TemporaryDirectory() as directory, patch.object(contracts,'TEMPLATE_DIR',Path(directory)):
            path=Path(directory)/'linkedin_post.json'
            with self.assertRaises(ContractError):load_template('linkedin')
            path.write_text('{"format":"linkedin","format":"email"}')
            with self.assertRaises(ContractError):load_template('linkedin')
        config=load_template('linkedin');config['content_schema']['unimplemented_rule']=True
        with patch.object(contracts,'_read_json',return_value=config),self.assertRaises(ContractError):load_template('linkedin')


if __name__=='__main__':unittest.main()
