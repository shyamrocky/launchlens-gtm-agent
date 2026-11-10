# Full GTM package — existing-harness integration

Decision **M2-D022**, 2026-11-09, America/Los_Angeles.
Status: **OWNER-AUTHORIZED SCOPE; OFFLINE TECHNICAL PASS; OWNER REVIEW PENDING**.

The owner approved moving from another isolated LinkedIn checkpoint to one full-
package integration milestone. Implement and verify offline, then prepare a separately
approved live US package run. This supersedes LinkedIn-first sequencing for this
increment only. It does not accept earlier marketing content or authorize inference,
Git publication, human acceptance, export or hosted tracing.

## What now works offline

| Deliverable | Existing contract retained | UI and review |
|---|---|---|
| Campaign brief | Objective, audience hypothesis, positioning, three pillars, tone, CTA, restrictions | Neutral creative anchor; its own six-dimension review |
| LinkedIn | Hook, body, exact existing CTA, hashtags | Simulated brand voice; existing strict admission reused |
| Promotional email | Subject, preview, headline, body, CTA | Distinct channel copy; its own review |
| Short blog | Title, introduction, sections, conclusion, CTA | Nested field citations and exact-quote review |
| Ad variations | Exactly three angle/headline/body/CTA concepts | All three checked inside the ads assessment |

One Writer call returns all five formats in a structured package. Its instructions
establish the campaign brief as shared creative direction and adapt it to the
channels within the same response; there is no separate hidden brief-generation
call. The brief is never promoted to product evidence or launch permission.
One separate Reviewer call assesses every format and cross-format consistency.
Alternative: separate Writer/Reviewer calls for each format would increase orchestration
and the shared call budget. The selected package-level calls reuse the current limits;
the tradeoff is that one invalid channel rejects the complete candidate, whose response
is still preserved. No automatic per-format repair or fallback is added.
These are model-selected actions inside the same FoundationSession/StateGraph,
not a new orchestrator or a forced Research → Write → Review graph. Offline scripted
controllers demonstrate different permissible research orders; live autonomy for
the new package profile remains untested.

**The visible copy and reviews are authored fixtures.** No new model wrote them.
The preserved Hermes LinkedIn response is reproduced as a safe fixture, retaining
its introduction/intensity concerns. Other formats are independently authored test
copy. Some fixtures fall below advisory length targets; those warnings remain
visible and never become automatic retries. Mock assessments are not independent
live factual verification or acceptance of the copy.

## Reuse and implementation boundaries

- Existing five JSON templates are byte-for-byte unchanged. New
  [package execution configuration](../../data/templates/gtm/package_execution_v1.json)
  SHA-binds those templates and four separate versioned prompts. The earlier voice
  configuration remains unchanged; the package profile applies its approved format
  mappings (neutral brief, optional simulated-brand channels).
- [package_content.py](../../src/launchlens/package_content.py) reuses original
  research/permission admission, evidence reconstruction, five content contracts,
  LinkedIn admission and the existing Reviewer assessment validator. No new source,
  database, pipeline, framework, dependency or model registration.
- Three actions in the existing registry: `generate_package`, `review_package`,
  `revise_package`, available only in the explicit `offline_package` profile.
  New live routes are not enabled. Existing Qwen/Hermes transport settings reject
  these new request envelopes before sending them; old authorizations do not transfer.
- Separate package Writer, Reviewer, revision and controller prompts live in
  `src/launchlens/prompts/package_*_v1.txt`; the historical prompts are unchanged.
  Same ROLE/task/boundaries/constraints/output structure, citation rules and current
  ban on unsupported availability/launch wording. Provider-enforced schema output
  has not been adopted. Prompt text is guidance; backend validation remains required.
- Full response is captured before parsing/admission using existing ContentCall.
  Every format must validate before any package draft is stored. One malformed
  format rejects the whole candidate, while preserving the complete available
  response/candidate. No partial package, cleanup, repairs or retries.
- The original complete authority independently drives backend validation. The
  accepted context projection is reused through its existing seam; material caveats,
  conflicts, qualifications and all direct source mappings remain. The projection
  audit ledger is retained for inspection but excluded from new model messages.
- Reviews bind the exact run, whole package, version, authoritative input and creative
  anchor hashes. Each format has six assessments and exact-quote findings, including
  nested blog/ad/brief fields. One missing/invalid format review rejects the complete
  review; no format is silently marked reviewed. Structurally valid review can still
  be semantically wrong; tests explicitly preserve that distinction.
- Explicit owner feedback authorizes at most one whole-package revision. The model
  must choose the revision action. All five outputs are revalidated and freshly
  reviewed, including unchanged pieces; prior review cannot label a changed package.
  Failed revision retains version 1; failed version-2 review leaves version 2 unreviewed.
- The same shared **12 model calls / 4 searches** remain. Standard fixture path uses
  7 calls through first review, 11 including one revision and re-review. These counts
  include controller selections and content calls. No fixed live call sequence is
  claimed; extra research/replayed selections consume the same budget and may stop it.
- Writer/revision output caps: 8,192 tokens; Reviewer: 4,096. These are prepared request
  settings for a new profile, not approved provider compatibility or spending. Length
  truncation is retained and rejected, with no automatic second attempt.
- UK Clarify, India Hold, unsupported product rejection, source failure, incomplete
  evidence, human-acceptance-false and publishing-disabled protections remain.
  No India research-only generation or free-text approval override was introduced.

