"""Four-state run screen and same-session commands, socket-blocked AppTest."""
from pathlib import Path
import os,sys,socket,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.offline_ui_run import OfflineUIRun
from launchlens.offline_fixtures import request
from launchlens.voice_policy import BRAND_POLICY_ID

from ui_review_helpers import finish_stack,show_card

class RunScreenTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
        self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
        p=patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'});p.start();self.addCleanup(p.stop)
    def start(self,market='US',scenario='Standard review'):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        app.button(key='open-'+market).click().run()
        app.selectbox(key='prepare-scenario').select(scenario).run()
        app.button(key='prepare-start').click().run();self.assertFalse(app.exception)
        return app,app.session_state['offline_run']
    def test_ready_layout_hides_engineering_and_output_until_review_click(self):
        app,run=self.start();html=' '.join(x.proto.body for x in app.get('html'))
        self.assertIn('Package ready for your review',html);self.assertIn('What the agent did',[s.value for s in app.subheader])
        self.assertNotIn('Skipped public research',html);self.assertNotIn('Source documents',html)
        self.assertEqual([t.label for t in app.tabs if t.label in {'Activity','Review','Package'}],['Activity','Review','Package']);self.assertTrue(any(e.label=='Technical details' and not e.proto.expanded for e in app.expander))
        self.assertTrue(all(e['why'] for e in run.snapshot()['events']))
        app.button(key='run-review').click().run();self.assertEqual(len(app.tabs),3)
        self.assertFalse(app.exception)
    def test_waiting_inline_continue_same_run_without_approval(self):
        app,run=self.start('UK');before=run.snapshot()
        self.assertEqual(before['status'],'needs_clarification');self.assertIn('Waiting on you',' '.join(x.proto.body for x in app.get('html')))
        app.radio(key='run-choice').set_value('Draft without availability wording')
        next(b for b in app.button if b.label=='Continue').click().run()
        self.assertFalse(app.exception);after=run.snapshot();self.assertEqual(after['run_id'],before['run_id'])
        self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['launch']['decision'],'Clarify')
        self.assertFalse(after['launch']['promotional_draft_allowed']);self.assertEqual(len(after['drafts']),5)
    def test_recheck_frozen_missing_displays_exact_continuation(self):
        app,run=self.start('UK');app.radio(key='run-choice').set_value('Recheck readiness')
        next(b for b in app.button if b.label=='Continue').click().run();self.assertFalse(app.exception)
        self.assertIn('Readiness still shows availability unconfirmed. Continuing without availability wording.',[x.value for x in app.info])
    def test_stopped_retry_preserves_research_and_is_not_automatic(self):
        app,run=self.start(scenario='Bad Writer response');before=run.snapshot();calls=len(run.writer.calls)
        self.assertEqual(before['status'],'draft_incomplete');app.run();self.assertEqual(len(run.writer.calls),calls)
        self.assertIn('Draft needs attention',' '.join(x.proto.body for x in app.get('html')))
        app.button(key='run-retry').click().run();self.assertFalse(app.exception);after=run.snapshot()
        self.assertEqual(after['status'],'awaiting_human_review');self.assertEqual(after['turns'],7)
        self.assertEqual(after['evidence'],before['evidence']);self.assertEqual(after['run_id'],before['run_id'])
        self.assertEqual(after['retry_attempts'],1);self.assertFalse(any(b.label=='Try again' for b in app.button))
    def test_rejected_retry_has_no_second_retry(self):
        app,run=self.start(scenario='Bad Writer twice');app.button(key='run-retry').click().run()
        self.assertFalse(app.exception);self.assertEqual(run.snapshot()['status'],'draft_incomplete')
        self.assertFalse(any(b.label=='Try again' for b in app.button));self.assertEqual(len(run.writer.calls),2)
    def test_inline_stop_and_back_to_setup(self):
        app,run=self.start('UK');rid=run.snapshot()['run_id'];app.radio(key='run-choice').set_value('Stop this run')
        next(b for b in app.button if b.label=='Continue').click().run();self.assertEqual(run.snapshot()['status'],'stopped')
        app.button(key='run-setup').click().run();self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value,'Prepare UK package');self.assertEqual(run.snapshot()['run_id'],rid)
    def test_running_is_real_created_session_and_stop_calls_no_models(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run()
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
        app.session_state['offline_run']=run;app.session_state['screen']='run';app.run()
        self.assertIn('Agent is working',' '.join(x.proto.body for x in app.get('html')))
        app.button(key='run-stop').click().run();self.assertFalse(app.exception)
        self.assertEqual(run.snapshot()['status'],'stopped');self.assertFalse(run.controller.calls)
    def test_visual_launcher_runs_all_four_actual_graph_states_offline(self):
        for case,status in [('working','running'),('waiting','needs_clarification'),('ready','awaiting_human_review'),('stopped','draft_incomplete')]:
            with self.subTest(case=case):
                app=AppTest.from_file(str(ROOT/'tools/preview_run_states.py'),default_timeout=20)
                app.query_params['case']=case;app.run();self.assertFalse(app.exception)
                run=app.session_state['offline_run'];before=run.snapshot();self.assertEqual(before['status'],status)
                if case=='working':
                    self.assertEqual(before['pending']['name'],'generate_package');self.assertFalse(before['drafts'])
                    app.button(key='run-continue').click().run();self.assertFalse(app.exception)
                    self.assertEqual(run.snapshot()['status'],'awaiting_human_review')
                    self.assertEqual(run.snapshot()['searches'],before['searches'])
                if case=='ready':self.assertEqual(run.snapshot()['review']['review_status'],'human_clearance_required')
if __name__=='__main__':unittest.main()
