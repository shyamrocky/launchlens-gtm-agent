# Writing voice — bounded offline policy update

Decision **M2-D021**, 2026-11-09 (America/Los_Angeles).
Status: **OWNER-APPROVED DIRECTION; IMPLEMENTED OFFLINE / TECHNICAL PASS,
IMPLEMENTATION REVIEW PENDING**.

The owner questioned why a PMM's brand draft could not say “we,” reviewed independent
Claude/GPT feedback, and explicitly approved the proposed small offline update.
Those external reviews informed this decision; their text did not independently
change permissions, revision limits, evidence or launch policy.

## Decision and alternatives

Allow **simulated brand voice**, including optional “we”/“our,” in LinkedIn marketing
drafts. Neutral sentences and naming the product are still allowed; first person
is not mandatory. Internal campaign briefs, research and readiness reporting remain
neutral. Other channel mappings record direction only; their generation is not
implemented here. The application owns this policy, not the model or user notes.

Rationale: a PMM should be able to assess realistic brand-style marketing copy.
Voice, factual support and operational permission are separate judgments. The old
neutral-only policy remains a historical reproduction option, not a universal rule.
Alternatives: keep all formats neutral (too restrictive for this intended task),
force first person (unnecessary), or introduce a voice-selection UI/new agent
(unnecessary for this MVP). No new pipeline, agent, framework or dependency.

## What changed and what did not

[Versioned configuration](../../../data/templates/gtm/voice_policy_v1.json),
[policy binding](../../../src/launchlens/voice_policy.py), and three new prompts:

- [Writer](../../../src/launchlens/prompts/linkedin_writer_brand_v1.txt)
- [Reviewer](../../../src/launchlens/prompts/linkedin_reviewer_brand_v1.txt)
- [Revision](../../../src/launchlens/prompts/linkedin_revision_brand_v1.txt)

The original Writer/Reviewer/revision prompts, old safe fixture JSON and protected
model receipts remain byte-for-byte unchanged. Historical runs use their original
instructions. New prompts are distinct, SHA-256-bound files. Policy ID/version/hash
and mode are included in the authoritative Writer input identity; old reviews cannot
be attached to a newly selected policy. Source text remains lower-trust evidence/
guidance; an old PMM style preference cannot override the selected writing mode.
Material factual caveats/conflicts are retained, not deleted to simplify copy.

Same FoundationSession/LangGraph, original content contract, evidence retrieval,
backend draft/review validators and accepted context-selection algorithm. Six
Reviewer dimensions and existing blocking/advisory severities are unchanged.
The policy is an optional application-selected constructor parameter for
`offline_review`; historical callers/defaults keep the old policy. Newly started
offline UI simulations explicitly select `simulated_brand_v1`. Generate again
retains the selected policy; current-run rendering labels it. No user voice picker.

**No live rollout:** the current live Writer/provider route remains historical and
rejects the new input profile before transport. Live harness profiles cannot select
the new policy. No provider/model choice or spending approval transfers to it.

| Concern | Treatment |
|---|---|
| “We” or “our” alone | Allowed in simulated brand voice; no product citation just for a pronoun |
| Product facts in the same sentence | Still require eligible supporting claims and qualifications |
| Unsupported availability, novelty, company actions or launch commitments | Evaluate complete meaning and supplied restrictions; identify missing support |
| Material ambiguity | Explain uncertainty; existing `uncertain` assessment + blocking finding can require resolution; do not claim proven falsity |
| Explicit voice/role-rule violation | Report under voice, separate from factual grounding |
| Stylistic preference or short length | Advisory; no automatic revision or added facts to meet targets |

The prompts do not add a pronoun/verb blacklist. Ordinary persuasive language is not
automatically a factual claim. For example, “we’re bringing” may imply an introduction,
but is not itself proof of current store availability. “A hint of vanilla” may add
unverified intensity; that is not proof the phrase is false. A live Reviewer must
make these assessments; JSON structure and valid IDs cannot establish entailment.

**All original boundaries remain:** allowed facts PROD-002/003; exact CTA; nonempty,
eligible, unique citation entries; full original evidence for backend admission;
UK Clarify, India Hold; no invented offers/links/stock/approval; current LinkedIn
availability/launch-date wording restrictions even for US Proceed; one explicit
owner-authorized revision with exact-version re-review. Voice does not grant
company affiliation, product truth, launch approval, human approval or publishing.
Application labeling stays outside marketing copy. Export implementation/labeling
remains a later checkpoint; no export or publication is added.

