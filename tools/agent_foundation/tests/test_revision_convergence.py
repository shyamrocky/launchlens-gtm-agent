"""Minimal synthetic no-op/partial-edit cases; no saved run artifacts are read."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools/agent_foundation/tests')]
from test_package_content import response, script
from test_grouped_reviewer_protocol import judgments
from launchlens.agent_foundation import FoundationSession
from launchlens.content_review import ContentCall
from launchlens.offline_fixtures import (ReviewFixtureTools, ScriptedReviewController,
    package_cases, request)
from launchlens.package_content import (compare_revision_phrases, current_revision_resolution,
    package_value, prepare_package_input, refinement_avoid_list,
    revision_phrase_targets)
from launchlens.package_presentation import must_decide, approve_current_version
from launchlens.review_decisions import (decision_book, grouped_findings, record_decision,
    revision_feedback)
from launchlens.voice_policy import BRAND_POLICY_ID

SYNTHETIC = json.loads((Path(__file__).parent / 'fixtures/revision_convergence.json').read_text())


class ApprovedFixtureTools(ReviewFixtureTools):
    """Fixture permission for each market; never changes real launch evidence."""
    def read_launch(self, task):
        result = super().read_launch(task)
        for row in result['readiness']:
            row['values']['Status'] = 'Approved'
            row['values']['Blocker / Missing Information'] = 'None'
        return result


class RevisionConvergenceTests(unittest.TestCase):
    def setUp(self):
        blocker = patch.object(socket.socket, 'connect', side_effect=AssertionError('No network'))
        self.net = blocker.start()
        self.addCleanup(blocker.stop)
        self.addCleanup(lambda: self.assertEqual(self.net.call_count, 0))

    def session(self, market='US', origin='human'):
        initial = package_cases()['initial_package']
        initial['blog']['content']['sections'][1]['body'] = SYNTHETIC['unchanged']
        initial['blog']['content']['sections'][0]['body'] += ' An appealing choice.'
        writer = ContentCall(lambda p: response(p, initial), stage='package_writer', model_id='OFFLINE')
        revisions = []
        def revise(payload):
            from launchlens.offline_fixtures import fixture_edits
            from launchlens.field_revisions import set_text
            inputs = json.loads(payload['messages'][1]['content']); revisions.append(inputs)
            candidate = deepcopy(initial)
            for field in inputs['targeted_fields'].values():
                set_text(candidate,field['format'],field['content_field'],field['text'])
            candidate['blog']['content']['sections'][1]['body'] = SYNTHETIC['unchanged' if len(revisions)==1 else 'partial']
            return response(payload, fixture_edits(inputs,candidate))
        reviser = ContentCall(revise, stage='package_revision', model_id='OFFLINE')
        reviews = []
        def review(payload):
            inputs = json.loads(payload['messages'][1]['content']); reviews.append(inputs)
            value = judgments(inputs['phrase_groups'])
            if inputs['binding']['draft_version'] == 1:
                value['additional_findings'] = [{'format':'blog','content_field':'sections.0.body',
                    'quote':'appealing choice','dimension':'tone','severity':'blocking',
                    'reason':'Offline fixture wording request.', 'suggestion':'Use descriptive wording.', 'claim_ids':[]}]
            return response(payload, value)
        reviewer = ContentCall(review, stage='package_reviewer', model_id='OFFLINE')
        session = FoundationSession(ScriptedReviewController(script()), ApprovedFixtureTools(),
            mode='offline_package', writer=writer, reviewer=reviewer, revision_writer=reviser,
            voice_policy_id=BRAND_POLICY_ID, automatic_refinement=origin == 'agent')
        state = session.run(session.start(request(market))['run_id'])
        return session, state, revisions, reviews

    def choose(self, state):
        book = decision_book(state)
        for group in grouped_findings(state):
            if group['phrase'] in ('dairy', 'favorite', 'ice cream', 'appealing choice'):
                book = record_decision(state, book, group['id'], 'request_changes')
        return revision_feedback(state, book)

    def test_shared_guidance_and_unresolved_requests_survive_omitted_review_all_markets_origins(self):
        for market in ('US', 'UK'):
            for origin in ('human', 'agent'):
                with self.subTest(market=market, origin=origin):
                    session, state, revisions, reviews = self.session(market, origin)
                    if origin == 'human':
                        session.request_revision(state['run_id'], self.choose(state), draft_version=1,
                            draft_sha256=state['package']['package_sha256'])
                        state = session.run(state['run_id'])
                    self.assertEqual(state['package']['version'], 1)
                    sent = revisions[0]
                    self.assertEqual(sent['full_avoid_list'], refinement_avoid_list(prepare_package_input(state)))
                    self.assertTrue(sent['current_flagged_locations'])
                    self.assertTrue(sent['targeted_fields'])
                    self.assertNotIn('package',sent)
                    self.assertNotIn('review',sent)
                    self.assertTrue(any(f['content_field']=='sections.1.body' and f['text']==SYNTHETIC['unchanged'] for f in sent['targeted_fields'].values()))
                    report = current_revision_resolution(state)
                    self.assertEqual(report['origin'], origin)
                    self.assertTrue(all(r['status'] == 'unresolved' for r in report['requests']))
                    groups = grouped_findings(state)
                    survivor = next(g for g in groups if g['phrase'] == 'appealing choice')
                    self.assertTrue(must_decide(survivor))
                    self.assertTrue(any(f.get('origin') == 'revision_request'
                        for o in survivor['occurrences'] for f in o['findings']))
                    self.assertEqual(len(reviews), 1)
                    self.assertEqual(reviews[-1]['package'], package_value(state))
                    self.assertNotIn('requested_phrase_changes', reviews[-1])
                    self.assertFalse(state['human_accepted'])
                    self.assertEqual(state['revision_attempts'], 0)
                    # A second human revision exercises a synthetic partial-removal shape.
                    session.request_revision(state['run_id'], self.choose(state), draft_version=1,
                        draft_sha256=state['package']['package_sha256'])
                    final = session.run(state['run_id']); rows = current_revision_resolution(final)['requests']
                    ice = [r for r in rows if r['quote'] == 'ice cream']
                    self.assertEqual([r['status'] for r in ice], ['wording_changed', 'unresolved'])
                    for phrase in ('dairy', 'favorite'):
                        self.assertTrue(all(r['status'] == 'unresolved' for r in rows if r['quote'] == phrase))
                    self.assertEqual(final['revision_attempts'], 1)
                    self.assertEqual(len(revisions), 2); self.assertEqual(len(reviews), 2)
                    self.assertFalse(any(f.get('quote')=='appealing choice' for f in final['review']['assessment']['blog']['findings']))
                    self.assertTrue(final['review']['review_complete'])
                    accepted, receipt = approve_current_version(final, decision_book(final), True)
                    self.assertTrue(receipt['internal_approved'])
                    self.assertFalse(final['human_accepted'])

    def test_generated_feedback_preserves_case_paths_overrides_and_repeated_occurrences(self):
        _, state, _, _ = self.session()
        book = decision_book(state)
        group = next(g for g in grouped_findings(state) if g['phrase'] == 'ice cream')
        book = record_decision(state, book, group['id'], 'request_changes')
        book = record_decision(state, book, group['occurrences'][1]['id'], 'keep_wording', occurrence=True)
        state['revision_request'] = {'feedback':revision_feedback(state, book)}
        targets = revision_phrase_targets(state)
        self.assertEqual(len(targets), 1); self.assertEqual(targets[0]['start'], SYNTHETIC['unchanged'].index('ice cream'))
        # Capitalization is irrelevant to phrase identity; offsets must still be exact.
        text = state['drafts']['blog']['draft']['content']['sections'][1]['body']
        state['revision_request']['feedback'] = 'Change “the” at blog.sections.1.body[0:3]'
        self.assertEqual(revision_phrase_targets(state)[0]['quote'], text[:3])
        state['revision_request']['feedback'] = 'Change “dairy” at blog.sections.1.body[0:5]'
        self.assertEqual(revision_phrase_targets(state), [])

    def test_repeated_phrase_alignment_case_changes_and_unrelated_paths(self):
        before = {'ads':{'content':{'concepts':[{'body':'ice cream and ice cream'}]}}}
        targets = [dict(format='ads',content_field='concepts.0.body',quote='ice cream',start=a,end=a+9) for a in (0,14)]
        after = deepcopy(before);after['ads']['content']['concepts'][0]['body'] = 'dessert and ICE CREAM'
        rows = compare_revision_phrases(before, after, targets)
        self.assertEqual([r['status'] for r in rows], ['wording_changed', 'unresolved'])

    def test_phrase_tracking_has_no_market_branch_including_india(self):
        _, state, _, _ = self.session()
        expected = None
        for market in ('US', 'UK', 'IN'):
            state['request'] = request(market)
            state['revision_request'] = {'feedback': self.choose(state)}
            targets = revision_phrase_targets(state)
            after = package_value(state)
            after['blog']['content']['sections'][1]['body'] = SYNTHETIC['partial']
            result = compare_revision_phrases(package_value(state), after, targets)
            if expected is None: expected = result
            self.assertEqual(result, expected)

    def test_reports_are_current_text_bound_and_absent_for_historical_runs(self):
        _, state, _, _ = self.session(origin='agent')
        self.assertTrue(current_revision_resolution(state))
        state['package']['package_sha256'] = 'changed'
        self.assertFalse(current_revision_resolution(state))
        state['ledger'] = {}
        self.assertEqual(current_revision_resolution(state), {})


if __name__ == '__main__':
    unittest.main()