## Evidence-preservation check with frozen real research

An offline-only child copy of the existing checksum-pinned research state was
prepared with the new application-owned package profile; no source refresh occurred.
Source state SHA-256:
`6ba71a0685bad5a6924f93d77e68de97dfb3675a1e2f8a6b8ae5423c15411b2b`.

Full authoritative input: **72,351 bytes**. Projected Writer brief: **38,305 bytes**.
The unchanged projection produced **284 include/exclude records**, retained both
PROD-002/003 claims, **four direct claim/source mappings** and all four material-
boundary entries. Full five-format fixture admission passed independently against
those original packets. This checks assembly, not live factual writing or tokens.

Authoritative package-input SHA-256:
`16d4ef34bcfb584a62a4b29a0cfc7e544cc37d8d95e2ca3feea7ecc0f5e3de53`.
This is an input identity, not a final provider-request identity: live model choices,
provider token qualification and whole-run reservation remain unresolved.
The private frozen state is an optional historical experiment input, not an
application/test prerequisite. Clean-copy checks use canonical safe substitutes.

## Verification

**371 offline tests passed: 231 agent +111 root +29 UI.**
Thirty-four new harness checks and three new UI checks cover all-five completeness,
three-ad shape, per-format citation/CTA/link/offer restrictions, exact/nested quote
validation, missing reviews, misleading valid citations, cross-format findings,
material authority/creative-anchor binding, projection boundary, prompt integrity,
replay suppression, alternate research order, call limits, tool failures, UK/India,
explicit feedback, failed revisions/reviews, reset and historical LinkedIn behavior.
Package and UI tests block socket connections and assert zero attempts. New UI
checks verify five tabs and fresh review of the entire revised package.

Clean canonical copy: **231 agent +29 UI tests passed**, using the existing provisioned
Python environments without workspace, credentials, generated/private inputs or original
PDFs. The runtime source/configuration/fixtures match the tested worktree exactly.
No package installation or lockfile change occurred.

Chrome desktop checks verified all five output tabs, exactly three ad concepts,
whole-package version 1 → explicit feedback → version 2 and fresh review, and Generate
again returning a fresh version-1 package with revision available. The final UI groups
copy into one card per format or ad concept, escapes source text and renders advisory
lengths in plain English. The local server remains explicitly offline on port8520.
No mobile, cross-browser or full accessibility certification is claimed.

Syntax, JSON, **146 relative links**, local credential-value/pattern exclusion and
`git diff --check` passed. **319 of335 baselined files unchanged** after updating the
two local continuity notes; 16 existing files changed and 9 canonical files added.
All **149 protected** pre-existing source/template/prompt/config/lock/receipt/credential/
MEMORY files remain unchanged. Approved datasets and historical responses preserved.
Git staging is empty; no commit/push or MEMORY append. No test proves that a hosted model will comply, catch every unsupported
statement or produce good marketing copy. No quality/reliability guarantee inferred.

## Inspect it

Use the existing local UI at http://127.0.0.1:8520/ in **Offline simulation**.
Open US → Start simulation. Inspect the five tabs, each format's mock review,
shared evidence and actual harness activity. Enter feedback → Request one revision.
Generate again starts a fresh whole-package simulation; Reset clears this session's
current task. No archive, new UI route or live fallback was introduced.

Existing reproducible setup remains:

```sh
uv sync --project tools/ui --locked --group offline-agent --no-python-downloads
LAUNCHLENS_UI_MODE=offline uv run --project tools/ui --locked --group offline-agent --no-python-downloads streamlit run streamlit_app.py
```

Canonical safe fixtures are provisioned by the repository checkout:
[gtm_package_cases_v1.json](../../tests/fixtures/gtm_package_cases_v1.json), plus the
existing neutral/brand cases. No runtime dependency on workspace or ignored receipts.
For a readable terminal report including all five outputs and review/revision:

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/demo_content_review.py --package
```

Omitting `--package` retains the historical LinkedIn demonstration.

## Next owner decision — one live full-package run

After offline review, prepare an explicit Nebius live profile for **one US package
run**, evaluation date December 14, 2026, objective flavor_discovery, and optional
one owner-requested revision/re-review. It will use the existing source tools and
same graph, the new package prompts, accepted context projection and full original
authority. It is a new integration test, not a repeat of the old LinkedIn experiment.

Candidate role assignments for review: existing provisional Qwen30 controller;
Hermes405B Writer and separate Reviewer calls, based on the preserved one-attempt
Writer result. This does not adopt a default model or establish live Reviewer
quality; same-family Writer/Reviewer may share blind spots. Current model access,
prices, request compatibility and token reservations must be qualified before any
live authorization is requested. No replacement model or inherited spending approval.

Proposed **$0.50 aggregate ceiling**, not an estimate or spending permission. Keep
12 shared calls, 4 searches, one initial package, two maximum reviews and one explicit
revision; zero automatic retries/repairs. Before enabling, bind exact model IDs,
prompt/template/projection/source identities and per-call/aggregate reservations.
Stop on unresolved prices, token bounds, authority, unknown usage or transport
failure. Reviewer/revision request hashes depend on actual earlier outputs and must
be recorded and qualified before their own calls; they cannot be precomputed from
unknown drafts. Current code does not implement this paid-run reservation/profile.

Separate approval is required for actual inference. Live UI activation, human
acceptance/export, sanitized LangSmith and certification submission remain later
completion work; no full certification completion is claimed here.
