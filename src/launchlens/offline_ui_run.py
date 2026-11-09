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
    FixtureWriter, action, review_adapters)

SCENARIOS = ('Standard review', 'Simulated launch-tool failure')


def fixture_inventory(display):
    tools = ReviewFixtureTools()
    return {'status':'ok', 'fetched_at':datetime.now(timezone.utc).isoformat(),
        'data_mode':'offline', 'source_access':{}, 'read_events':[],
        'markets':{market:market_row(tools.read_launch({'market_id':market}), market)
                   for market in display['case']['markets']}}


class OfflineUIRun:
    """Thin UI command boundary. All action execution/policy stays in the harness."""
    def __init__(self, request, notes='', scenario=SCENARIOS[0], *, voice_policy_id=None):
        request = validate_request(request)  # Before constructing/calling adapters.
        require(type(notes) is str and len(notes) <= 1000, 'Invalid agent notes')
        require(scenario in SCENARIOS, 'Unsupported offline scenario')
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
        reviewer, reviser = review_adapters(voice_policy_id)
        self.reviewer, self.reviser = reviewer, reviser
        self.writer = FixtureWriter()
        self.session = FoundationSession(self.controller, self.tools, mode='offline_review',
            writer=self.writer, reviewer=reviewer, revision_writer=reviser, voice_policy_id=voice_policy_id)
        self.session.start(request, user_notes=notes)

    def snapshot(self):
        return self.session.snapshot()

    def execute(self, run_id):
        return self.session.run(run_id)

    def revise(self, run_id, feedback, version, draft_hash):
        # Permission and exact version checked by the existing owner-only command.
        self.session.request_revision(run_id, feedback,
            draft_version=version, draft_sha256=draft_hash)
        return self.session.run(run_id)

    def reset(self):
        self.session.reset()

    def capture(self):
        """Available full mock responses remain inspectable for this current run."""
        return deepcopy({'writer_candidate':self.writer.candidate if self.writer.calls else None,
                         'review':self.reviewer.calls,
                         'revision':self.reviser.calls})


def draft_identity(state):
    record = state['drafts']['linkedin']
    return record['version'], digest(record['draft'])
