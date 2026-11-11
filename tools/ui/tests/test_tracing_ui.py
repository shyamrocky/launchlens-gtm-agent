"""Actual suggestion/submit/approval/deferred-download controls with fake tracing."""
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests'),str(ROOT/'tools/ui/tests')]
import test_live_package_ui as existing
from test_observability import FakeClient
from launchlens import observability as obs
from launchlens.review_decisions import grouped_findings,safe_hints
from ui_review_helpers import show_card,finish_pending


class TracingUITests(unittest.TestCase):
    start_live=existing.LivePackageUITests.start_live
    def setUp(self):
        existing.LivePackageUITests.setUp(self)
        self.client=FakeClient()
        self.tracer=obs.Tracer('SYNTHETIC-KEY','ui-test',client_factory=lambda _:self.client)
        self.enterContext(patch('launchlens.agent_foundation.configured',return_value=self.tracer))
        self.enterContext(patch.object(obs,'configured',return_value=self.tracer))

    def test_actual_suggestion_submit_approval_and_download_keep_same_trace(self):
        from streamlit.runtime.media_file_manager import MediaFileManager
        from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
        manager=MediaFileManager(MemoryMediaFileStorage('/mock/media'))
        # AppTest discards its Runtime after each render; retain the actual download
        # manager so the same deferred request handler can be exercised afterward.
        self.enterContext(patch('streamlit.testing.v1.app_test.MediaFileManager',return_value=manager))
        app,run,wire=self.start_live();before=run.snapshot();calls=len(wire.calls)
        group=next(g for g in grouped_findings(before) if g['needs_attention'] and safe_hints(g))
        show_card(app,group);app.button(key='use-'+group['id']).click().run()
        self.assertFalse(app.exception);self.assertEqual(run.snapshot(),before);self.assertEqual(len(wire.calls),calls)
        finish_pending(app);app.button(key='create-next-version').click().run()
        self.assertFalse(app.exception);state=run.snapshot();self.assertEqual(state['package']['version'],2)
        self.assertEqual(len(run.reviser.calls),0);self.assertEqual(len(run.reviewer.calls),2)
        app.session_state['run-tabs-'+state['run_id']]='Package';app.run()
        next(c for c in app.checkbox if (c.key or '').startswith('run-approval-as-is-')).check().run()
        app.button(key='approve-package').click().run();self.assertFalse(app.exception)
        self.assertTrue(list(run.store.path.glob('human-internal-approval-*.json')))
        proto=next(d.proto for d in app.get('download_button') if d.proto.label=='Download Markdown')
        self.assertTrue(proto.ignore_rerun);self.assertTrue(proto.deferred_file_id)
        self.assertFalse(any(r['name']=='download' for r in self.client.created))
        self.assertTrue(manager.execute_deferred(proto.deferred_file_id).startswith('/mock/media/'))
        deadline=time.monotonic()+2
        while self.tracer.queue.unfinished_tasks and time.monotonic()<deadline:time.sleep(.005)
        self.assertEqual(self.tracer.failed_operations,0)
        rows=self.client.created;self.assertEqual(len([r for r in rows if not r.get('parent_run_id')]),1)
        self.assertTrue({'human review decision','human_resume','exact-replacement apply','approval','download'} <= {r['name'] for r in rows})
        self.assertEqual({r['trace_id'] for r in rows},{rows[0]['id']})
        self.assertEqual(run.snapshot(),state)

if __name__=='__main__':unittest.main()
