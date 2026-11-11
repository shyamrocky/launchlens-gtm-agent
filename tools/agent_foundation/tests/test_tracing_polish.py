"""Root lifetime/metadata and scan grouping; no service calls or real runs."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import socket,sys,tempfile,time,unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
from launchlens import observability as obs
from launchlens.live_package import LivePackageRun,preflight
from launchlens.offline_fixtures import request,ReviewFixtureTools,action,package_cases
from launchlens.package_content import risky_phrase_scan,FORMATS
from launchlens.writer_comparison import ProtectedStore
from test_live_package import Wire,permission,KEYS,NOW,FrozenDateTime,project
from test_observability import FakeClient

class Ingestion(FakeClient):
    def __init__(self):super().__init__();self.remote={};self.requests=[]
    def create_run(self,**row):
        super().create_run(**row);self.remote.setdefault(row['id'],deepcopy(row))
    def update_run(self,**row):
        super().update_run(**row);self.remote[row['run_id']].update(deepcopy(row))
    def request_with_retries(self,*args,**kwargs):
        self.requests.append((args,deepcopy(kwargs)))
        return super().request_with_retries(*args,**kwargs)

class Clock(datetime):
    offset=0
    @classmethod
    def now(cls,tz=None):return cls(2026,11,10,tzinfo=timezone.utc)+timedelta(seconds=cls.offset)

class TracingPolishTests(unittest.TestCase):
    def setUp(self):
        self.net=self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('No network')))
        self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
        self.enterContext(patch('launchlens.live_package.datetime',FrozenDateTime))
        self.enterContext(patch('launchlens.live_package.project_writer_input',side_effect=project))
        self.client=Ingestion();self.tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:self.client)
        self.enterContext(patch('launchlens.live_package.configured',return_value=self.tracer))
    def drain(self,tracer=None):
        tracer=tracer or self.tracer;limit=time.monotonic()+2
        while tracer.queue.unfinished_tasks and time.monotonic()<limit:time.sleep(.005)
        self.assertEqual(tracer.queue.unfinished_tasks,0);self.assertEqual(tracer.failed_operations,0)
    def live(self,market='US'):
        grant=permission();wire=Wire()
        if market!='US':grant['request']=request(market);grant['scope_sha256']=preflight(request=request(market))['scope_sha256']
        if market=='UK':wire.actions=[action('read_pmm_brief','pmm'),action('check_launch','launch'),action('request_clarification','ask',market_id='UK',question='Choose scope'),action('generate_package','write')]
        run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
        return run,run.execute(run.snapshot()['run_id'])

    def test_root_clock_covers_pause_resume_and_process_restore_with_original_start(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(obs,'datetime',Clock):
            Clock.offset=0;store=ProtectedStore(Path(folder)/'run');state={'run_id':'root-clock','request':request()}
            self.tracer.bind_context(state,store)
            with self.tracer.run(state):Clock.offset=5
            self.drain();root=next(r for r in self.client.created if not r.get('parent_run_id'));saved=(store.path/'langsmith-trace-context.json').read_bytes()
            self.assertEqual((self.client.remote[root['id']]['end_time']-root['start_time']).total_seconds(),5)
            Clock.offset=300
            with self.tracer.run({**state,'status':'running','turns':3}):Clock.offset=320
            self.drain();self.assertEqual((self.client.remote[root['id']]['end_time']-root['start_time']).total_seconds(),320)
            other=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:self.client)
            other.bind_context(state,store);Clock.offset=600
            with other.run({**state,'status':'running','turns':5}):Clock.offset=650
            self.drain(other);remote=self.client.remote[root['id']]
            self.assertEqual(remote['start_time'],root['start_time']);self.assertEqual((remote['end_time']-remote['start_time']).total_seconds(),650)
            last_end=remote['end_time'];Clock.offset=640;other.update(state);self.drain(other)
            self.assertEqual(self.client.remote[root['id']]['end_time'],last_end)
            self.assertEqual((store.path/'langsmith-trace-context.json').read_bytes(),saved)

    def test_actual_clarification_sets_root_gate_and_resume_does_not_clear_it(self):
        run,state=self.live('UK');self.assertEqual(state['status'],'needs_clarification');self.drain()
        root=next(r for r in self.client.created if not r.get('parent_run_id'));first=self.client.remote[root['id']]['end_time']
        self.assertEqual(self.client.remote[root['id']]['extra']['metadata']['gate_decision'],'Clarify')
        final=run.resume(state['run_id'],'draft_without_availability');self.assertEqual(final['status'],'awaiting_human_review');self.drain()
        self.tracer.update({'run_id':state['run_id'],'request':state['request'],'launch':None},models={});self.drain()
        remote=self.client.remote[root['id']]
        self.assertEqual(remote['extra']['metadata']['gate_decision'],'Clarify');self.assertIn('gate_decision=Clarify',remote['tags'])
        self.assertTrue(remote['extra']['metadata']['models']);self.assertGreaterEqual(remote['end_time'],first)
        self.assertEqual({r['trace_id'] for r in self.client.created},{root['id']})

    def test_gate_result_sets_root_before_a_pause_without_final_state_update(self):
        @obs.step('launch gate check')
        def check_gate():return {'decision':'Clarify'}
        with self.tracer.run({'run_id':'pause-gate','request':request('UK')}):
            check_gate()
        self.drain();root=next(r for r in self.client.created if not r.get('parent_run_id'))
        self.assertEqual(self.client.remote[root['id']]['extra']['metadata']['gate_decision'],'Clarify')

    def test_hold_still_has_root_gate_and_does_not_create_scan_group(self):
        _,state=self.live('IN');self.assertEqual(state['status'],'held');self.drain()
        root=next(r for r in self.client.created if not r.get('parent_run_id'))
        self.assertEqual(self.client.remote[root['id']]['extra']['metadata']['gate_decision'],'Hold')
        self.assertFalse(any(r['name']=='risky-phrase scan' for r in self.client.created))

    def test_engine_and_ui_share_exporter_and_union_redaction_secrets(self):
        factory=lambda _:self.client
        with tempfile.TemporaryDirectory() as folder,patch.dict('os.environ',{},clear=True):
            path=Path(folder)/'.env';path.write_text('LANGSMITH_TRACING=true\nLANGSMITH_API_KEY=SYNTHETIC-POLISH-KEY\nLANGSMITH_PROJECT=polish\n')
            one=obs.configured(path=path,secrets=('SYNTHETIC-NEBIUS','SYNTHETIC-NOTION'),client_factory=factory)
            two=obs.configured(path=path,secrets=(),client_factory=factory)
            three=obs.configured(path=path,secrets=('SYNTHETIC-PINECONE',),client_factory=factory)
            self.assertIs(one,two);self.assertIs(one,three)
            self.assertTrue({'SYNTHETIC-POLISH-KEY','SYNTHETIC-NEBIUS','SYNTHETIC-NOTION','SYNTHETIC-PINECONE'}<=set(one.secrets))

    def test_multiple_format_scans_are_grouped_once_and_results_match_untraced(self):
        package=deepcopy(package_cases()['initial_package']);before=deepcopy(package)
        expected=[];actual=[]
        cases=[(package,False,True),({'email':package['email'],'blog':package['blog']},True,'tone_v2'),(package,False,False)]
        for value,suggestion,scan in cases:expected.append(risky_phrase_scan(value,suggestion=suggestion,scan_additions=scan))
        with self.tracer.run({'run_id':'scans','request':request()}):
            for value,suggestion,scan in cases:actual.append(risky_phrase_scan(value,suggestion=suggestion,scan_additions=scan))
        self.drain();self.assertEqual(actual,expected);self.assertEqual(package,before)
        groups=[r for r in self.client.created if r['name']=='risky-phrase scan'];self.assertEqual(len(groups),1);group=groups[0]
        children=[r for r in self.client.created if r.get('parent_run_id')==group['id']]
        self.assertEqual({r['inputs']['format'] for r in children},set(FORMATS))
        self.assertEqual(len(children),12);self.assertEqual(group['outputs']['scan_count'],3)
        self.assertEqual(group['outputs']['format_scan_count'],12)
        self.assertEqual(group['outputs']['hit_count'],sum(map(len,actual)))
        self.assertEqual(sum(c['outputs']['hit_count'] for c in children),group['outputs']['hit_count'])
        self.assertTrue(all(c['end_time']<=group['end_time'] for c in children))

    def test_actual_harness_collects_scan_calls_under_one_segment_parent(self):
        _,state=self.live();self.assertEqual(state['status'],'awaiting_human_review');self.drain()
        groups=[r for r in self.client.created if r['name']=='risky-phrase scan'];self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['parent_run_id'],groups[0]['trace_id'])
        self.assertGreater(groups[0]['outputs']['format_scan_count'],5)
        scans=[r for r in self.client.created if r['name'].startswith('scan ')]
        self.assertTrue(scans);self.assertTrue(all(r['parent_run_id']==groups[0]['id'] for r in scans))

    def test_installed_sdk_root_updates_use_minimal_ingestion_with_one_attempt(self):
        from langsmith import Client
        sdk=Client(api_key='SYNTHETIC-KEY',api_url='https://api.smith.langchain.com',auto_batch_tracing=False,omit_traced_runtime_info=True)
        requests=[]
        def http(method,path,**kwargs):
            self.assertEqual(method,'POST');body=json.loads(kwargs['request_kwargs']['data']);requests.append((path,body))
            if path=='/runs/batch':
                self.assertEqual(kwargs['stop_after_attempt'],1);self.assertEqual(set(body),{'patch'})
                for row in body['patch']:
                    self.assertEqual(row['id'],row['trace_id']);self.assertTrue(row['end_time']);self.assertTrue(row['start_time'])
                    self.assertNotIn('address',row);self.assertNotIn('parent_run_id',row)
                    self.assertTrue(all(v is not None for v in row.values()))
            return Mock(status_code=202)
        with patch.object(Client,'request_with_retries',side_effect=http),patch.object(Client,'read_run',side_effect=AssertionError('No lookup')):
            tracer=obs.Tracer('SYNTHETIC-KEY','test',client_factory=lambda _:sdk)
            with tracer.run({'run_id':'ingestion','request':request(),'launch':{'decision':'Clarify'}}):pass
            self.drain(tracer)
        self.assertTrue(any(path=='/runs/batch' for path,_ in requests))

if __name__=='__main__':unittest.main()
