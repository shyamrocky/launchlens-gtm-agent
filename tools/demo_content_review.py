"""Readable, zero-network Reviewer/revision demonstration inside FoundationSession."""
from pathlib import Path
import argparse
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from foundation_fixtures import request
from reviewer_fixtures import (cases, ReviewFixtureTools, ScriptedReviewController,
                              FixtureWriter, review_adapters)
from launchlens.agent_foundation import FoundationSession
from launchlens.linkedin_drafting import digest
from launchlens.voice_policy import BRAND_POLICY_ID


def main():
    parser=argparse.ArgumentParser(description='Offline mock review; never inference')
    parser.add_argument('--package',action='store_true',help='Show the full five-format offline package')
    parser.add_argument('--voice-policy',choices=[BRAND_POLICY_ID],default=None)
    args=parser.parse_args()
    if args.package:
        return package_demo()
    policy_id=args.voice_policy
    print('# Reviewer + one revision — OFFLINE SIMULATION\n')
    print('Writing policy:',policy_id or 'historical neutral policy')
    print('Scripted model choices and authored mock reviews. No live semantic-review quality is claimed.\n')
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline demo forbids network')) as network:
        for name in ['supported','unsupported','misleading']:
            reviewer,reviser=review_adapters(policy_id)
            session=FoundationSession(ScriptedReviewController(),ReviewFixtureTools(),mode='offline_review',
                writer=FixtureWriter(cases()[name+'_candidate']),reviewer=reviewer,revision_writer=reviser,voice_policy_id=policy_id)
            state=session.run(session.start(request())['run_id'])
            print(f'## {name}: {state["review"]["review_status"]}')
            for f in state['review']['assessment']['findings']:
                print(f'- {f["dimension"]}: “{f["quote"]}” — {f["rationale"]}')
            print()
        reviewer,reviser=review_adapters(policy_id)
        session=FoundationSession(ScriptedReviewController(),ReviewFixtureTools(),mode='offline_review',
            writer=FixtureWriter(),reviewer=reviewer,revision_writer=reviser,voice_policy_id=policy_id)
        before=session.run(session.start(request())['run_id'])
        print('## Preserved Hermes draft: before')
        print(before['drafts']['linkedin']['draft']['content']['hook'])
        print(before['drafts']['linkedin']['draft']['content']['body'])
        print('\n## Mock independent findings')
        for f in before['review']['assessment']['findings']:
            print(f'- {f["severity"]} / {f["dimension"]}: “{f["quote"]}” — {f["suggested_change"]}')
        feedback=('Keep optional brand voice; remove introduction implication and unsupported flavor intensity.' if policy_id else
                  'Use neutral third-person wording and source-faithful vanilla notes.')
        print('\nExplicit fixture-owner feedback:',feedback)
        session.request_revision(before['run_id'],feedback,
            draft_version=1,draft_sha256=digest(before['drafts']['linkedin']['draft']))
        after=session.run(before['run_id'])
        print('\n## Revised fixture draft: version 2')
        draft=after['drafts']['linkedin']['draft']
        for field in ['hook','body','cta']:print(draft['content'][field]+'\n')
        print(' '.join(draft['content']['hashtags']))
        print('\nRe-review:',after['review']['review_status'],'(scripted mock; human review still required).')
        print('Versions retained:',len(after['draft_history']),'Reviews retained:',len(after['reviews']))
        print('Actual harness actions:', ' → '.join(e['action'] for e in after['events'] if e.get('action_id')))
        print('Shared call budget:',after['turns'],'of 12; revision attempts:',after['revision_attempts'])
        print('Human accepted:',after['human_accepted'],'Publishing:',after['drafts']['linkedin']['publishing_allowed'])
        print('Network attempts:',network.call_count,'No sources or historical responses modified.')


def package_demo():
    from launchlens.offline_ui_run import OfflineUIRun, draft_identity
    from launchlens.package_content import FORMATS, LABELS, text_fields
    print('# Full GTM package — OFFLINE SIMULATION')
    print('Scripted choices and authored mock outputs; no live model or semantic-quality claim.\n')
    with patch.object(socket.socket,'connect',side_effect=AssertionError('No demo network')) as network:
        run=OfflineUIRun(request(),voice_policy_id=BRAND_POLICY_ID,package=True)
        first=run.execute(run.snapshot()['run_id'])
        assert first['status']=='awaiting_human_review'
        for name in FORMATS:
            print('## '+LABELS[name]+' · Version 1')
            for field,text in text_fields(first['drafts'][name]['draft']['content']):
                print(field.replace('_',' ')+': '+text+'\n')
            print('Claim references:',first['drafts'][name]['draft']['claim_references'])
            print('Mock review:',first['review']['format_reviews'][name]['review_status'])
            for finding in first['review']['assessment'][name]['findings']:
                print('- '+finding['dimension']+': '+finding['rationale'])
            print()
        v,h=draft_identity(first)
        after=run.revise(first['run_id'],'Keep optional brand voice; remove unsupported intensity and introduction implication.',v,h)
        assert after['status']=='awaiting_human_review'
        print('## One explicit package revision + fresh review')
        print('Formats:',', '.join(FORMATS),'· Package version:',after['package']['version'])
        print('Calls:',after['turns'],'of 12 · Reviews:',len(after['reviews']))
        print('Human accepted:',after['human_accepted'],'Publishing:',after['package']['publishing_allowed'])
        print('Actions:',' → '.join(e['action'] for e in after['events']))
        for market in ['UK','IN']:
            blocked=OfflineUIRun(request(market),voice_policy_id=BRAND_POLICY_ID,package=True)
            state=blocked.execute(blocked.snapshot()['run_id'])
            print(market+': '+state['status']+' · formats drafted: '+str(len(state['drafts'])))
        print('Network attempts:',network.call_count)


if __name__ == '__main__':main()
