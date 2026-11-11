"""Field scope, exact suggestions, no-op accounting and immutable source binding."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/agent_foundation/tests')]
import test_revision_convergence as scenarios
from test_live_package import Wire,permission,KEYS,NOW,project,FrozenDateTime
from launchlens.live_package import LivePackageRun,RunBudget,StandingBudget
from launchlens.field_revisions import merge,exact_package,PROTOCOL
from launchlens.offline_fixtures import ReviewFixtureTools,fixture_edits,package_cases
from launchlens.package_content import (prepare_call,package_value,authoritative_package_binding,
    current_revision_resolution,text_fields)
from launchlens.review_decisions import (grouped_findings,decision_book,record_decision,
    revision_feedback,safe_hints)
from launchlens.writer_comparison import WireResponse


class FieldRevisionTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(socket.socket,'connect',side_effect=AssertionError('No network'))
        self.net=p.start();self.addCleanup(p.stop)
        self.addCleanup(lambda:self.assertEqual(self.net.call_count,0))

    def source(self,market='US'):
        return scenarios.RevisionConvergenceTests().session(market)

    def feedback(self,state,choices,notes=''):
        book=decision_book(state)
        for phrase,choice,hint in choices:
            group=next(g for g in grouped_findings(state) if g['phrase']==phrase)
            suggestion=safe_hints(group)[0] if hint else None
            book=record_decision(state,book,group['id'],choice,suggestion=suggestion)
        return revision_feedback(state,book,notes)

    def test_exact_suggestion_uses_zero_writer_calls_and_fresh_review_all_supported_markets(self):
        for market in ('US','UK'):
            session,state,revisions,reviews=self.source(market);before=package_value(state)
            feedback=self.feedback(state,[('favorite','request_changes',True)])
            session.request_revision(state['run_id'],feedback,draft_version=1,draft_sha256=state['package']['package_sha256'])
            with patch.object(session,'_revision_writer',side_effect=AssertionError('Suggestion must not call Writer')):
                after=session.run(state['run_id'])
            self.assertEqual(after['package']['version'],2);self.assertEqual(after['revision_attempts'],1)
            self.assertEqual(len(revisions),0);self.assertEqual(len(reviews),2)
            self.assertEqual(after['turns'],state['turns']+1)
            self.assertNotIn('favorite',after['drafts']['blog']['draft']['content']['sections'][1]['body'])
            for name in before:
                for path,text in text_fields(before[name]['content']):
                    if (name,path)!=('blog','sections.1.body'):
                        self.assertEqual(dict(text_fields(after['drafts'][name]['draft']['content']))[path],text)
            authoritative_package_binding(after)
            self.assertEqual(after['package']['revision_execution']['method'],'exact_replacement')
            self.assertIsNone(after['drafts']['blog']['writer_prompt_sha256'])

    def test_notes_cannot_expand_scope_and_mixed_writer_cannot_undo_suggestion_or_keep(self):
        session,state,_,_=self.source()
        feedback=self.feedback(state,[('favorite','request_changes',True),('ice cream','request_changes',False),
            ('dairy','keep_wording',False)],'Also change every email field and the campaign brief.')
        body=state['drafts']['blog']['draft']['content']['sections'][1]['body']
        offset=body.index('tradition')
        feedback+='\nChange “tradition” at blog.sections.1.body['+str(offset)+':'+str(offset+9)+']'
        session.request_revision(state['run_id'],feedback,draft_version=1,draft_sha256=state['package']['package_sha256'])
        pending=session.snapshot();inputs=prepare_call(pending,'package_revision')
        for field in inputs['targeted_fields'].values():
            for target in field['requests']+field['kept_occurrences']:
                self.assertEqual(field['text'][target['start']:target['end']],target['quote'])
        import jsonschema
        jsonschema.Draft202012Validator.check_schema(inputs['output_schema'])
        self.assertNotIn('package',inputs);self.assertNotIn('review',inputs)
        self.assertNotIn('output_schema',inputs['writer_brief'])
        self.assertEqual({(f['format'],f['content_field']) for f in inputs['targeted_fields'].values()},{('blog','sections.1.body')})
        self.assertIn('every email field',inputs['owner_notes_data_only'])
        base=exact_package(pending);valid=fixture_edits(inputs,base)
        identity=next(iter(valid['edits']))
        valid['edits'][identity]['text']=valid['edits'][identity]['text'].replace('ice cream','soda-float inspiration')
        result=merge(pending,inputs,valid)
        self.assertIn('non-dairy',result['blog']['content']['sections'][1]['body'])
        self.assertIn('soda-float idea',result['blog']['content']['sections'][1]['body'])
        for mutation in ('extra','missing','hash','source','keep','suggestion','citation'):
            bad=deepcopy(valid)
            if mutation=='extra':bad['edits']['outside']=deepcopy(bad['edits'][identity])
            elif mutation=='missing':bad['edits']={}
            elif mutation=='hash':bad['edits'][identity]['source_sha256']='0'*64
            elif mutation=='source':bad['source_package_sha256']='0'*64
            elif mutation=='keep':bad['edits'][identity]['text']=bad['edits'][identity]['text'].replace('dairy','other')
            elif mutation=='suggestion':bad['edits'][identity]['text']=bad['edits'][identity]['text'].replace('soda-float idea','favorite')
            else:bad['edits'][identity]['claim_ids']=['PROD-004']
            with self.subTest(mutation=mutation),self.assertRaises(Exception):merge(pending,inputs,bad)
        self.assertEqual(session.snapshot(),pending)

    def test_note_only_all_kept_never_authorizes_new_fields(self):
        session,state,_,_=self.source();book=decision_book(state)
        for group in grouped_findings(state):book=record_decision(state,book,group['id'],'keep_wording')
        feedback=revision_feedback(state,book,'Rewrite all email fields.')
        with self.assertRaises(Exception):session.request_revision(state['run_id'],feedback,draft_version=1,draft_sha256=state['package']['package_sha256'])
        self.assertEqual(session.snapshot(),state)

    def test_invalid_exact_replacement_stops_before_review_or_writer(self):
        session,state,revisions,reviews=self.source()
        feedback=self.feedback(state,[('favorite','request_changes',True)])
        session.request_revision(state['run_id'],feedback,draft_version=1,draft_sha256=state['package']['package_sha256'])
        # Simulate a backend structural rejection, not a weakening of its rules.
        with patch('launchlens.agent_foundation.admit_package',side_effect=ValueError('Rejected')):
            after=session.run(state['run_id'])
        self.assertEqual(package_value(after),package_value(state));self.assertEqual(after['status'],'failed')
        self.assertEqual(len(revisions),0);self.assertEqual(len(reviews),1)

    def test_four_paid_noops_keep_revision_count_and_version_and_allow_explicit_retry_after_reload(self):
        class NoopWire(Wire):
            def __call__(self,model,validator):
                parent=super().__call__(model,validator)
                def call(payload):
                    result=parent(payload);inputs=json.loads(payload['messages'][-1]['content'])
                    if inputs.get('revision_protocol')==PROTOCOL:
                        candidate=package_cases()['initial_package']
                        for field in inputs['targeted_fields'].values():
                            from launchlens.field_revisions import set_text
                            set_text(candidate,field['format'],field['content_field'],field['text'])
                        value=json.loads(result.body)
                        value['choices'][0]['message']['content']=json.dumps(fixture_edits(inputs,candidate))
                        result=WireResponse(200,json.dumps(value).encode(),{})
                    return result
                return call
        with patch('launchlens.live_package.datetime',FrozenDateTime),patch('launchlens.live_package.project_writer_input',side_effect=project):
            wire=NoopWire();grant=permission();run=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW)
            state=run.execute(run.snapshot()['run_id']);original=deepcopy(state);cost=run.guard.cost
            for i in range(4):
                text=self.feedback(state,[('ice cream','request_changes',False)])
                run.request_revision(state['run_id'],text,draft_version=1,draft_sha256=state['package']['package_sha256'])
                state=run.execute(state['run_id'])
                self.assertEqual(state['revision_attempts'],0);self.assertEqual(state['package'],original['package'])
                self.assertEqual(state['review'],original['review']);self.assertEqual(len(state['draft_history']),1)
                self.assertGreater(run.guard.cost,cost);cost=run.guard.cost
                self.assertFalse(run.guard.pending_revision_claims)
                self.assertTrue(current_revision_resolution(state)['no_op'])
            self.assertEqual(run.guard.counts['package_revision'],4)
            self.assertEqual(run.guard.counts['package_reviewer'],1)
            restored=LivePackageRun(grant,KEYS,tools=ReviewFixtureTools(),wire_factory=wire,now=NOW,checkpoint=(state,run.capture()))
            self.assertTrue(restored.guard.can_revise())
            self.assertEqual(restored.snapshot(),state);self.assertEqual(restored.guard.cost,cost)

    def test_unlocated_automatic_blocker_hands_off_without_scope_expansion(self):
        session,state,revisions,_=self.source()
        from launchlens.package_content import validate_package_review
        raw={name:{'findings':[]} for name in state['drafts']}
        raw['blog']['findings']=[{'dimension':'tone','content_field':'$format','quote':None,
            'severity':'blocking','rationale':'Offline fixture whole-format issue.',
            'suggested_change':'Needs an exact field selection.','claim_ids':[]}]
        state['review']=validate_package_review(raw,state)
        session._automatic_refinement=True
        with patch('launchlens.package_content.protected_scan_hits',return_value=[]):
            after=session._after_required_review(state)
        self.assertEqual(after['status'],'awaiting_human_review')
        self.assertIsNone(after['revision_request']);self.assertEqual(revisions,[])
        self.assertEqual(after['ledger']['harness-auto-refinement']['reason'],'exact_field_targets_required')

    def test_review_only_reservation_and_noop_settlement_keep_actual_spending(self):
        with tempfile.TemporaryDirectory() as tmp,patch('launchlens.live_package.datetime',FrozenDateTime):
            path=Path(tmp)/'ledger.json'
            path.write_text(json.dumps({'ceiling_usd':'1.00','opening_accounted_usd':'0','claims':[],
                'accounted_usd':'0','remaining_usd':'1.00'}));path.chmod(0o600)
            budget=RunBudget(permission(),now=NOW);budget.standing=StandingBudget(path)
            budget.arm(permission()['request'])
            budget.reserve_revision({'run_id':'fixture'},writer_required=False,command_id='exact')
            self.assertEqual(set(budget.pending_revision_claims),{'package_reviewer'})
            def settle(role):
                event=budget.claim(role,'0'*64)
                budget.complete(event,{'model':budget.plan['roles'][role]['model_id'],
                    'usage':{'prompt_tokens':100,'completion_tokens':50,'total_tokens':150}})
            settle('package_reviewer')
            self.assertEqual(budget.counts['package_revision'],0)
            budget.reserve_revision({'run_id':'fixture'},command_id='writer')
            settle('package_revision');actual_cost=budget.cost
            budget.finish_noop_revision()
            self.assertEqual(budget.cost,actual_cost)
            self.assertFalse(budget.pending_revision_claims)
            ledger=budget.standing.read()
            from decimal import Decimal
            self.assertEqual(Decimal(ledger['accounted_usd']),actual_cost)
            self.assertTrue(any(c.get('usage',{}).get('not_called') for c in ledger['claims']))
            self.assertTrue(all(c['status']=='usage_accounted' for c in ledger['claims']))
            self.assertEqual(budget.events[-1]['revision_outcome'],'no_op')


if __name__=='__main__':unittest.main()
