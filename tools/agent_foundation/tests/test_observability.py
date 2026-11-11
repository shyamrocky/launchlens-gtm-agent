"""Opt-in telemetry over actual graph/live flows; synthetic data and no sockets."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import socket
import sys
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools/agent_foundation/tests')]
from launchlens import observability as obs
from launchlens.agent_foundation import FoundationSession
from launchlens.offline_fixtures import FixtureTools, ScriptedModel, ReviewFixtureTools, request, action, research_script
from launchlens.live_package import LivePackageRun, preflight
from test_live_package import Wire, permission, KEYS, NOW, FrozenDateTime, project


class FakeClient:
    def __init__(self): self.created = []; self.updated = []
    def create_run(self, **values): self.created.append(deepcopy(values))
    def update_run(self, **values):
        assert isinstance(values.get('end_time', datetime.now()), datetime)
        self.updated.append(deepcopy(values))


class TracingTests(unittest.TestCase):
    def setUp(self):
        self.net = self.enterContext(patch.object(socket.socket, 'connect', side_effect=AssertionError('No network')))
        self.addCleanup(lambda: self.assertEqual(self.net.call_count, 0))
        self.enterContext(patch('launchlens.live_package.datetime', FrozenDateTime))
        self.enterContext(patch('launchlens.live_package.project_writer_input', side_effect=project))
        self.client = FakeClient()
        self.tracer = obs.Tracer('SYNTHETIC-LANGSMITH-SECRET', 'offline-test', secrets=tuple(KEYS.values()), client_factory=lambda _: self.client)
        self.enterContext(patch('launchlens.agent_foundation.configured', return_value=self.tracer))

    def delivered(self):
        deadline = time.monotonic() + 2
        while self.tracer.queue.unfinished_tasks and time.monotonic() < deadline: time.sleep(.005)
        self.assertEqual(self.tracer.queue.unfinished_tasks, 0)
        self.assertEqual(self.tracer.failed_operations,0)
        return self.client.created

    def live(self, market='US', wire=None, tracer=True):
        grant = permission()
        if market != 'US':
            grant['request'] = request(market)
            grant['scope_sha256'] = preflight(request=request(market))['scope_sha256']
        run = LivePackageRun(grant, KEYS, tools=ReviewFixtureTools(), wire_factory=wire or Wire(), now=NOW)
        if not tracer: run.session._tracer = None
        return run

    def test_disabled_ignores_inherited_tracing_and_makes_no_client_calls(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'LANGSMITH_TRACING':'false', 'LANGSMITH_API_KEY':'SYNTHETIC-KEY', 'LANGCHAIN_TRACING_V2':'true'}), patch('langsmith.Client') as sdk:
            self.assertIsNone(obs.configured(path=Path(folder)/'.env'))
            session = FoundationSession(ScriptedModel(research_script()), FixtureTools())
            state = session.start(request()); self.assertEqual(session.run(state['run_id'])['status'], 'research_complete')
            with patch('launchlens.agent_foundation.configured', side_effect=lambda: obs.configured(path=Path(folder)/'.env')):
                run=self.live();self.assertIsNone(run.session._tracer)
                self.assertEqual(run.execute(run.snapshot()['run_id'])['status'],'awaiting_human_review')
            sdk.assert_not_called()
        self.assertFalse(self.client.created)

    def test_settings_read_private_env_without_mutation_and_require_true(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {}, clear=True):
            path = Path(folder)/'.env'
            path.write_text('LANGSMITH_TRACING=true\nLANGSMITH_API_KEY=SYNTHETIC-KEY\nLANGSMITH_PROJECT=demo-test\nNEBIUS_API_KEY=NEVER-EXPORT\n')
            before = dict(obs.os.environ)
            tracer = obs.configured(path=path, client_factory=lambda _: self.client)
            self.assertEqual(tracer.project, 'demo-test'); self.assertEqual(dict(obs.os.environ), before)
            self.assertIn('NEVER-EXPORT', tracer.secrets)
            path.write_text('LANGSMITH_TRACING=1\nLANGSMITH_API_KEY=SYNTHETIC-KEY\n')
            self.assertIsNone(obs.configured(path=path))

    def test_live_graph_spans_models_usage_and_controller_why(self):
        run = self.live(); state = run.execute(run.snapshot()['run_id'])
        self.assertEqual(state['status'], 'awaiting_human_review')
        rows = self.delivered(); names = {r['name'] for r in rows}
        self.assertTrue({'node:decide','node:dispatch','node:required_review','Writer','Reviewer','controller','controller_action','launch gate check','risky-phrase scan'} <= names, names)
        root = next(r for r in rows if not r.get('parent_run_id'))
        self.assertEqual(root['name'], 'cherry-float-gtm · market=US · ' + state['run_id'])
        self.assertIn('scope_value=US', root['tags'])
        by_id = {r['id']:r for r in rows}
        for row in rows:
            self.assertEqual(row['trace_id'], root['id'])
            if row.get('parent_run_id'): self.assertIn(row['parent_run_id'], by_id)
        llms = [r for r in rows if r['run_type']=='llm']
        self.assertTrue(all(by_id[r['parent_run_id']]['name'].startswith('node:') for r in llms))
        for row in llms:
            self.assertIsNotNone(row.get('end_time'))
            self.assertGreaterEqual(row['end_time'],row['start_time'])
            self.assertEqual(row['outputs']['usage_metadata']['total_tokens'],150)
            self.assertEqual(row['extra']['metadata']['usage_metadata'],row['outputs']['usage_metadata'])
            self.assertGreaterEqual(row['extra']['metadata']['latency_seconds'],0)
        self.assertTrue(any(r['inputs'].get('why','').startswith('MOCK:') for r in rows if r['name']=='controller_action'))
        self.assertTrue(any(r.get('extra',{}).get('metadata',{}).get('gate_decision')=='Proceed' for r in self.client.updated))

    def test_clarification_resume_uses_same_root(self):
        actions = [action('read_pmm_brief','pmm'), action('check_launch','launch'),
                   action('request_clarification','ask',market_id='UK',question='Choose a drafting scope'), action('generate_package','write')]
        from unittest.mock import Mock
        self.client.read_run=Mock(side_effect=AssertionError('No lookup for new or paused in-process run'))
        run = self.live('UK', Wire(actions=actions)); state = run.execute(run.snapshot()['run_id'])
        self.assertEqual(state['status'],'needs_clarification'); self.delivered()
        state = run.resume(state['run_id'],'draft_without_availability')
        self.assertEqual(state['status'],'awaiting_human_review')
        rows = self.delivered(); roots = [r for r in rows if not r.get('parent_run_id')]
        self.assertEqual(len(roots),1)
        self.assertTrue({'human_interrupt','human_resume','node:clarify','node:required_objective_evidence'} <= {r['name'] for r in rows})
        self.assertEqual({r['trace_id'] for r in rows},{roots[0]['id']})
        self.client.read_run.assert_not_called()

    def test_missing_key_and_failed_client_do_not_fail_run(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{'LANGSMITH_TRACING':'true','LANGSMITH_API_KEY':''}):
            self.assertIsNone(obs.configured(path=Path(folder)/'.env'))
            with patch('launchlens.agent_foundation.configured', side_effect=lambda: obs.configured(path=Path(folder)/'.env')):
                run=self.live();self.assertIsNone(run.session._tracer)
                self.assertEqual(run.execute(run.snapshot()['run_id'])['status'],'awaiting_human_review')
        def broken(_): raise RuntimeError('SYNTHETIC-LANGSMITH-SECRET unreachable')
        tracer = obs.Tracer('SYNTHETIC-LANGSMITH-SECRET','test',client_factory=broken)
        run = self.live(); run.session._tracer=tracer
        with self.assertLogs('launchlens.observability',level='WARNING') as logs:
            state=run.execute(run.snapshot()['run_id']); self.assertEqual(state['status'],'awaiting_human_review')
            self.drain(tracer)
        self.assertTrue(tracer.worker.is_alive());self.assertGreater(tracer.failed_operations,0)
        self.assertNotIn('SYNTHETIC-LANGSMITH-SECRET',' '.join(logs.output))

    def test_slow_delivery_and_full_queue_never_block_run(self):
        entered=Event(); release=Event()
        def slow(_): entered.set(); release.wait(4); return self.client
        tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=slow,capacity=2)
        self.addCleanup(release.set)
        run=self.live(); run.session._tracer=tracer
        started=time.monotonic(); state=run.execute(run.snapshot()['run_id'])
        self.assertEqual(state['status'],'awaiting_human_review')
        self.assertTrue(entered.is_set()); self.assertLess(time.monotonic()-started,2)
        self.assertLessEqual(tracer.queue.qsize(),2);release.set()

    def test_generic_scope_all_and_stable_identity_after_exporter_recreation(self):
        state={'run_id':'synthetic-run','request':{'use_case_id':'another-use-case','product_id':'another-product','scope':{'type':'audience','value':'partners'}}}
        root=self.tracer.root(state)
        self.assertIn('audience=partners',root['name'])
        self.assertEqual(obs.Tracer('KEY','test',client_factory=lambda _:self.client).root(state)['id'],root['id'])
        state['request'].pop('scope');state['run_id']='scope-free'
        self.assertIn(' · all · ',self.tracer.root(state)['name'])

    def test_privacy_filters_strings_nested_json_unknown_objects_and_private_paths(self):
        with self.tracer.run({'run_id':'privacy','request':{'use_case_id':'test'}}):
            with obs.span('safe',{'content':json.dumps({'text':'draft person@example.com TEST-NEBIUS-CREDENTIAL','ledger':{'amount':'secret-ledger'},'receipt':'human-decision-secret.json'}),'headers':{'Authorization':'bad'},'store':object(),'note':'data/private/secret.json'}) as record:
                record['outputs']={'text':'SYNTHETIC-LANGSMITH-SECRET','credentials':KEYS}
        self.delivered();text=json.dumps(self.client.created+self.client.updated,default=str)
        for private in ['person@example.com','TEST-NEBIUS-CREDENTIAL','secret-ledger','human-decision-secret.json','data/private/secret.json','SYNTHETIC-LANGSMITH-SECRET','Authorization']:
            self.assertNotIn(private,text)
        self.assertIn('draft',text)

    def test_download_is_observed_at_request_only_and_keeps_export_bytes(self):
        state={'run_id':'download-test','request':request(),'package':{'version':2}}
        with patch.object(obs,'configured',return_value=self.tracer):
            data=obs.download_data(state,'identical markdown');self.assertTrue(callable(data));self.assertFalse(self.client.created)
            self.assertEqual(data(),'identical markdown')
        rows=self.delivered();self.assertEqual([r['name'] for r in rows if r['run_type']=='tool'],['download'])

    def test_human_revision_and_exact_submission_attach_to_original_tree(self):
        from launchlens.review_decisions import decision_book, grouped_findings, record_decision, revision_feedback, safe_hints
        for exact in (False,True):
            run=self.live(); state=run.execute(run.snapshot()['run_id'])
            book=decision_book(state)
            group=next(g for g in grouped_findings(state) if g['needs_attention'] and (not exact or safe_hints(g)))
            hint=safe_hints(group)[0] if exact else None
            book=record_decision(state,book,group['id'],'request_changes',suggestion=hint)
            feedback=revision_feedback(state,book,'Keep the scoped evidence.')
            run.request_revision(state['run_id'],feedback,draft_version=state['package']['version'],draft_sha256=state['package']['package_sha256'])
            state=run.execute(state['run_id'])
            self.assertEqual(state['status'],'awaiting_human_review')
        rows=self.delivered();self.assertEqual(len([r for r in rows if not r.get('parent_run_id')]),2)
        self.assertTrue({'revision Writer','exact-replacement apply','human_resume'} <= {r['name'] for r in rows})
        self.assertEqual(len([r for r in rows if r['name']=='revision Writer']),1)
        for row in [r for r in rows if r['run_type']=='llm']:
            self.assertIn('end_time',row);self.assertIn('total_cost',row['outputs']['usage_metadata'])

    def test_automatic_revision_and_citation_repair_are_child_llm_spans(self):
        from test_automatic_refinement import BlockingWire
        grant=permission();grant['allow_automatic_refinement']=True
        run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=BlockingWire(),now=NOW)
        state=run.execute(run.snapshot()['run_id']);self.assertEqual(state['package']['version'],2)
        rows=self.delivered();revision=next(r for r in rows if r['name']=='revision Writer')
        parent=next(r for r in rows if r['id']==revision['parent_run_id'])
        self.assertEqual(parent['name'],'node:required_refine')
        from test_citation_repair import CitationRepairTests
        scenario=CitationRepairTests();scenario.setUp()
        try:
            repaired,state,_,_=scenario.run_case([('email','subject')],market='UK')
            self.assertEqual(state['status'],'awaiting_human_review')
        finally:scenario.doCleanups()
        rows=self.delivered();repair=next(r for r in rows if r['name']=='citation repair')
        self.assertEqual(repair['run_type'],'llm')
        self.assertIn('end_time',repair);self.assertIn('total_cost',repair['outputs']['usage_metadata'])
        self.assertEqual(repair['extra']['metadata']['ls_provider'],'nebius')
        root=next(r for r in rows if r['id']==repair['trace_id'])
        self.assertIn('market=UK',root['name'])
        self.assertTrue(any(r['name']=='human_resume' and r['trace_id']==repair['trace_id'] for r in rows))

    def test_real_tool_adapters_are_observed_without_credentials_or_network(self):
        from unittest.mock import Mock
        from launchlens.live_research import LiveResearchTools
        notion=Mock();notion.get_pmm_brief.return_value={'text':'synthetic brief'}
        notion.get_launch_context.return_value={'text':'synthetic launch context'}
        tools=LiveResearchTools(notion,Mock())
        with self.tracer.run({'run_id':'tools-test','request':request()}), patch('launchlens.live_research.retrieve_product_evidence',return_value={'results':[]}), patch('launchlens.retrieval.fetch_objective_claims',return_value={'results':[]}):
            tools.read_pmm(request());tools.read_launch(request());tools.search('synthetic query','public_product_facts');tools.fetch_objective_claims(['PROD-002'])
        rows=self.delivered();self.assertTrue({'Notion read','Pinecone search','required claim fetch'} <= {r['name'] for r in rows})

    def test_client_create_and_update_errors_leave_requests_and_usage_unchanged(self):
        for failing_method in ('create_run','update_run'):
            with self.subTest(failing_method=failing_method):
                client=FakeClient()
                setattr(client,failing_method,lambda **_: (_ for _ in ()).throw(RuntimeError('unreachable')))
                tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:client)
                wire=Wire();run=self.live(wire=wire);run.session._tracer=tracer
                with self.assertLogs('launchlens.observability',level='WARNING'):
                    state=run.execute(run.snapshot()['run_id']);self.drain(tracer)
                self.assertEqual(state['status'],'awaiting_human_review');self.assertEqual(len(wire.calls),6)
                self.assertEqual(sum(run.guard.counts.values()),6)

    def test_exporter_restart_reattaches_existing_root_and_preserves_dotted_order(self):
        from unittest.mock import Mock
        from launchlens.writer_comparison import ProtectedStore
        with tempfile.TemporaryDirectory() as folder:
            store=ProtectedStore(Path(folder)/'run');state={'run_id':'restart-test','request':request()}
            self.tracer.bind_context(state,store)
            with self.tracer.run(state):pass
            old=self.tracer.root(state);self.delivered();saved=(store.path/'langsmith-trace-context.json').read_bytes()
            self.client.read_run=Mock(side_effect=AssertionError('No deprecated lookup'))
            other=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:self.client)
            other.bind_context({**state,'status':'needs_clarification','turns':3},store)
            with other.run(state):
                with obs.span('after restart'):pass
            self.drain(other)
            self.assertEqual(other.failed_operations,0);self.client.read_run.assert_not_called()
            roots=[r for r in self.client.created if not r.get('parent_run_id')]
            self.assertEqual({r['id'] for r in roots},{old['id']})
            self.assertEqual({r['dotted_order'] for r in roots},{old['dotted_order']})
            child=next(r for r in self.client.created if r['name']=='after restart')
            self.assertEqual(child['parent_run_id'],old['id']);self.assertTrue(child['dotted_order'].startswith(old['dotted_order']+'.'))
            self.assertEqual((store.path/'langsmith-trace-context.json').read_bytes(),saved)

    def test_enabled_and_disabled_make_identical_requests_and_package_results(self):
        from uuid import UUID
        with patch('launchlens.agent_foundation.uuid4',return_value=UUID('11111111-2222-4333-8444-555555555555')):
            off_wire=Wire();off=self.live(wire=off_wire,tracer=False);off_state=off.execute(off.snapshot()['run_id'])
            on_wire=Wire();on=self.live(wire=on_wire);on_state=on.execute(on.snapshot()['run_id'])
        self.assertEqual(off_wire.calls,on_wire.calls)
        self.assertEqual(off.guard.counts,on.guard.counts);self.assertEqual(off.guard.cost,on.guard.cost)
        def stable(value):
            if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k!='elapsed_seconds'}
            if isinstance(value,list):return [stable(v) for v in value]
            return value
        self.assertEqual(stable(off_state),stable(on_state))
        self.delivered()

    def test_real_sdk_serializes_export_records_without_runtime_metadata(self):
        # Exercise the installed SDK's synchronous create/update transformation,
        # intercepting its HTTP boundary. This catches fake-client blind spots.
        from langsmith import Client
        client=Client(api_key='SYNTHETIC-KEY',api_url='https://api.smith.langchain.com',auto_batch_tracing=False,omit_traced_runtime_info=True)
        with patch.object(Client,'request_with_retries') as request_http, patch.object(Client,'read_run',return_value=None) as lookup:
            tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:client)
            # No remote lookup in this SDK serialization test.
            state={'run_id':'sdk-test','request':request()}
            with tracer.run(state):
                obs.llm('Writer',{'model':'synthetic-model','messages':[]},lambda:{'choices':[],'usage':{'prompt_tokens':2,'completion_tokens':3,'total_tokens':5}})
            tracer.update(state)
            deadline=time.monotonic()+2
            while tracer.queue.unfinished_tasks and time.monotonic()<deadline:time.sleep(.005)
            self.assertEqual(tracer.failed_operations,0)
            self.assertGreaterEqual(request_http.call_count,4)
            lookup.assert_not_called()
            posted=[json.loads(call.kwargs['request_kwargs']['data']) for call in request_http.call_args_list if call.args[0]=='POST']
            self.assertTrue(posted);self.assertTrue(all('runtime' not in item.get('extra',{}) for item in posted))
            self.assertIn('usage_metadata',json.dumps([c.kwargs for c in request_http.call_args_list],default=str))

    def test_live_provisioning_redacts_injected_credentials_too(self):
        with patch('launchlens.live_package.configured',return_value=self.tracer) as config:
            run=self.live()
        self.assertIs(run.session._tracer,self.tracer)
        config.assert_called_once_with(secrets=tuple(KEYS.values()))

    def drain(self,tracer):
        deadline=time.monotonic()+2
        while tracer.queue.unfinished_tasks and time.monotonic()<deadline:time.sleep(.005)
        self.assertEqual(tracer.queue.unfinished_tasks,0)
        self.assertTrue(tracer.worker.is_alive())

    def test_new_run_creates_root_without_any_lookup(self):
        from unittest.mock import Mock
        self.client.read_run=Mock(side_effect=TimeoutError('lookup should not run'))
        run=self.live();state=run.execute(run.snapshot()['run_id']);rows=self.delivered()
        self.assertEqual(state['status'],'awaiting_human_review')
        self.client.read_run.assert_not_called()
        self.assertEqual(len([r for r in rows if not r.get('parent_run_id')]),1)
        self.assertEqual(rows[0]['trace_id'],rows[0]['id'])

    def test_failed_client_factory_does_not_disable_next_export(self):
        client=FakeClient();attempts=[]
        def factory(_):
            attempts.append(1)
            if len(attempts)==1:raise RuntimeError('SYNTHETIC-LANGSMITH-SECRET person@example.com')
            return client
        tracer=obs.Tracer('SYNTHETIC-LANGSMITH-SECRET','test',client_factory=factory)
        with self.assertLogs('launchlens.observability',level='WARNING') as logs:
            tracer.root({'run_id':'failed-create','request':request()})
            tracer.root({'run_id':'next-export','request':request()});self.drain(tracer)
        self.assertEqual(len(attempts),2);self.assertEqual(len(client.created),1)
        self.assertEqual(tracer.failed_operations,1)
        self.assertNotIn('SYNTHETIC-LANGSMITH-SECRET',' '.join(logs.output))
        self.assertIn('operation=client',' '.join(logs.output))

    def test_failed_create_and_update_leave_later_records_enabled_and_logs_sanitized(self):
        for method in ['create_run','update_run']:
            with self.subTest(method=method):
                client=FakeClient();original=getattr(client,method);attempts=[]
                def once(**values):
                    attempts.append(1)
                    if len(attempts)==1:raise RuntimeError('TEST-NEBIUS-CREDENTIAL person@example.com request-body')
                    return original(**values)
                setattr(client,method,once)
                tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:client)
                with self.assertLogs('launchlens.observability',level='WARNING') as logs:
                    for identity in ['first','next']:
                        state={'run_id':identity,'request':request()};tracer.root(state);tracer.update(state)
                    self.drain(tracer)
                self.assertEqual(tracer.failed_operations,1);self.assertGreaterEqual(len(attempts),2)
                self.assertTrue(any('next' in r['name'] for r in client.created))
                self.assertTrue(client.updated)
                self.assertIn('operation='+method.removesuffix('_run'),' '.join(logs.output))
                for value in ['TEST-NEBIUS-CREDENTIAL','person@example.com','request-body','Traceback']:
                    self.assertNotIn(value,' '.join(logs.output))

    def test_network_timeout_is_background_only_and_no_sdk_retries(self):
        with patch('langsmith.Client') as sdk:
            obs._client('SYNTHETIC-KEY')
        self.assertEqual(sdk.call_args.kwargs['timeout_ms'],(2000,5000))
        self.assertEqual(sdk.call_args.kwargs['retry_config'].total,0)
        self.assertFalse(sdk.call_args.kwargs['auto_batch_tracing'])


if __name__=='__main__':unittest.main()
