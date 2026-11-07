"""M2.2b audit contract tests: safe fixtures, zero network or credential access."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
for folder in ['src','tools','tests']:sys.path.insert(0,str(ROOT/folder))
import validate_live_restrictions as audit
from launchlens.agent_foundation import FoundationSession
from launchlens.live_research import ResearchModel, LiveResearchTools
from launchlens.notion_tools import NotionReader, NotionReadError, READINESS, PMM_PAGE
from foundation_fixtures import action
from test_live_research import MockChat
from test_launch_checks import FakeNotion


class LiveRestrictionTests(unittest.TestCase):
    def setUp(self):
        blocker=patch.object(socket.socket,'connect',side_effect=AssertionError('Offline network attempt'))
        connection=blocker.start();self.addCleanup(blocker.stop)
        self.addCleanup(lambda:self.assertEqual(connection.call_count,0))

    def simulate(self, case):
        transport=FakeNotion();transport.events=[]
        source=audit.ReadinessUnavailable(transport) if case['fault'] else transport
        actions=[action('check_launch','launch')]
        if case['id']!='india':
            actions.append(action('request_clarification','question',question='Safe fixture: resolve the missing operational evidence in the authorized tracker.'))
        def no_pinecone(*args):raise AssertionError('Unexpected search')
        session=FoundationSession(ResearchModel(MockChat(actions)),
            LiveResearchTools(NotionReader(source),no_pinecone),mode='live_research')
        state=session.run(session.start(audit.request(case))['run_id'])
        faults=source.faults if case['fault'] else []
        return state,faults,transport

    def test_all_three_real_adapter_compositions_meet_fixed_audit_expectations(self):
        for case in audit.CASES:
            with self.subTest(case=case['id']):
                state,faults,_=self.simulate(case)
                result=audit.evaluate(case,state,faults)
                self.assertEqual(result['verdict'],'PASS',result)

    def test_failure_persists_and_never_forwards_readiness_query(self):
        transport=FakeNotion();transport.events=[]
        source=audit.ReadinessUnavailable(transport)
        for _ in range(2):
            with self.assertRaises(NotionReadError):source('POST',f'/data_sources/{READINESS}/query',{})
        self.assertEqual(transport.calls,[]);self.assertEqual(len(source.faults),2)
        self.assertTrue(all(not f['forwarded_to_service'] for f in source.faults))
        self.assertEqual(source('GET',f'/pages/{PMM_PAGE}'),{'id':PMM_PAGE})
        self.assertEqual(len(transport.calls),1)

    def test_reader_discards_partial_launch_data_on_injected_failure(self):
        state,faults,transport=self.simulate(audit.CASES[2])
        self.assertTrue(faults);self.assertEqual(state['launch']['readiness_evidence'],[])
        self.assertEqual(state['launch']['conditions'][0]['code'],'source_unavailable')
        self.assertFalse(any(method=='POST' and path==f'/data_sources/{READINESS}/query'
            for method,path,_ in transport.calls))

    def test_evaluator_rejects_permission_without_records_and_wrong_scope(self):
        case=audit.CASES[0];state,faults,_=self.simulate(case)
        for mutation in ['permission','scope','no_question','no_missing_row','draft']:
            changed=deepcopy(state)
            if mutation=='permission':changed['launch']['promotional_draft_allowed']=True
            elif mutation=='scope':changed['request']['market_id']='US'
            elif mutation=='no_question':changed['clarification']=''
            elif mutation=='draft':changed['drafts']={'linkedin':'Unpermitted draft'}
            else:changed['launch']['readiness_evidence']=[]
            self.assertEqual(audit.evaluate(case,changed,faults)['verdict'],'REVIEW_REQUIRED')

    def test_failure_must_be_exercised_and_india_must_observe_pending_auth(self):
        state,faults,_=self.simulate(audit.CASES[2])
        self.assertEqual(audit.evaluate(audit.CASES[2],state,[])['verdict'],'REVIEW_REQUIRED')
        state,_,_=self.simulate(audit.CASES[1]);state['launch']['readiness_evidence']=[]
        self.assertEqual(audit.evaluate(audit.CASES[1],state,[])['verdict'],'REVIEW_REQUIRED')

    def test_report_is_readable_and_labels_local_failure(self):
        case=audit.CASES[2];state,faults,_=self.simulate(case)
        receipt={'case':case,'status':'PASS','model_actions':[
            {'turn':i+1,'action':v['action']} for i,v in enumerate(state['ledger'].values())],
            'evaluation':audit.evaluate(case,state,faults),'elapsed_seconds':0,'usage':{}}
        report=audit.render(receipt,state)
        self.assertIn('INJECTED LOCALLY',report);self.assertIn('source_unavailable',report)
        self.assertIn('Question for the user',report);self.assertIn('request_clarification',report)

    def test_existing_output_blocks_before_keys_clients_or_case_execution(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(audit,'OUTPUT',Path(directory)), \
                patch.object(audit,'read_keys') as keys, patch.object(audit,'execute_case') as case:
            with self.assertRaisesRegex(ValueError,'no rerun'):audit.execute()
            keys.assert_not_called();case.assert_not_called()

    def test_suite_stops_on_failed_case_and_does_not_run_later_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'run'
            def failed(case,path,keys):
                path.mkdir();(path/'receipt.json').write_text('{}')
                return {'status':'REVIEW_REQUIRED','run_id':'safe-fixture','usage':{},'elapsed_seconds':0}
            with patch.object(audit,'OUTPUT',output),patch.object(audit,'read_keys',return_value={}), \
                    patch.object(audit,'execute_case',side_effect=failed) as execute, patch('builtins.print'):
                audit.execute();self.assertEqual(execute.call_count,1)
            self.assertEqual(json.loads((output/'suite.json').read_text())['status'],'REVIEW_REQUIRED')


if __name__=='__main__':unittest.main()
