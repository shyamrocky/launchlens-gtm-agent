"""Offline guards for the separately authorized single-call experiment."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
for name in ['src','tools']:sys.path.insert(0,str(ROOT/name))
import validate_projected_writer as runner
import test_writer_context as fixtures
from launchlens.linkedin_drafting import LinkedInWriter,writer_request
from launchlens.live_research import MODEL,dumps
from launchlens.writer_context import project_writer_input


class ProjectedRunnerTests(unittest.TestCase):
    def setUp(self):
        block=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))
        conn=block.start();self.addCleanup(block.stop)
        self.addCleanup(lambda:self.assertEqual(conn.call_count,0))

    def test_wrong_request_never_reaches_transport(self):
        calls=[];audit={}
        capture=runner.SingleCallCapture(lambda p:calls.append(p),audit,lambda:None)
        with self.assertRaises(ValueError):capture({'unexpected':'request'})
        self.assertFalse(capture.attempted);self.assertEqual(calls,[])

    def test_transport_failure_consumes_sole_attempt(self):
        payload={'SAFE':'fixture'};calls=[];audit={}
        def fail(p):
            calls.append(p);raise RuntimeError('SAFE outage')
        with patch.object(runner,'PROJECTED_REQUEST_SHA',hashlib.sha256(dumps(payload).encode()).hexdigest()):
            capture=runner.SingleCallCapture(fail,audit,lambda:None)
            with self.assertRaises(RuntimeError):capture(payload)
            with self.assertRaises(ValueError):capture(payload)
        self.assertEqual(len(calls),1);self.assertTrue(audit['sole_attempt_claimed'])

    def test_rejected_candidate_and_full_response_preserved_without_repair(self):
        inputs,policy=fixtures.fixture();candidate=fixtures.draft()
        candidate['claim_references'].append({'content_field':'cta','claim_ids':[]})
        response={'model':MODEL,'choices':[{'finish_reason':'stop','message':{
            'role':'assistant','content':json.dumps(candidate)}}],'id':'SAFE FIXTURE response'}
        payload=writer_request(project_writer_input(inputs,policy=policy)['model_input'])
        audit={};calls=[]
        def transport(p):calls.append(deepcopy(p));return deepcopy(response)
        with patch.object(runner,'PROJECTED_REQUEST_SHA',hashlib.sha256(dumps(payload).encode()).hexdigest()):
            capture=runner.SingleCallCapture(transport,audit,lambda:None)
            writer=LinkedInWriter(capture,context_projector=lambda i:project_writer_input(i,policy=policy))
            result=runner.write_and_validate(inputs,writer)
        self.assertEqual(result['status'],'WRITER_REJECTED');self.assertIsNone(result['draft'])
        self.assertEqual(result['diagnostic']['field_path'],'claim_references.1.claim_ids')
        self.assertEqual(result['diagnostic']['rule'],'array_length_invalid')
        self.assertEqual(audit['provider_response'],response)
        self.assertEqual(writer.calls[0]['candidate'],candidate);self.assertEqual(len(calls),1)

    def test_consumed_directory_blocks_before_credentials_or_transport(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runner,'OUTPUT',Path(d)), \
             patch.object(runner,'verified_context',return_value=({}, {}, {}, {})), \
             patch.object(runner,'read_keys') as keys,patch.object(runner,'NebiusHTTP') as http:
            with self.assertRaises(FileExistsError):runner.execute(None,None,None)
            keys.assert_not_called();http.assert_not_called()
