"""Home-only evidence metadata and planned-rebuild routing; no external calls."""
from copy import deepcopy
import json, os, socket, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from streamlit.testing.v1 import AppTest
from launchlens.inventory import load_display
from launchlens.offline_ui_run import fixture_inventory
from launchlens.inventory_ui import indexed_date, product_evidence_status
from launchlens.source_access import APPROVED_PDFS
from launchlens.retrieval import INDEX, NAMESPACE, MODEL

class EvidenceStatusTests(unittest.TestCase):
 def setUp(self):
  self.display=load_display();self.snapshot=fixture_inventory(self.display);self.snapshot.pop('data_mode')
  for doc in self.display['documents']:
   if doc['app']=='Google Drive':
    digest=APPROVED_PDFS[doc['file_id']]
    self.snapshot['source_access'][doc['name']]={'status':'accessible','sha256':digest,'indexed_sha256':digest}
  self.receipt={'status':'PASS','index':INDEX,'namespace':NAMESPACE,'model':MODEL,'upserted_count':45,
   'started_utc':'2026-11-01T01:00:00+00:00','finished_utc':'2026-11-06T06:04:00.563850+00:00'}
  p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'));self.net=p.start();self.addCleanup(p.stop)
  self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))
 def test_date_comes_from_finished_receipt_in_pacific_time(self):
  with patch.object(Path,'read_bytes',return_value=json.dumps(self.receipt).encode()):
   self.assertEqual(indexed_date(),'Nov 5, 2026')
 def test_missing_invalid_or_wrong_corpus_metadata_has_no_invented_date(self):
  for change in [{'status':'IN_PROGRESS'},{'namespace':'other'},{'upserted_count':3},
                 {'finished_utc':'bad'},{'finished_utc':'2026-11-06T06:04:00'}]:
   with self.subTest(change=change),patch.object(Path,'read_bytes',return_value=json.dumps({**self.receipt,**change}).encode()):
    self.assertIsNone(indexed_date())
  with patch.object(Path,'read_bytes',side_effect=FileNotFoundError):self.assertIsNone(indexed_date())
 def test_fresh_matches_only_and_changed_checksum_is_amber(self):
  with patch('launchlens.inventory_ui.indexed_date',return_value='Nov 5, 2026'):
   self.assertEqual(product_evidence_status(self.display,self.snapshot),('Product evidence · indexed Nov 5, 2026 · ✓ Up to date','good'))
   for name in ['Product Brief','Synthetic PRD']:
    snap=deepcopy(self.snapshot);snap['source_access'][name]['sha256']='a'*64
    self.assertEqual(product_evidence_status(self.display,snap),('Product brief changed · evidence not re-indexed','warn'))
 def test_unchecked_unavailable_fixture_or_missing_date_never_claims_up_to_date(self):
  with patch('launchlens.inventory_ui.indexed_date',return_value='Nov 5, 2026'):
   for change in [{'source_access':{}},{'data_mode':'offline'}]:
    self.assertNotIn('Up to date',product_evidence_status(self.display,{**self.snapshot,**change})[0])
   snap=deepcopy(self.snapshot);snap['source_access']['Product Brief']['status']='unavailable'
   self.assertNotIn('Up to date',product_evidence_status(self.display,snap)[0])
  with patch('launchlens.inventory_ui.indexed_date',return_value=None):
   self.assertEqual(product_evidence_status(self.display,self.snapshot),('Product evidence · index date unavailable · Not verified','unknown'))
 def test_home_line_link_and_original_explanation_without_refetch_or_state_change(self):
  with patch('launchlens.live_package.current_resume_available',return_value=False),patch.dict(os.environ,{'LAUNCHLENS_UI_MODE':'live'}),patch('launchlens.inventory_ui.indexed_date',return_value='Nov 5, 2026'),patch('launchlens.inventory_ui.ui_saved_runs',return_value=[]),patch('launchlens.inventory_ui.fetch_inventory',side_effect=AssertionError('Navigation must not fetch')):
   a=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=20)
   a.session_state['inventory']=deepcopy(self.snapshot);a=a.run();self.assertFalse(a.exception)
   html=' '.join(x.proto.body for x in a.get('html'))
   self.assertIn('Product evidence · indexed Nov 5, 2026 · ✓ Up to date',html)
   self.assertEqual([b.label for b in a.button[:2]],['GTM launches','Current run'])
   self.assertEqual(a.button(key='source-rebuild').label,'Rebuild evidence (planned) ›')
   before=deepcopy(a.session_state['inventory']);a.button(key='source-rebuild').click().run();self.assertFalse(a.exception)
   self.assertEqual(a.title[0].value,'Rebuild evidence');self.assertTrue(a.button(key='rebuild-evidence-placeholder').disabled)
   content=' '.join(x.value for x in a.markdown)
   for text in ['Approve changed content','Build and verify first','Export before replacing runs']:self.assertIn(text,content)
   a.button(key='home').click().run();self.assertFalse(a.exception)
   self.assertEqual(a.session_state['inventory'],before);self.assertNotIn('offline_run',a.session_state)
 def test_header_fix_is_scoped_to_scroll_region_not_interactive_focus(self):
  css=(ROOT/'src/launchlens/inventory_ui.css').read_text()
  self.assertIn('[data-testid="stMain"]:focus-visible { outline: none; }',css)
  self.assertIn('.source-item a:focus-visible',css)

if __name__=='__main__':unittest.main()