## Readable comparison — authored offline expectations

Separate safe fixtures: [brand-policy cases](../../../tests/fixtures/gtm_brand_voice_cases_v1.json).
The original [neutral-policy cases](../../../tests/fixtures/gtm_review_cases.json) are
preserved; the protected Hermes candidate is neither modified nor reclassified.
These are selected test concerns, not an exhaustive or live semantic review.

| Text | Historical neutral rule | New simulated-brand rule |
|---|---|---|
| “We’re exploring the classic soda-float inspiration behind Coca-Cola Cherry Float.” | First-person brand role conflicts with the old neutral instruction | Voice permitted; factual inspiration still references PROD-003 |
| “We’re bringing that nostalgic inspiration to a new Coca-Cola flavor.” | Old mock flags manufacturer voice | New mock passes voice; separately reports uncertain introduction/novelty implication, without asserting current availability or proven falsity |
| “A hint of vanilla” | Old mock asks for source-faithful wording | Qualification concern remains, framed as unverified intensity rather than proven falsehood |
| “Made with real vanilla ice cream.” citing PROD-003 | Unsupported ingredient assertion | Still unsupported; the valid ID does not prove the assertion |
| “Available now” / invented discount | Existing hard output rejection | Same hard rejection |

Example revised **fixture** post after explicit owner feedback:

> We’re exploring the classic soda-float inspiration behind Coca-Cola Cherry Float.
>
> Cherry with vanilla notes, inspired by classic soda floats. Nostalgia offers a creative starting point for this flavor story.
>
> What would you like to know about Cherry Float's flavor inspiration?
>
> #CocaCola #CherryFloat #FlavorDiscovery

Hook references PROD-003; body references PROD-002/003. Nonfactual CTA/categorization
hashtags have no citation entry. Word count remains advisory; this is not a newly
generated or owner-approved marketing asset. Mock version2 receives fresh review,
with human acceptance and publishing still false.

## Actual offline verification

**334 tests PASS:197 agent +111 root +26 UI.** Fourteen new checks (12 agent, 2 UI)
cover prompt/policy identities, historical defaults, permitted first-person and
neutral wording, source/notes/action injection, unsupported/misleading claims,
editorial-only nonrevision, unchanged citation/CTA/offers/availability checks,
UK/India/failed-source/incomplete-evidence restrictions, stale review/policy binding,
one explicit revision and fresh review, new UI selection and legacy-run preservation.
New focused tests block sockets and assert zero connection attempts. Test fixtures
prove contracts and connections; they do not prove a live model follows the policy.

Clean canonical copy: **197 agent +26 UI tests PASS** without workspace, private/
generated artifacts, credentials or original PDFs, using the existing provisioned
Python environments. No new installation or lockfile change. The readable brand
and historical-neutral demos both remain available; the new demo reports zero
network attempts and no human acceptance/publishing.

Chrome verified a fresh offline US run shows “Writing voice: simulated brand ·
Policy v1” and the new findings: no pronoun-only voice rejection, separately stated
material introduction/novelty ambiguity and unverified intensity. The local8520
server was restarted only in offline mode; the previous disposable demo session
was cleared. Current Version1 is left ready for owner inspection/one explicit
revision. Historical files/receipts were not overwritten. No live source or model
call was needed for this check.

Final syntax, JSON, relative-link, exact credential-value exclusion and
`git diff --check` checks PASS. **326 of341 baselined files unchanged**, including
145 protected pre-existing prompt/data/MEMORY files. Fifteen existing files changed
(including two current-state notes); eight canonical files added. Original source
facts, operational datasets, templates/projection policy, model configurations,
protected responses, credentials and locks remain unchanged.
No dependencies, source service calls, paid inference, hosted LangSmith, Git staging,
commit/push or MEMORY append. Existing source datasets and accepted context-projection
configuration remain unchanged. Canonical configuration/code/fixtures supply everything
required; no dependency on workspace or private experimental artifacts.

Use the existing readable demo (no provider calls):

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/demo_content_review.py --voice-policy simulated_brand_v1
```

Omit the flag to reproduce the historical neutral mock path. Demo uses one revision,
two exact-version reviews, 11/12 simulated shared calls and zero network attempts.

## Next boundary

Stop for owner inspection of this offline policy update. M2.3b content and prior
checkpoint acceptance remain separate. Next proposed only: explicit live model
profiles, request identities and whole-run budgets; then one separately authorized
US end-to-end test. No live run, final model adoption, other formats, human acceptance/
export, tracing or Git publication is authorized here.
