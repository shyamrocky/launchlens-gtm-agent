"""Completed spans and local identity propagation through the real SDK/graph."""
from contextvars import Context
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from launchlens import observability as obs
from launchlens.offline_fixtures import request,ReviewFixtureTools
from launchlens.live_package import LivePackageRun,profile
from launchlens.writer_comparison import ProtectedStore
from test_live_package import Wire,permission,KEYS,NOW,FrozenDateTime,project
from test_observability import FakeClient

class TraceMetricsTests(unittest.TestCase):
    def setUp(self):
        self.net=self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('No network')))
        self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
        self.enterContext(patch('launchlens.live_package.datetime',FrozenDateTime))
        self.enterContext(patch('launchlens.live_package.project_writer_input',side_effect=project))
        self.client=FakeClient();self.client.read_run=Mock(side_effect=AssertionError('No GET /runs'))
        self.tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:self.client)
        self.enterContext(patch('launchlens.live_package.configured',return_value=self.tracer))
    def drain(self,tracer=None):
        tracer=tracer or self.tracer;limit=time.monotonic()+2
        while tracer.queue.unfinished_tasks and time.monotonic()<limit:time.sleep(.005)
        self.assertEqual(tracer.queue.unfinished_tasks,0);self.assertEqual(tracer.failed_operations,0)
    def live(self,store=None):
        run=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=Wire(),now=NOW,store=store)
        state=run.execute(run.snapshot()['run_id']);self.assertEqual(state['status'],'awaiting_human_review');return run,state

    def test_every_child_is_posted_once_complete_with_outputs_and_root_ended(self):
        run,state=self.live();self.drain()
        rows=self.client.created;roots=[r for r in rows if not r.get('parent_run_id')]
        self.assertEqual(len(roots),1);root=roots[0]
        children=[r for r in rows if r.get('parent_run_id')];self.assertTrue(children)
        for row in children:
            self.assertIsInstance(row['start_time'],datetime);self.assertIsInstance(row['end_time'],datetime)
            self.assertGreaterEqual(row['end_time'],row['start_time']);self.assertIn('outputs',row)
            self.assertTrue(row['outputs']);self.assertEqual(row['trace_id'],root['id'])
        # Children need no separate PATCH to acquire timing or usage.
        self.assertFalse(any(r['run_id'] in {c['id'] for c in children} for r in self.client.updated))
        self.assertTrue(any(r['run_id']==root['id'] and r['end_time']>=root['start_time'] for r in self.client.updated))
        llms=[r for r in children if r['run_type']=='llm'];self.assertEqual(len(llms),len(run.guard.events))
        total=Decimal(0)
        for row in llms:
            usage=row['outputs']['usage_metadata'];meta=row['extra']['metadata']
            self.assertEqual(row['outputs']['usage'],{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150})
            self.assertEqual(usage['input_tokens'],100);self.assertEqual(usage['output_tokens'],50);self.assertEqual(usage['total_tokens'],150)
            self.assertEqual(meta['ls_provider'],'nebius');self.assertTrue(meta['ls_model_name'])
            self.assertEqual(meta['usage_metadata'],usage);self.assertTrue(meta['cost_is_estimate'])
            self.assertAlmostEqual(usage['total_cost'],usage['input_cost']+usage['output_cost'],places=14)
            total+=Decimal(str(usage['total_cost']))
        self.assertAlmostEqual(float(total),float(run.guard.cost),places=12)
        gate=next(r for r in children if r['name']=='launch gate check')
        self.assertEqual(gate['outputs']['gate_decision'],'Proceed')

    def test_all_five_llm_roles_use_canonical_usage_and_profile_cost_fields(self):
        roles={'controller':'controller','Writer':'package_writer','Reviewer':'package_reviewer','revision Writer':'package_revision','citation repair':'package_writer'}
        with self.tracer.run({'run_id':'all-roles','request':request()}):
            for name,role in roles.items():
                cfg=profile()['roles'][role]
                result={'choices':[{'message':{'role':'assistant','content':'synthetic'}}], 'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}}
                self.assertIs(obs.llm(name,{'model':cfg['model_id'],'messages':[]},lambda:result,pricing=cfg),result)
        self.drain()
        for row in [r for r in self.client.created if r['run_type']=='llm']:
            cfg=profile()['roles'][roles[row['name']]];usage=row['outputs']['usage_metadata']
            self.assertEqual(row['extra']['metadata']['ls_model_name'],cfg['model_id'])
            self.assertAlmostEqual(usage['input_cost'],float(Decimal(100)*Decimal(cfg['input_per_million_usd'])/Decimal(1000000)),places=14)
            self.assertAlmostEqual(usage['output_cost'],float(Decimal(50)*Decimal(cfg['output_per_million_usd'])/Decimal(1000000)),places=14)

    def test_tool_evidence_count_and_failed_span_are_ended_without_exception_text(self):
        @obs.step('Pinecone search')
        def evidence():return {'records':[{'id':'synthetic-a'},{'id':'synthetic-b'}]}
        with self.tracer.run({'run_id':'tools','request':request()}):
            self.assertEqual(len(evidence()['records']),2)
            with self.assertRaises(RuntimeError):
                with obs.span('failed tool'):raise RuntimeError('SYNTHETIC-KEY user@example.com')
        self.drain()
        rows={r['name']:r for r in self.client.created}
        self.assertEqual(rows['Pinecone search']['outputs']['evidence_hit_count'],2)
        self.assertIn('end_time',rows['failed tool']);self.assertEqual(rows['failed tool']['outputs']['status'],'failed')
        self.assertNotIn('user@example.com',json.dumps(self.client.created,default=str))

    def test_graph_callback_can_end_in_a_different_context(self):
        from uuid import uuid4
        with self.tracer.run({'run_id':'copied-context','request':request()}):
            handler=obs.graph_callbacks()[0];identity=uuid4();one=Context();two=Context()
            # Carry the active root to one context, then close from another.
            one.run(obs._CURRENT.set,obs._CURRENT.get())
            one.run(handler.on_chain_start,{}, {'status':'running'},run_id=identity,metadata={'langgraph_node':'dispatch'},name='dispatch')
            two.run(handler.on_chain_end,{'status':'completed'},run_id=identity)
        self.drain();node=next(r for r in self.client.created if r['name']=='node:dispatch')
        self.assertIn('end_time',node);self.assertEqual(node['outputs']['status'],'completed')

    def test_supported_sdk_wire_posts_completed_children_and_never_gets_runs(self):
        from langsmith import Client
        sdk=Client(api_key='SYNTHETIC-KEY',api_url='https://api.smith.langchain.com',auto_batch_tracing=False,omit_traced_runtime_info=True)
        wire=[]
        def http(method,url,**kwargs):
            body=json.loads(kwargs['request_kwargs']['data']);wire.append((method,url,body))
            self.assertIn(method,{'POST','PATCH'})
            if method=='POST' and body.get('parent_run_id'):
                self.assertIn('end_time',body);self.assertIn('start_time',body);self.assertTrue(body.get('outputs'))
            if method=='PATCH':
                self.assertIn('start_time',body);self.assertEqual(body['run_type'],'chain');self.assertIn('end_time',body)
            return Mock(status_code=202)
        with patch.object(Client,'request_with_retries',side_effect=http),patch.object(Client,'read_run',side_effect=AssertionError('Deprecated lookup')) as lookup:
            tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:sdk)
            with tracer.run({'run_id':'sdk-wire','request':request()}):
                obs.llm('Writer',{'model':'synthetic-model','messages':[]},lambda:{'choices':[],'usage':{'prompt_tokens':2,'completion_tokens':3,'total_tokens':5}},pricing={'input_per_million_usd':'1','output_per_million_usd':'2'})
            self.drain(tracer);lookup.assert_not_called()
        child=next(body for method,_,body in wire if method=='POST' and body.get('parent_run_id'))
        self.assertEqual(child['outputs']['usage_metadata']['total_tokens'],5)
        self.assertAlmostEqual(child['outputs']['usage_metadata']['total_cost'],.000008,places=14)
        self.assertEqual(child['extra']['metadata']['ls_provider'],'nebius')

    def test_saved_review_restore_and_revision_reuse_local_trace_context_without_lookup(self):
        from launchlens.review_decisions import decision_book,grouped_findings,record_decision,revision_feedback
        with tempfile.TemporaryDirectory() as folder:
            store=ProtectedStore(Path(folder)/'run');run,state=self.live(store);self.drain()
            path=store.path/'langsmith-trace-context.json';saved=path.read_bytes();identity=json.loads(saved)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            capture=run.capture();original=deepcopy(state)
            other=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:self.client)
            with patch('launchlens.live_package.configured',return_value=other):
                restored=LivePackageRun(permission(),KEYS,tools=ReviewFixtureTools(),wire_factory=Wire(),now=NOW,store=store,checkpoint=(state,capture))
                self.assertEqual(restored.snapshot(),original)
                book=decision_book(state);group=next(g for g in grouped_findings(state) if g['needs_attention'])
                book=record_decision(state,book,group['id'],'request_changes')
                restored.request_revision(state['run_id'],revision_feedback(state,book,''),draft_version=1,draft_sha256=state['package']['package_sha256'])
                result=restored.execute(state['run_id']);self.assertEqual(result['status'],'awaiting_human_review')
            self.drain(other);self.client.read_run.assert_not_called();self.assertEqual(path.read_bytes(),saved)
            roots=[r for r in self.client.created if not r.get('parent_run_id')]
            self.assertEqual({r['id'] for r in roots},{identity['root_id']})
            self.assertEqual({r['dotted_order'] for r in roots},{identity['dotted_order']})
            for child in [r for r in self.client.created if r.get('parent_run_id')]:
                self.assertTrue(child['dotted_order'].startswith(identity['dotted_order']+'.'))
            self.assertNotIn('trace_context',restored.snapshot())

    def test_invalid_or_unwritable_context_is_nonfatal_and_logs_no_private_data(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ProtectedStore(Path(folder)/'run');bad={'run_id':'SYNTHETIC-KEY user@example.com'}
            store.write('langsmith-trace-context.json',bad);path=store.path/'langsmith-trace-context.json';before=path.read_bytes()
            with self.assertLogs('launchlens.observability',level='WARNING') as logs:
                self.tracer.bind_context({'run_id':'safe'},store)
            self.assertEqual(path.read_bytes(),before);self.assertNotIn('user@example.com',' '.join(logs.output))
            with self.tracer.run({'run_id':'safe','request':request()}):pass
            self.drain()
        broken=Mock();broken.path=Path('/nonexistent/synthetic-trace-test');broken.write.side_effect=PermissionError('SYNTHETIC-KEY user@example.com')
        with self.assertLogs('launchlens.observability',level='WARNING'):
            self.tracer.bind_context({'run_id':'cannot-save'},broken)
        with self.tracer.run({'run_id':'cannot-save','request':request()}):pass
        self.drain()

    def test_unknown_usage_never_invents_cost(self):
        with self.tracer.run({'run_id':'unknown-usage','request':request()}):
            obs.llm('Writer',{'model':'synthetic'},lambda:{'choices':[]},pricing={'input_per_million_usd':'1','output_per_million_usd':'2'})
        self.drain();row=next(r for r in self.client.created if r['run_type']=='llm')
        self.assertEqual(row['outputs']['usage_metadata'],{});self.assertNotIn('cost_is_estimate',row['extra']['metadata'])

if __name__=='__main__':unittest.main()
