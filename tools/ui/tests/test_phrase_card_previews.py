"""Phrase previews and cents formatting are display-only; no live providers."""
from copy import deepcopy
from pathlib import Path
import os,socket,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.agent_run_ui import rounded_budget_display
from launchlens.review_decisions import grouped_findings,safe_hints,replacement_preview
from ui_review_helpers import show_card
class PhrasePreviewUITests(unittest.TestCase):
 def test_budget_format_is_a_copy_and_keeps_exact_ledger_input(self):
  original={'remaining_usd':'0.7290314','events':[{'estimated_cost_usd':'0.0018627'}]};before=deepcopy(original)
  value=rounded_budget_display(original);self.assertEqual(value,{'remaining_usd':'0.73','events':[{'estimated_cost_usd':'0.00'}]});self.assertEqual(original,before)
 def test_card_previews_full_sentence_and_displays_no_paid_activity(self):
  with patch.object(socket.socket,'connect',side_effect=AssertionError('Offline only')) as network,patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'offline'}):
   a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20).run();a.button(key='open-US').click().run();a.button(key='prepare-start').click().run()
   r=a.session_state['offline_run'];s=r.snapshot();calls=deepcopy(r.capture());g=next(g for g in grouped_findings(s) if g['needs_attention'] and safe_hints(g));show_card(a,g)
   html=' '.join(x.proto.body for x in a.get('html'));self.assertIn('Sentence after the change',html)
   from html import escape
   self.assertIn(escape(replacement_preview(g['occurrences'][0],safe_hints(g)[0])),html)
   self.assertFalse(a.exception);self.assertEqual(r.snapshot(),s);self.assertEqual(r.capture(),calls);self.assertEqual(network.call_count,0)
