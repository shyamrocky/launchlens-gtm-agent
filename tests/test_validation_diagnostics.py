"""Bounded, validator-authored diagnostics; safe fixtures only, no external services."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from launchlens.content_contracts import ContractError, validate_draft, validation_detail
from test_content_contracts import draft, evidence


class ValidationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline network attempt'))
        connection=blocker.start();self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))

    def failure(self, value, records=None, fmt='linkedin'):
        with self.assertRaises(ContractError) as caught:
            validate_draft(value,format_name=fmt,evidence_records=[] if records is None else records)
        return caught.exception.diagnostic

    def test_missing_required_body_is_explicit(self):
        value=draft();del value['content']['body']
        self.assertEqual(self.failure(value),{'field_path':'content.body','rule':'required_field_missing'})

    def test_wrong_types_and_empty_strings_have_exact_field_rules(self):
        for field,bad,path,rule in [
            ('body',42,'content.body','invalid_type'),
            ('hashtags','SAFE','content.hashtags','invalid_type'),
            ('hashtags',[False],'content.hashtags.0','invalid_type'),
            ('body','   ','content.body','nonempty_text_required')]:
            value=draft();value['content'][field]=bad
            with self.subTest(field=field,bad=bad):
                self.assertEqual(self.failure(value),{'field_path':path,'rule':rule})

    def test_unexpected_keys_report_parent_without_copying_sensitive_key_or_value(self):
        secret='SAFE-SENSITIVE-SENTINEL-never-a-real-credential'
        value=draft();value['content'][secret]={'source_payload':secret}
        detail=self.failure(value)
        self.assertEqual(detail,{'field_path':'content','rule':'unexpected_field'})
        self.assertNotIn(secret,json.dumps(detail));self.assertNotIn('source_payload',json.dumps(detail))

    def test_invalid_claim_and_content_references_report_reference_slots(self):
        value=draft();value['claim_references']=[{'content_field':'body','claim_ids':['SAFE-SENSITIVE-ID']}]
        self.assertEqual(self.failure(value,[evidence()]),{
            'field_path':'claim_references.0.claim_ids.0','rule':'invalid_claim_reference'})
        value['claim_references']=[{'content_field':'SAFE-SENSITIVE-PATH','claim_ids':['PROD-002']}]
        self.assertEqual(self.failure(value,[evidence()]),{
            'field_path':'claim_references.0.content_field','rule':'invalid_content_field_reference'})
        value['claim_references']=[{'content_field':'body','claim_ids':['PROD-002']}]*2
        self.assertEqual(self.failure(value,[evidence()]),{
            'field_path':'claim_references.1.content_field','rule':'duplicate_field_reference'})

    def test_corrupt_evidence_reports_record_without_source_content(self):
        row=evidence();row['evidence_payload']['primary_text']='SAFE-SENSITIVE-SOURCE-PAYLOAD'
        value=draft();value['claim_references']=[{'content_field':'body','claim_ids':['PROD-002']}]
        detail=self.failure(value,[row])
        self.assertEqual(detail,{'field_path':'evidence_records.0','rule':'evidence_validation_failed'})
        self.assertNotIn('SAFE-SENSITIVE',json.dumps(detail))

    def test_nested_shape_array_count_enum_and_duplicate_rules(self):
        value=draft('ads');del value['content']['concepts'][1]['cta']
        self.assertEqual(self.failure(value,fmt='ads'),{
            'field_path':'content.concepts.1.cta','rule':'required_field_missing'})
        value=draft('ads');value['content']['concepts'].pop()
        self.assertEqual(self.failure(value,fmt='ads'),{
            'field_path':'content.concepts','rule':'array_length_invalid'})
        value=draft();value['format']='email'
        self.assertEqual(self.failure(value),{'field_path':'format','rule':'invalid_enum_value'})
        value=draft();value['claim_references']=[{'content_field':'body','claim_ids':['PROD-002']*2}]
        self.assertEqual(self.failure(value,[evidence()]),{
            'field_path':'claim_references.0.claim_ids','rule':'duplicate_array_item'})

    def test_valid_fixtures_keep_existing_result_and_editorial_advisories(self):
        for fmt in ['campaign_brief','linkedin','email','blog','ads']:
            result=validate_draft(draft(fmt),format_name=fmt,evidence_records=[])
            self.assertEqual(set(result),{'structural_validation','editorial_warnings','semantic_review_required'})
            self.assertEqual(result['structural_validation'],'passed');self.assertTrue(result['semantic_review_required'])
        value=draft();value['content']['body']=' '.join(['SAFE']*250)
        self.assertTrue(validate_draft(value,format_name='linkedin',evidence_records=[])['editorial_warnings'])

    def test_unknown_or_sensitive_diagnostics_fall_back_without_message_inference(self):
        fallback={'field_path':None,'rule':'unknown_validation_failure'}
        # A message resembling a validation error does not become trusted metadata.
        error=ContractError('content.body: invalid type; SAFE-SENSITIVE-EXCEPTION')
        self.assertEqual(error.diagnostic,fallback)
        for path,rule in [('content.SAFE-SENSITIVE-KEY','invalid_type'),
                          ('content.body','SAFE-SENSITIVE-RULE'),
                          ('content.hashtags.1234567','invalid_type'),
                          (None,'invalid_type')]:
            self.assertEqual(validation_detail(path,rule),fallback)
        self.assertEqual(validation_detail('draft.content.body','required_field_missing'),{
            'field_path':'content.body','rule':'required_field_missing'})


if __name__=='__main__':unittest.main()
