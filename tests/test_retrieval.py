"""Offline safe fixtures: bounded retrieval, evidence isolation and failure handling."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from launchlens.evidence_payload import storage_fields
from launchlens.retrieval import (SOURCES, NAMESPACE, MODEL, PRODUCT, PineconeHTTP,
    RetrievalError, retrieve_product_evidence)


def packet(unit='PROD-002', authority='public_product_facts', links=()):
    document, version, sha = SOURCES[authority]
    return {'chunk_id': f'{document}:v{version}:{unit}:' + 'a'*24, 'unit_id': unit,
        'document_id': document, 'document_version': version, 'authority': authority,
        'source_sha256': sha, 'product_id': PRODUCT, 'chunk_status': 'OWNER_REVIEW_PENDING',
        'source_acceptance': {'status': 'OWNER_ACCEPTED', 'source_sha256': sha},
        'primary_text': 'SAFE TEST FIXTURE: publisher label for US original 12 fl oz only.',
        'text': 'SAFE TEST FIXTURE: complete qualification; not independently tested.',
        'segments': [{'role': 'required_context', 'text': 'SAFE FIXTURE: scope retained'}],
        'source_references': [{'source_id': 'TEST-SOURCE', 'url': 'https://example.com/fixture',
                               'citation_role': 'claim_support'}],
        'claim_source_mappings': [{'source_id': 'TEST-SOURCE', 'limitation': 'SAFE TEST FIXTURE'}],
        'page_numbers': [2, 3], 'related_chunk_ids': list(links), 'related_claim_ids': [],
        'claim_ids': [unit], 'requirement_ids': [], 'chunk_kind': 'product_claim'}


def record(p, score=.9):
    return {'id': p['chunk_id'], 'score': score, 'metadata': storage_fields(p)}


class Fake:
    def __init__(self, hits=(), targets=()):
        self.hits = list(hits)
        self.targets = {p['chunk_id']: record(p) for p in targets}
        self.calls = []
        self.fail_fetch = False
        self.namespace = NAMESPACE

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == '/embed':
            return {'model': MODEL, 'data': [{'values': [1.] + [0.]*1023}]}
        if path == '/query':
            return {'namespace': self.namespace, 'matches': copy.deepcopy(self.hits)}
        if self.fail_fetch:
            raise RetrievalError('safe fixture transport failure')
        ids = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)['ids']
        return {'namespace': NAMESPACE, 'vectors': {i: self.targets[i] for i in ids if i in self.targets}}


class RetrievalTests(unittest.TestCase):
    def run_tool(self, fake, authority='public_product_facts', query='Prepare GTM evidence'):
        return retrieve_product_evidence(query, authority, transport=fake)

    def test_complete_packet_and_original_rank_retained(self):
        p = packet(); f = Fake([record(p)])
        result = self.run_tool(f)
        self.assertEqual(result['status'], 'evidence_found')
        self.assertEqual(result['records'][0]['evidence_payload'], p)
        self.assertEqual(result['search_ranking'][0]['rank'], 1)
        self.assertEqual([x[1] for x in f.calls], ['/embed', '/query'])
        self.assertEqual(f.calls[0][2]['parameters'], {'input_type': 'query', 'truncate': 'NONE'})
        self.assertEqual(f.calls[1][2]['filter'], {'product_id': {'$eq': PRODUCT},
                        'authority': {'$eq': 'public_product_facts'}})

    def test_live_parent_links_recover_missing_claim_deduplicated(self):
        target = packet(); p = packet('overview', links=[target['chunk_id']])
        f = Fake([record(p), record(packet('PROD-003'), .8)], [target])
        result = self.run_tool(f)
        self.assertEqual(result['status'], 'evidence_found')
        self.assertEqual(result['records'][-1]['unit_id'], 'PROD-002')
        self.assertEqual(result['records'][-1]['origin'], 'reference')
        self.assertIsNone(result['records'][-1]['search_rank'])
        self.assertEqual(len(f.calls), 3)
        self.assertEqual(len(result['search_ranking']), 2)
        f = Fake([record(p), record(target, .8)])
        self.assertEqual(len(self.run_tool(f)['records']), 2)
        self.assertEqual(len(f.calls), 2)

    def test_synthetic_reference_retains_public_authority(self):
        target = packet(); p = packet('audience', 'synthetic_product_intent', [target['chunk_id']])
        result = self.run_tool(Fake([record(p)], [target]), 'synthetic_product_intent')
        self.assertEqual(result['status'], 'evidence_found')
        self.assertEqual([r['authority'] for r in result['records']],
                         ['synthetic_product_intent', 'public_product_facts'])

    def test_public_to_synthetic_link_not_allowed(self):
        target = packet('REQ-007', 'synthetic_product_intent')
        result = self.run_tool(Fake([record(packet(links=[target['chunk_id']]))], [target]))
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['records']), 1)
        self.assertEqual(result['records'][0]['reference_status'], 'invalid')

    def test_global_five_reference_limit_and_no_recursion(self):
        targets = [packet('PROD-'+str(i)) for i in range(10, 16)]
        parent = packet('overview', links=[p['chunk_id'] for p in targets])
        targets[0]['related_chunk_ids'] = [packet('PROD-099')['chunk_id']]
        f = Fake([record(parent)], targets)
        result = self.run_tool(f)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['records']), 6)
        self.assertEqual(result['unresolved_reference_ids'], [targets[-1]['chunk_id']])
        self.assertEqual(result['records'][0]['reference_status'], 'incomplete')
        self.assertEqual(len(f.calls), 3)

    def test_missing_link_and_timeout_are_explicit(self):
        target = packet(); p = packet('overview', links=[target['chunk_id']])
        for fail in [False, True]:
            with self.subTest(fail=fail):
                f=Fake([record(p)]);f.fail_fetch=fail
                result=self.run_tool(f)
                self.assertEqual(result['status'], 'incomplete')
                self.assertEqual(result['records'][0]['unresolved_reference_ids'], [target['chunk_id']])
                self.assertEqual(len(result['records']), 1)
                self.assertEqual(len(f.calls), 3)

    def test_corrupt_digest_or_wrong_metadata_rejected(self):
        for field in ['evidence_json', 'chunk_id', 'authority']:
            with self.subTest(field=field):
                rec=record(packet());rec['metadata'][field]+='BROKEN'
                result=self.run_tool(Fake([rec]))
                self.assertEqual(result['status'], 'incomplete')
                self.assertEqual(result['records'], [])

    def test_wrong_product_source_version_and_source_acceptance_rejected(self):
        for field,value in [('product_id','OTHER'),('source_sha256','0'*64),
                            ('document_version','0.9'),('source_acceptance', {'status':'PENDING'})]:
            with self.subTest(field=field):
                p=packet();p[field]=value
                result=self.run_tool(Fake([record(p)]))
                self.assertEqual(result['records'], [])
                self.assertEqual(result['status'], 'incomplete')

    def test_wrong_category_and_wrong_namespace_rejected(self):
        f=Fake([record(packet('REQ-007','synthetic_product_intent'))])
        self.assertEqual(self.run_tool(f)['records'], [])
        f=Fake([record(packet())]);f.namespace='other'
        self.assertEqual(self.run_tool(f)['status'], 'error')

    def test_empty_matches_not_permission(self):
        result=self.run_tool(Fake())
        self.assertEqual(result['status'], 'incomplete')
        self.assertIn('neither absence nor permission',result['issues'][0]['message'])
        self.assertNotIn('Proceed',json.dumps(result))

    def test_duplicate_and_self_links_rejected(self):
        p=packet('overview');p['related_chunk_ids']=[p['chunk_id']]
        for links in [p['related_chunk_ids'],[packet()['chunk_id']]*2, [['not hashable']]]:
            p['related_chunk_ids']=links
            self.assertEqual(self.run_tool(Fake([record(p)]))['status'],'incomplete')

    def test_unexpected_fetch_record_and_wrong_target_identity_rejected(self):
        p=packet('overview',links=[packet()['chunk_id']]); f=Fake([record(p)], [packet()])
        f.targets[packet()['chunk_id']]['id']=packet('PROD-999')['chunk_id']
        self.assertEqual(len(self.run_tool(f)['records']),1)
        class Extra(Fake):
            def __call__(self,method,path,body=None):
                response=super().__call__(method,path,body)
                if path.startswith('/vectors/fetch'):
                    response['vectors'][packet('PROD-999')['chunk_id']]=record(packet('PROD-999'))
                return response
        result=self.run_tool(Extra([record(p)],[packet()]))
        self.assertEqual(len(result['records']),1)
        self.assertEqual(result['status'],'incomplete')

    def test_invalid_inputs_make_no_calls(self):
        for query,authority in [('', 'public_product_facts'),('x'*2001,'public_product_facts'),
                                ('q','unapproved'),(None,'public_product_facts')]:
            f=Fake()
            self.assertEqual(self.run_tool(f,authority,query)['status'],'error')
            self.assertEqual(f.calls,[])

    def test_invalid_vectors_stop_before_search(self):
        for values in [[0.]*1024,[1.]*1023,[float('nan')]*1024]:
            class Bad(Fake):
                def __call__(self,method,path,body=None):
                    self.calls.append((method,path,body))
                    return {'model': MODEL,'data':[{'values': values}]}
            f=Bad()
            self.assertEqual(self.run_tool(f)['status'],'error')
            self.assertEqual(len(f.calls),1)

    def test_http_restrictions_and_failure_do_not_expose_key_or_retry(self):
        client=PineconeHTTP('safe-fixture-key')
        for method,path in [('DELETE','/vectors/delete'),('POST','https://evil.example/query')]:
            with self.assertRaises(RetrievalError): client(method,path,{})
        for failure in [urllib.error.URLError('safe-fixture-key'),TimeoutError('safe-fixture-key'),
                        urllib.error.HTTPError('https://fixture',401,'safe-fixture-key',{},io.BytesIO())]:
            with patch.object(client._opener,'open',side_effect=failure) as call:
                with self.assertRaises(RetrievalError) as error:
                    client('POST','/embed',{})
                self.assertNotIn('safe-fixture-key',str(error.exception))
                self.assertEqual(call.call_count,1)

    def test_runtime_in_empty_directory_without_dependencies_or_env(self):
        with tempfile.TemporaryDirectory() as directory:
            code='import sys; sys.path.insert(0,'+repr(str(ROOT/'tests'))+'); from test_retrieval import Fake, packet, record; from launchlens.retrieval import retrieve_product_evidence; r=retrieve_product_evidence("GTM evidence", "public_product_facts", transport=Fake([record(packet())])); assert r["status"]=="evidence_found"'
            subprocess.run([sys.executable,'-S','-c',code],cwd=directory,check=True,
                           env={'PATH':'/usr/bin:/bin'})


if __name__=='__main__':
    unittest.main()
