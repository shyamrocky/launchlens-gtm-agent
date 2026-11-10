"""Source access requires real content reads; HTTP200 alone is insufficient."""
from copy import deepcopy
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"));sys.path.insert(0, str(ROOT / "tests"))
from launchlens.source_access import APPROVED_PDFS, MAX_PDF_BYTES, check_drive_pdf
from launchlens.inventory import fetch_inventory, load_display
from test_inventory import Reader

FILE = next(iter(APPROVED_PDFS))
PDF = b'%PDF-1.7\nSAFE FIXTURE\n%%EOF\n'

class Response(io.BytesIO):
    status = 200

class SourceAccessTests(unittest.TestCase):
    def run_check(self, raw, status=200, error=None):
        response = Response(raw);response.status = status
        with patch('urllib.request.OpenerDirector.open', return_value=response, side_effect=error) as opened:
            result = check_drive_pdf(FILE)
        self.assertEqual(opened.call_count, 1)
        request = opened.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertTrue(request.full_url.startswith('https://drive.usercontent.google.com/download?id=' + FILE))
        self.assertEqual(set(k.lower() for k in request.headers), {'accept'})
        self.assertEqual(opened.call_args.kwargs['timeout'], 20)
        return result

    def test_exact_approved_pdf_bytes_required_no_auth_or_cookies(self):
        with patch.dict(APPROVED_PDFS, {FILE: hashlib.sha256(PDF).hexdigest()}):
            result = self.run_check(PDF)
        self.assertEqual(result['status'], 'accessible')
        self.assertEqual(result['sha256'], hashlib.sha256(PDF).hexdigest())
        self.assertEqual(result['bytes'], len(PDF))
        self.assertTrue(result['checked_at'])
        self.assertNotIn('SAFE FIXTURE', str(result))

    def test_http200_html_changed_pdf_and_oversize_are_not_accessible(self):
        for raw, reason in [(b'<html>Sign in</html>', 'not_pdf'),
                (b'x'*(MAX_PDF_BYTES+1), 'size_limit')]:
            with self.subTest(reason=reason):
                result = self.run_check(raw)
                self.assertEqual(result['status'], 'unavailable')
                self.assertEqual(result['detail'], reason)
                self.assertNotIn('Sign in', str(result))

    def test_changed_pdf_reports_observed_and_indexed_hash_without_accepting_or_retaining_bytes(self):
        from launchlens.retrieval import SOURCES
        from launchlens.source_access import DRIVE_AUTHORITIES
        for file_id, authority in DRIVE_AUTHORITIES.items():
            self.assertEqual(APPROVED_PDFS[file_id], SOURCES[authority][2])
        result = self.run_check(PDF)
        self.assertEqual(result['status'], 'changed')
        self.assertEqual(result['detail'], 'content_mismatch')
        self.assertEqual(result['sha256'], hashlib.sha256(PDF).hexdigest())
        self.assertEqual(result['indexed_sha256'], APPROVED_PDFS[FILE])
        self.assertNotIn('SAFE FIXTURE', str(result))

    def test_denied_or_transport_failure_does_not_retry_or_echo_error(self):
        secret = 'private-token-and-source-body'
        for error in [urllib.error.HTTPError('https://example.invalid',403,secret,{},None), OSError(secret)]:
            result = self.run_check(b'', error=error)
            self.assertEqual(result['status'], 'unavailable')
            self.assertNotIn(secret, str(result))

    def test_unapproved_file_never_requests_and_redirects_are_disabled(self):
        with patch('urllib.request.OpenerDirector.open') as opened:
            self.assertEqual(check_drive_pdf('unapproved')['status'], 'unavailable')
            opened.assert_not_called()
        from launchlens.notion_tools import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 303, '', {}, 'https://unapproved.invalid'))

    def test_complete_checks_and_independent_failures(self):
        class Complete(Reader):
            def get_pmm_brief(self): return {'status':'ok','blocks':[{'safe':'fixture'}]}
        display = load_display()
        good = {'status':'accessible','checked_at':'2026-11-08T23:30:00+00:00','detail':'fixture'}
        with patch('launchlens.inventory.check_drive_pdf', return_value=good) as drive:
            snapshot = fetch_inventory(display, Complete(), verify_documents=True)
            self.assertEqual(drive.call_count, 2)
        self.assertTrue(all(v['status']=='accessible' for v in snapshot['source_access'].values()))
        class MissingPMM(Complete):
            def get_pmm_brief(self): return {'status':'error','blocks':[]}
        bad = {**good, 'status':'unavailable'}
        with patch('launchlens.inventory.check_drive_pdf', side_effect=[bad, good]):
            next_snapshot = fetch_inventory(display, MissingPMM(), verify_documents=True)
        self.assertEqual(next_snapshot['source_access']['Product Brief']['status'], 'unavailable')
        self.assertEqual(next_snapshot['source_access']['Synthetic PRD']['status'], 'accessible')
        self.assertEqual(next_snapshot['source_access']['PMM / GTM Brief']['status'], 'unavailable')
        self.assertEqual(next_snapshot['markets'], snapshot['markets'])
        self.assertEqual(snapshot['source_access']['Product Brief']['status'], 'accessible')

    def test_incomplete_notion_read_never_reuses_previous_success_and_no_check_default(self):
        class Failed(Reader):
            def get_launch_context(self, market): return {'status':'error'}
        with patch('launchlens.inventory.check_drive_pdf', side_effect=AssertionError('No hidden PDF check')):
            snapshot = fetch_inventory(load_display(), Failed())
        checks = snapshot['source_access']
        for name in ('Launch Calendar', 'Readiness Tracker'):
            self.assertEqual(checks[name]['status'], 'unavailable')
        for name in ('Product Brief', 'Synthetic PRD', 'PMM / GTM Brief'):
            self.assertEqual(checks[name]['status'], 'not_checked')
            self.assertIsNone(checks[name]['checked_at'])

if __name__ == '__main__': unittest.main()
