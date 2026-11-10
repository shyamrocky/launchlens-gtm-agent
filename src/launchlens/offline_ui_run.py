"""Explicit offline UI adapter for the existing FoundationSession, never a provider.

Only canonical safe fixtures are accepted. No source/credential reads, live model
transport, alternate graph, background job, or durable run storage is created.
"""
from copy import deepcopy
from datetime import datetime, timezone

from launchlens.agent_foundation import FoundationSession
from launchlens.gtm_registry import require, validate_request
from launchlens.inventory import market_row
from launchlens.linkedin_drafting import digest
from launchlens.offline_fixtures import (ReviewFixtureTools, ScriptedReviewController,
    FixtureWriter, action, review_adapters, package_adapters)

SCENARIOS = ('Standard review', 'Simulated launch-tool failure', 'Bad Writer response', 'Bad Writer twice')


def fixture_inventory(display):
    tools = ReviewFixtureTools()
    return {'status':'ok', 'fetched_at':datetime.now(timezone.utc).isoformat(),
        'data_mode':'offline', 'source_access':{}, 'read_events':[],
        'markets':{market:market_row(tools.read_launch({'market_id':market}), market)
                   for market in display['case']['markets']}}


class OfflineUIRun:
    """Thin UI command boundary. All action execution/policy stays in the harness."""
    def __init__(self, request, notes='', scenario=SCENARIOS[0], *, voice_policy_id=None, package=False):
        request = validate_request(request)  # Before constructing/calling adapters.
        require(type(notes) is str and len(notes) <= 1000, 'Invalid agent notes')
        require(scenario in SCENARIOS, 'Unsupported offline scenario')
        require(type(package) is bool, 'Invalid package selection')
        self.package = package
        self.scenario = scenario
        self.tools = ReviewFixtureTools()
        if scenario == SCENARIOS[1]:
            self.tools.fail = 'launch'
        # These are authored test decisions, never claimed as live model choices.
        if request['market_id'] == 'US':
            actions = None
        else:
            actions = [action('check_launch','launch'), action('finish','pause')]
        self.controller = ScriptedReviewController(actions)
        if package:
            self.writer, reviewer, reviser = package_adapters()
            if actions is None:
                self.controller = ScriptedReviewController([
                    action('read_pmm_brief','pmm'), action('check_launch','launch'),
                    action('search_product_evidence','facts',query='Flavor and classic soda-float inspiration',authority='public_product_facts'),
                    action('generate_package','write'), action('review_package','review-v1'),
                    action('revise_package','revise-v2'), action('review_package','review-v2')])
        else:
            reviewer, reviser = review_adapters(voice_policy_id)
            self.writer = FixtureWriter()
        if package:
            purposes={'read_pmm_brief':'Read positioning and tone so drafts follow the campaign strategy.',
                'check_launch':'Check the market and date against the authoritative readiness records.',
                'search_product_evidence':'Find complete flavor and inspiration evidence before making product claims.',
                'request_clarification':'Ask how to proceed while availability is unconfirmed.',
                'generate_package':'Use the researched facts and creative direction to draft all five formats.',
                'review_package':'Have a separate Reviewer check the exact package against evidence and restrictions.',
                'revise_package':'Address the requested changes while preserving evidence and launch restrictions.'}
            actions=[action('read_pmm_brief','pmm'), action('check_launch','launch'),
                action('search_product_evidence','facts',query='Flavor and classic soda-float inspiration',authority='public_product_facts')]
            if request['market_id']=='UK':actions.append(action('request_clarification','ask',question='UK availability is unconfirmed. Continue without availability wording, recheck readiness, or stop?'))
            actions += [action('generate_package','write'),action('revise_package','revise-v2')]
            for entry in actions:entry['why']=purposes[entry['name']]
            self.controller=ScriptedReviewController(actions)
            if scenario in {'Bad Writer response','Bad Writer twice'}:
                base=self.writer._transport
                class BadWriter:
                    def __init__(self):self.count=0
                    def __call__(self,payload):
                        import json
                        self.count+=1
                        response=base(payload)
                        if self.count==1 or scenario=='Bad Writer twice':
                            candidate=json.loads(response['choices'][0]['message']['content'])
                            candidate['campaign_brief']=13
                            response['choices'][0]['message']['content']=json.dumps(candidate)
                        return response
                self.writer._transport=BadWriter()
        self.reviewer, self.reviser = reviewer, reviser
        self.session = FoundationSession(self.controller, self.tools, mode='offline_package' if package else 'offline_review',
            writer=self.writer, reviewer=reviewer, revision_writer=reviser, voice_policy_id=voice_policy_id)
        self.session.start(request, user_notes=notes)

    def snapshot(self):
        return self.session.snapshot()

    def execute(self, run_id, *, on_update=None):
        return self.session.run(run_id,on_update=on_update)

    def continue_run(self,run_id,*,on_update=None):
        return self.session.continue_run(run_id,on_update=on_update)

    def resume(self,run_id,reply,*,on_update=None):
        return self.session.resume(run_id,reply,on_update=on_update)

    def retry_writer(self,run_id,*,on_update=None):
        return self.session.retry_writer(run_id,on_update=on_update)

    def can_review_saved(self):return self.session.can_review_saved()

    def review_saved(self,run_id,*,on_update=None):return self.session.review_saved(run_id,on_update=on_update)

    def stop(self,run_id):
        self.session.stop(run_id)

    def edit_current_fields(self,run_id,changes,*,draft_version,draft_sha256):
        result=self.session.edit_current_fields(run_id,changes,draft_version=draft_version,draft_sha256=draft_sha256)
        return result

    def revise(self, run_id, feedback, version, draft_hash):
        # Permission and exact version checked by the existing owner-only command.
        self.session.request_revision(run_id, feedback,
            draft_version=version, draft_sha256=draft_hash)
        return self.session.run(run_id)

    def reset(self):
        self.session.reset()

    def capture(self):
        """Available full mock responses remain inspectable for this current run."""
        return deepcopy({'writer_candidate':(self.writer.calls[-1].get('candidate') if self.package else self.writer.candidate) if self.writer.calls else None,
                         'writer':self.writer.calls,
                         'review':self.reviewer.calls,
                         'revision':self.reviser.calls})


def draft_identity(state):
    if state['mode'] in {'offline_package','live_package'}:
        return state['package']['version'], state['package']['package_sha256']
    record = state['drafts']['linkedin']
    return record['version'], digest(record['draft'])
