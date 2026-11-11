## Known E2E issues pending approval

November 10, 2026: owner reports final live E2E passed for US, UK and India.
The assistant did not repeat those live runs. Read-only saved-file/code diagnosis
confirmed three remaining defects; their fixes require separate owner approval:

- **Suggestion submission:** Use suggestion currently queues an immediate exact
  revision and fresh review, consuming a revision when text changes. Expected:
  record the choice and apply it only on Create next version. This behavior is
  preserved in this sync; the earlier implementation's immediate-submit
  interpretation was incorrect.
- **Citation retry after clarification:** field_claim_coverage is recognized as
  citation-only, but automatic retry is attached only to LivePackageRun.execute.
  resume/continue_run bypass that wrapper, so a rejected post-clarification Writer
  response can stop after one call although manual Try again is eligible.
- **Approved run across markets:** Prepare uses raw status/human_accepted flags;
  actual approval is a matching protected receipt/UI state and does not set those
  flags. The earlier test fabricated approved flags rather than clicking real
  approval, so it missed the receipt-based case.

No fix, new inference, run change, content approval, budget adjustment or retry is
included in publication of this diagnosis. Future regressions must use minimal
synthetic inputs, with real approval flow and continuation entry points exercised
offline; protected responses/runs remain local. Earlier pending-restart and saved
run status notes below describe their original checkpoints.

---

## Fixture storage follow-up — November 10, 2026

Owner clarified that code/tests belong in normal version-controlled project
locations, workspace is continuity-only, and regression fixtures must be minimal
synthetic failure shapes rather than copied Writer responses or protected runs.
The revision test fixture now has two short independently authored strings
(196bytes): an unchanged field and a partially edited field with a repeated phrase.
Removed copied response excerpts and unused section text; assertions derive offsets
from synthetic input. Application code and saved artifacts are unchanged.

Verification:450 harness +113 UI tests PASS in an isolated copy without credentials,
saved responses, private receipts or protected run files. Existing
maintained fixtures and version-controlled source inputs remain available. No new
application test claim, live call, runtime change, restart or Git sync. The earlier
M2-D053 root results below remain historical; this follow-up changes test data,
assertions, policy and continuity notes only.
[Canonical storage policy](../project-governance.md#reproducibility-and-private-runtime-artifacts).

---

## M2-D053 — Targeted field edits, exact suggestions and no-op accounting

**Date/authority:** November 10, 2026. Owner approved the bounded field-edit fix
with three explicit changes: Use suggestion applies its exact replacement in
code without a Writer call; notes guide targeted fields only and cannot expand
scope; a no-op response does not use the three-revision allowance, while actual
model spending remains spent. **Status:** implemented offline; owner review and
app restart pending. No live execution or Git publication authorized here.

**Decision and rationale:** retain the existing harness and independent fresh
Reviewer, but replace whole-package revision output with source-bound field edits.
The saved UK V1/V2/V3 were identical across all46 text fields despite44 requested
occurrences; field edits reduce copying pressure and make scope enforceable.
Alternatives rejected: another prompt-only whole-package rewrite, unbounded retry,
notes selecting arbitrary fields, and refunding actual model usage. This supersedes
the earlier Writer-mediated-suggestion and no-op-cap proposals, not their history.

**Input/output boundary.** New versioned `targeted_fields_v1` permission and hashed
`package_field_revision_v1.txt` prompt operate in the existing revision node and
ContentCall adapter. Each targeted field appears once, with its exact hash,
requested occurrences, keep spans and approved replacements. The Writer receives
original eligible evidence/qualifications/launch constraints, relevant format tone,
the complete avoid-list and current flagged locations. Duplicate whole-package
schemas, review transcripts and the rest of the package are excluded. Notes are
guidance only. Every returned field ID/hash, source package hash, text value and
citation list is checked; missing/unknown edits, invalid citations and attempts to
undo keeps or exact replacements are rejected before admission. The full merged
package is then validated against original evidence and structural policy and
fresh-reviewed. The AI assessment and deterministic request outcomes stay separate.

**Exact suggestions.** Clicking Use suggestion queues a literal span replacement,
validation and fresh Reviewer only. Offsets are checked against the bound source;
repeated replacements apply in reverse order. Mixed exact/rephrase requests shift
remaining request/keep coordinates to the text actually supplied to the Writer.
An exact change has explicit deterministic provenance and no fabricated Writer
receipt. A successful exact replacement creates a revised version and uses one
revision under the existing limit. Notes-only/all-kept UI submissions cannot start
a rewrite; direct API guidance is bounded to current flagged locations. Unlocated
automatic findings hand off for exact field selection rather than expanding scope.

**No-op/accounting.** A valid response with no text changes preserves the current
package, version, history and existing matching review. It clears the command and
returns to human review; it does not consume a revision or automatically call again.
A later explicit command has a new identity, so replay protection does not block
an intentional request after a no-op. Every actual Writer call/usage/cost remains
in captures and the spending ledger. Only a provably uncalled Reviewer reservation
is settled at zero; actual spending is never refunded. Budget/raw-call counters
and consumed revisions are separate and survive restore, including more than
three raw calls when the excess are audited no-ops. Other failure handling retains
its existing conservative behavior. The one automatic pass is still single-use.

**Historical/current-state preservation.** Original prompts, configuration,
profiles, source data, authorization receipts, decisions, approvals and accounting
are unchanged. Old packages remain valid through original contracts; new package
metadata records the actual revision protocol/method/prompt identity. No prior
attempt is retroactively refunded. Current saved UK Version3 remains unapproved,
2of3 used; no remaining revision, suggestion, review or model call was executed.

**Verification:**450 harness +113 UI +114 root tests PASS offline in an isolated
copy, using existing interpreters with no install/dependency change. New and updated
regressions cover saved V3/V4 shapes and partial survivors, both origins/US/UK,
market-independent helpers, exact suggestions with zero Writer/one fresh Reviewer,
notes-only rejection and attempted scope expansion, shifted offsets after exact
edits, stale/unknown/missing fields and citations, keep/suggestion preservation,
four paid no-ops with zero consumed revisions and checkpoint restore, review-only
reservations and known-unused-review settlement, current/source contract integrity,
and the existing approval/limit/recovery controls. Mock transports speak the new
field contract and remain explicitly authored fixtures, not semantic evaluation.
Independent schema checks pass. Offline preview of the saved UK request groups
44 targets into14 fields; its compact model-facing user payload is about55KB versus
92KB previously (not a live token/cost or quality result). No API calls, automatic
retries, source/index writes, app restart, MEMORY append or Git sync.

**Restart/next boundary:** restart the existing localhost:8520 Streamlit app to load
this code. Restart is not execution permission. Owner then reviews/retests; live
field-rewrite compliance and semantic quality remain unverified by offline tests.

---

## M2-D052 — Market-independent revision convergence, November 10, 2026

**Decision:** give every package revision the same explicit avoidance guidance and
current flagged field locations; compare requested phrase occurrences after the
Writer returns, then retain the existing fresh independent Reviewer pass.
**Authority/status:** owner approved this bounded implementation on November 10,
2026; implemented offline, owner review pending. No new inference, retry, cap,
market eligibility, pipeline, approval or publication authority.
**Rationale:** saved UK V3/V4 received the right field and human requests but
returned surviving wording. Human revisions lacked the automatic pass's explicit
scanner patterns. Fresh Reviewer omissions made surviving issues disappear.
**Alternatives:** relying on fresh review alone loses prior requests; replacing
text deterministically would author copy; additional Writer loops consume calls.
Neither alternative was adopted.

`prepare_call` now provides `full_avoid_list`, `current_flagged_locations`, exact
`requested_phrase_changes` and a single-response self-check to either origin.
The existing evidence projection, original validation, prompt/model bindings and
fresh Reviewer input scope remain. The flags include current scan occurrences
(with disposition) and semantic findings, including unresolved earlier requests.

The existing revision handler compares source-verified field/phrase spans with
the admitted response and records `revision-resolution-vN` in the existing ledger,
bound to its exact package hash. Repeated occurrences are aligned through field
edits, including shifted offsets, capitalization and partial removal. Results are
**Unresolved** or **Wording changed; meaning requires review**, never automatic
claims of a successful semantic fix. Freeform notes still reach the Writer but
are not claimed as mechanically verified phrase requests.

Unresolved occurrences become clearly attributed request findings in the human
review UI even when the fresh Reviewer clears or omits them. The original AI
assessment is unchanged. The summary and detailed results remain visible if the
fresh review is not ready. Human keep/accept-as-is, evidence/launch controls and
revision cap remain. No automatic retry or additional model pass was added.

**Verification:** 443 harness + 111 UI + 114 root tests PASS in an isolated copy,
using the existing UI interpreter for harness/schema checks (the foundation
interpreter lacks jsonschema). No install or dependency/lock change. Six new tests
include sanitized saved V3/V4 blog shapes, ignored rephrases, partially removed
repeats, path/case/offset mapping, a Reviewer omitting a surviving phrase, complete
and pending-review UI, and historical-report absence. Both origins are exercised
end to end in US/UK; pure phrase tracking is identical for US/UK/IN. Existing India
drafting eligibility remains gated; no India end-to-end generation is claimed.
Focused checks were rerun after final presentation/test refinements. Saved UK V4
passed authoritative binding and read-only AppTest with zero socket connections.

The current UK V4 and its protected artifacts are unchanged; historical runs are
not retrofitted with a new ledger report. It remains unapproved with 3/3 revisions
used. Existing human editing/rescan and explicit as-is approval remain available;
no V5 Writer call is unlocked. Corrected model-authored prose would require a new,
separately authorized Writer call. New checks expose surviving requests for future
revisions; offline wiring does not establish live semantic convergence.

No service restart, live model/service call, Git sync or MEMORY append. Stop for
owner review. Earlier results below retain their historical scope.

---

## M2-D048 — Required-only review and protected-scan refinement

Owner direction, November10,2026: required decisions only in the card stack;
optional findings collapsed and never required. Extend future automatic refinement
to protected scan hits and provide the full avoid-list. Offline verification,
then re-review the exact saved V2 without a Writer call. No Git publication.

**UI:** the existing must_decide predicate selects stack/progress/recap cards.
Advisory notes appear inside a collapsed `N optional suggestions ›` section, with
optional screened hints, sentence previews, full-draft links and choices. Ignoring
that section never blocks approval/revision. Existing decisions are not silently
created or applied; no maintained pipeline or extra page was introduced.

**Harness:** new immutable package executionv13/revision promptv5 adds protected
scan hits as independent rewrite targets, even if the Reviewer cleared them or
rated them advisory. They remain conservative scan matches, not fabricated
Reviewer findings. The revision input contains every format's configured Avoid
line, universal prohibitions, link restriction and exact shared scan patterns.
The scanner and model input use the same pattern builder; no competing avoid-list.
Exact binding checks prevent target tampering. One pass, shared cap3, paired
reservation and human-only keep/approval rules remain unchanged.

**Same-pass interpretation:** the Writer is told to inspect and rephrase new
matches before returning its single response. The harness then deterministically
scans that response; new protected hits are included in the SAME cycle's fresh
Reviewer input and remain human decisions. A finished Writer call cannot receive
its later scan results without another call. No extra Writer loop, automatic
clearance or silent text replacement was added. This future Writer behavior has
only offline wiring evidence in this checkpoint, not a new live-generation result.

**Preservation:** v12 and previous bindings/prompts remain intact. The current V2
retains its v12 policy and exact package/evidence hashes. A new consumed run-bound
owner grant permits this one Reviewer-only command; repeat execution under that
grant is rejected. It never routes through automatic refinement or the controller.
No old grant is transferred to new v13 writing. Models and backend content/evidence/
launch validation remain unchanged; no dependency install or corpus/index changes.

**Verification:**620 offline tests PASS (412 harness+96 UI+112 root), including5
new harness tests and1 new UI test. Covered protected-only triggering, complete
avoid-list equality, current-only postscan, new occurrence vs shifted-offset
classification, no extra Writer loop, same-V2 recheck/replay, required-only stack
and collapsed optional notes, optional preview/choice preservation. Existing
advisory-only trigger test now explicitly isolates absence of protected hits;
UI navigation tests follow the required stack. No validator weakening.

**Actual recheck:** same USrun `b61fab9e-e853-4666-b667-610ea6c64e03`, Version2; complete protocol review,
3 required cards and8 optional suggestions.
5 valid blocking findings remain;4 unverifiable findings excluded individually and
shown as a warning. This is human-review readiness, not factual/content acceptance.
ONE Qwen Reviewer call, ZERO Writer/revision/controller/research calls. Package copy,
evidence and revision count remain unchanged (1of3 used byagent). New usage estimate
USD0.0020731; existing shared USD1 ledger remaining USD0.6595278.
These are usage estimates, not billing-console reconciliation. Original captures,
V2 text, prior review and owner decisions remain protected; current pointer now
references the new review. No new wording choice, approval or publishing action.

Saved actualV2 AppTest passed all display checks with zero network/state changes.
815 original protected files checked: only the authorized current pointer and
budget ledger change during live re-review. No workspace dependency, MEMORY edit
or Git staging/commit/push. App8520 reloaded; stop for owner inspection at
Current run → Review. Native Safari inspection confirmed three required cards and
the collapsed eight-optional section; expanding exposes the optional-only caption.
No decision, revision or approval control was activated. Screenshots:
[Required stack](screenshots/d048/required.jpg) ·
[Collapsed optional section](screenshots/d048/optional.jpg).

---

## M2-D047 — One automatic blocking-only refinement

**Authority:** owner approval November 10, 2026. Implement in the existing harness,
offline verification first, then exactly one fresh live US run, USD1.00 ceiling,
stop at human review. Protected phrases may be rewritten automatically; only the
human may grant keep clearance. Agent and human revisions share the three-revision
cap, and each revision's actor is displayed. No Git publication authorized.

**Implementation:** same FoundationSession/LangGraph. The harness checks validated
Reviewer blocking findings after required review, reserves both revision Writer
and fresh Reviewer atomically, then routes one correction through the existing
revision adapter. Advisory/cleared/scan-only findings do not trigger the pass.
Incomplete reviews hand off rather than speculate. Exact original evidence,
launch restrictions, current-version bindings, source permissions and budget
validation remain. The automatic permission contains only blockers for correction;
no human keep decisions, content acceptance or publishing permission are created.
The second review sees only its new version. Remaining protected scan hits are
human decisions even if the model clears them. No additional autonomous pass,
including after later human revisions; attempted/failed calls still consume limits.

New immutable package execution v12 binds the policy. v11 and earlier inputs,
prompts and authorizations remain reconstructable; existing grants default to no
automatic refinement. A new explicit private grant enables this test. Models,
prompts, tone policy, output schemas and validators remain as accepted in D046.
Controller/Reviewer: Qwen/Qwen3-30B-A3B-Instruct-2507. Writer/revision:
NousResearch/Hermes-4-405B. No new dependency, pipeline or framework.

**Activity/UI:** displays who used each revision (for example `1 of 3 used · by agent`).
`Agent fixed N blocking issues` counts removed quoted findings only after a complete
fresh review with no remaining blocker in that field. Otherwise reports refinement
checked, preserving remaining issues. This is bounded review evidence, not a claim
of universal factual accuracy. Existing approve-as-is human controls remain.

**Offline gate:**614 tests PASS (407 harness +95 UI +112 root), including ten new
harness and two UI tests. Covered: one automatic pass, no advisory/no-grant trigger,
paired reservation and denial, unknown/closed budget, failed revision accounting,
remaining blockers, subsequent human revisions sharing cap3, exact-V2-only review,
permission tampering, reserved harness-ID spoofing, incomplete review, protected human-only keeps, replay and
truthful Activity/actor labels. Existing saved approved USV2 restored with zero
network; all745 protected baseline files were byte-identical before live execution.
Initial verification command mistakes (missing jsonschema in the harness-only
environment; missing PYTHONPATH for UI) were corrected using existing environments;
no package installation or validation relaxation.

**Observed integration correction:** the first live review returned28 valid blockers,
but a duplicated serialization of findings in the feedback string exceeded the
local12000-character feedback bound. No revision inference ran in that handoff.
The short direction now refers to separately supplied complete blockers instead
of duplicating them. A regression reproduces the denial and verifies same-run
continuation without research/controller/initial-Writer calls or counter reset.
The original denial and interim state/result remain protected; the single allowed
refinement is the first and only revision attempt. No source or rule was loosened.

**Live result:** `awaiting_human_review`, current Version `2`,
5 formats; complete review `True`;
5 validated Reviewer blockers remain. Automatic pass
status `reviewed`; 17 original
quoted blocking findings confirmed removed by the bounded check. Actual role
calls: {"controller": 4, "package_writer": 1, "package_reviewer": 2, "package_revision": 1}. Total revisions consumed: 1.
Human approval remains false, publishing disabled. Full requests/responses, usage,
source events, both versions and exact findings remain protected at
`data/generated/live-package-d047-auto-refine-us`. No additional fresh run was started.

**Costs:** new run usage estimate USD0.0464754; shared ledger
remaining USD0.6616009 under its original USD1.00 ceiling. The prior
accounted balance was retained, never reset. Estimates use provider token usage;
these are not a billing-console reconciliation. Unknown charges retain reservation.
Read-only official account/public catalog checks confirmed both models active and
unchanged relevant prices/context; the public catalog required a normal browser
user-agent after HTTP403/1010. Production transport remained unchanged and its
read-only account check returned200. Catalog snapshots are in the protected store.

**Handoff:** open app8520 → Current run → Review; Package contains all five drafts.
Original approved USV2 and historical approval receipts remain protected; prior
current pointer is backed up separately. No source documents, claim mappings,
Pinecone index, credentials or MEMORY changed. No Git stage/commit/push. Required
code/config/tests and this record are canonical; no runtime dependency on workspace.
Stop at human review. New live quality is one example, not a reliability benchmark.

**Review limitations and UI verification:**4 unverifiable findings were dropped individually; valid findings remain. The current Review has11 phrase groups, including3 protected must-decide groups. This is not content approval. Socket-blocked AppTest restored the actual liveV2 across Activity/Review/Package without state or call changes. Native Safari verified Version2, agent attribution and the17-fix Activity line. Screenshots: [Review](screenshots/d047/review.jpg), [Activity](screenshots/d047/activity.jpg). No wording decisions, approval or later version were created during UI checks.

---

## M2-D046 — Shared per-format tone policy and measurable checks

**Decision/authority:** explicit owner direction, November 10, 2026; no links in
all five draft formats, with citation/source URLs kept separately. Status:
implemented; offline verification PASS; owner review pending. No live validation
or Git publication authorized by this checkpoint.

**Source of truth:** [voice_policy_v2.json](../../data/templates/gtm/voice_policy_v2.json).
Contains core tone, each format's Voice/Tone/Avoid/short label, structural rules,
advisory measurements, all-format prohibitions and scan additions. The existing
voice-policy mechanism is extended; immutable v1 remains a historical binding.
New packages derive both voice modes and measurable rules from v2. Exact policy
hash is bound through package_execution_v11, authoritative input and package
metadata. Raw original templates remain unchanged; current model-facing template
guidance/schema derives from the bound policy. No extra framework or dependency.

Writer v3, Reviewer v7 and revision v4 receive the identical policy via
writer_brief.tone_policy. Prompts refer to it rather than duplicating the tone
spec. Reviewer judges each draft against its own Tone line; findings remain
model judgments, statuses remain application-owned. Notes are lower-trust creative
steering and cannot change the bound policy, evidence, launch gate or budgets.

| Enforcement | Rules |
|---|---|
| Blocking structure | Exact supplied LinkedIn CTA; exactly3 LinkedIn hashtags; exactly3 ad concepts;2–3 blog sections; no copy links in any format; no case-insensitive standalone we/our in any campaign-brief field. Existing3 messaging pillars also stays hard. |
| Advisory only | All configured word/character targets and exclamation counts:0 in brief, at most1 in LinkedIn/email/blog, at most1 per ad concept. Code computes and displays warnings on Package; these never block approval. |
| Semantic review / scan | Format tone, hype/superlatives, distinct angles, audience-hypothesis language, unsupported claims and all Avoid categories. Scan matches are candidates, not semantic proof; existing protected categories still require human clearance. |

Existing citation validation, original evidence verification, launch restrictions,
link prohibitions and budget controls remain in force. Factual blog section
headings can inherit only their own body's citations; other factual fields keep
their own references. Creative headings do not acquire empty citation entries.
Structural failures cannot be misclassified for the missing-citations-only retry.
Source URLs remain available as separate evidence, never prohibited draft copy.
The v2 scan adds uncovered Avoid terms (including standalone today and full
phrases) from config; historical scan modes remain reproducible. Reviewer hints
are screened against the current additions. No regex claims to identify every
superlative or determine support; contextual review remains necessary.

**Read-only UI:** Prepare has Tone = Warm, factual, lightly nostalgic, with
per format › expanding all five tone lines. Existing Notes remains the only
steering field. Package shows each short tone label next to its deliverable and
plain advisory captions. No tone selectors. For historical packages, labels are
explicitly current guidance; original policy, review and approval are retained.
Editable per-format tone presets are a future feature, not implemented/authorized.

**Preservation:** historical config/prompt files and all approved datasets remain
unchanged. Existing packages reconstruct their original input/schema/advisories
and retain exact approval bindings. Only a consumed, run-bound v10 authorization
may restore that original scope; it cannot start a new run or call the new policy.
Transport verifies the authorized package/prompt binding before dispatch. New
policy scope does not inherit old spending approval. Models and budgets unchanged.

**Verification:602 offline tests PASS** (397 harness +93 UI +112 root), including
12 new tests. Checked exact policy/schema, Writer/Reviewer/revision input equality,
structural rejection, no-links across5 formats, separate citation URLs, Notes/
policy-tampering boundaries, advisory approval, precise measurements, risky terms,
required-review behavior and historical authorization isolation. JSON Schema check
PASS locally. The tiny final authorization input guard also passed the26-test
mocked live-adapter subset. Mocks prove wiring/validation, not live tone quality
or hosted-schema compatibility. Native Safari screenshots use only authored
fixtures, with socket connections blocked in the temporary preview process:
[Prepare tones](screenshots/d046/prepare-tones.jpg),
[Package tones/advisories](screenshots/d046/package-tones.jpg).

Actual saved USVersion2 was separately restored and revalidated in socket-blocked
AppTest: same state/capture/evidence/decisions/approval/accounting, zero network.
745 protected file hashes unchanged, including credentials, sources, private runs,
ledger, approved receipt and MEMORY. Syntax/whitespace checks PASS. Required code,
config and tests are canonical; no runtime dependency on workspace or the temporary
visual launcher. Main8520 was not restarted during this offline checkpoint;
fixture-only preview8524 shows the new screens. No source reads/writes, inference,
new approval/revision, Pinecone operation, dependency install or Git sync occurred.
Stop for owner review; further model verification is separately authorized work.

---

# M2-D024 — Writer output, recovery and run experience

November 9, 2026 · **REVIEWER PROBE REJECTED; OFFLINE STREAM FIX VERIFIED; STOP FOR OWNER REVIEW.**
Owner approved the bounded batch and six refinements. Calendar targets were then
superseded by completion ASAP. This report records results, not content acceptance.

## Exact live role mapping — verified November 9, 2026

Owner requested stating and recording each role before any live run. Current
`nebius_gtm_package_v2` profile and constructed live adapters agree:

| Role | Exact Nebius model ID | Current adapter wiring |
|---|---|---|
| Controller | `Qwen/Qwen3-30B-A3B-Instruct-2507` | `ResearchModel` uses `live_research.MODEL`; its transport is role `controller`. The constant matches the profile. |
| Writer | `NousResearch/Hermes-4-405B` | `ContentCall`, stage/transport `package_writer`, takes the exact model from the live profile. |
| Reviewer | `NousResearch/Hermes-4-405B` | A separate `ContentCall`, stage/transport `package_reviewer`, takes the exact model from the live profile. |
| Revision Writer | `NousResearch/Hermes-4-405B` | Separate `ContentCall`, stage/transport `package_revision`. |

All use `https://api.tokenfactory.nebius.com/v1/chat/completions`. Reviewer separation
means a separate call, prompt and assessment; Writer and Reviewer currently use the
same model. Testing Qwen's Writer schema in the probe does not select it as the
application Writer. No model configuration or routing was changed by this check.

Evidence: [SHA-bound live profile](../../data/templates/gtm/live_package_profile_v2.json),
[role construction and transport checks](../../src/launchlens/live_package.py),
[controller request model](../../src/launchlens/live_research.py), and
[content request model](../../src/launchlens/content_review.py). Verified profile
SHA-256: `df54a09981443fa58628c32d0fd3fc4ad1105efbbdabfaceefffc8e4ec711381`.

Fresh verification constructed the actual live adapter classes with injected mock
transport, safe fixture tools and fake credentials. Exact role/model/stage assertions
PASS; zero provider/source requests and no real credential loading. This confirms
wiring, not current hosted compatibility. `hosted_schema_qualified=false`; no full
live run occurred during that role check. The later authorized schema audit and
Qwen-then-Hermes probes are completed in the next section; full live execution
remains outside this checkpoint.

## Corrected schema audit — November 9, 2026

Owner authorized an offline audit followed by Qwen then Hermes, one corrected
full-package request each; conditional one Hermes channel request only on its full
failure and remaining budget. Zero automatic retries/repairs; stop after probes.
This does not authorize a whole-agent live run or unlock the live profile.

### Provider keyword inventory (before paid calls)

Audited actual `package_schema()` for Writer/revision, `package_schema(True)` for
Reviewer, and all five channel schemas. Counts below are Writer / Reviewer keyword
occurrences, counting keyword positions rather than field names or enum values.

| Keyword | Count W / R | Support evidence before corrected probes | Provider action |
|---|---:|---|---|
| `type` | 75 / 76 | Supported in official examples | Keep |
| `properties` | 18 / 16 | Supported in official examples | Keep |
| `required` | 18 / 16 | Supported in official examples | Keep |
| `additionalProperties` | 18 / 16 | Supported (`false`) in official example | Keep |
| `items` | 16 / 15 | Supported in official array example | Keep |
| `enum` | 5 / 25 | Supported in official example | Keep |
| `minLength` | 41 / 20 | Supported in official example | Keep |
| `minItems` | 11 / 5 | Undocumented keyword compatibility; unverified, not proven unsupported | Keep for authorized actual-schema probe; backend checks regardless |
| `maxItems` | 2 / 15 | Undocumented keyword compatibility; unverified, not proven unsupported | Keep for authorized actual-schema probe; backend checks regardless |
| `uniqueItems` | 5 / 5 | **Unsupported**, observed Qwen HTTP400 grammar rejection | **Omit from provider schema only** |

`pattern`, `maxLength`, `$schema`, `$ref`, `minimum`, `maximum`, `const`, `anyOf`,
`oneOf`, `allOf`, `default`, `description`, `format` and `title` are not schema
keywords in these actual schemas. `format` is an output property name. We make no
support claim for unused keywords. Request wrapper keys are `type=json_schema`,
`json_schema`, `name`, `strict=true`, `schema`, as in the official structured-output
example. They are not constraints within the JSON Schema itself.

The [Nebius structured-output guide](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
shows the seven retained keywords identified above and the strict wrapper. It does
not enumerate a comprehensive dialect. The [chat API reference](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion)
contains contradictory response-format wording (object/text only). Consequently,
we record documentation uncertainty and test the exact deployed models; we do not
invent support guarantees from OpenAI compatibility. This audit found no additional
**confirmed unsupported** keyword beyond `uniqueItems`. Its existing provider-only
projection already removes that keyword. No backend schema or validator edits.

### Rules outside provider enforcement

- Omitted `uniqueItems`: duplicate claim IDs still fail backend checks for both
  Writer and Reviewer. Until hosted qualification, array cardinality is also
  explicitly unverified at provider level; exact three ads/pillars and nonempty
  citation ID lists remain backend checks.
- Whitespace-only strings fail backend `.strip()` checks; JSON Schema `minLength`
  measures raw length. Reviewer field text has a backend 1,200-character ceiling
  absent from its provider schema. Path syntax and resolution to an actual string,
  and one reference per content field, are backend checks.
- Writer claim IDs are free strings in the schema. Backend independently verifies
  complete public evidence, registered eligible IDs, source mappings, authority,
  digests, resolved qualifications and objective coverage of PROD-002/PROD-003.
  No ID presence check proves semantic grounding.
- Exact LinkedIn CTA, prohibited links/wording, narrowly defined uncited factual
  fields, original launch/registry/market/date permissions, voice-policy bindings,
  package completeness and application-owned metadata remain backend controls.
- Reviewer requires each of six dimensions exactly once, exact quotations from the
  cited draft field, nonduplicated findings, eligible evidence, and consistent
  blocking findings versus dimension verdicts. Schema length/enums alone cannot
  establish these cross-field conditions.
- Run/draft/evidence/creative-anchor identity, stale-review protection, one explicit
  revision/retry, cumulative attempts/spend, human acceptance and publishing remain
  harness-owned. Editorial length/hashtag preferences remain advisory. Semantic
  entailment, tone and misleading claims still require real review; neither schema
  validation nor this probe asserts those checks have passed.

### Offline gate and command

Existing **jsonschema 4.26.0**, **Draft 2020-12**, in `tools/ui/.venv` independently
checked all seven backend schemas and seven projected schemas: **14 PASS**.
Schema diff confirms only `uniqueItems` removed (five Writer / five Reviewer
locations; one per channel), with every field/type/required/other constraint intact.
A valid nested fixture passes; quoted format JSON and empty citation IDs fail;
duplicate IDs pass the projected schema but fail the unchanged backend schema.
Nine focused offline tests PASS, including no network, original failure capture,
independent results, conditional single fallback, immutable guard and retained-cap
blocking. These fixtures do not prove hosted enforcement or content quality.

```sh
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python tools/probe_package_schema.py --audit
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python -m unittest discover -s tools/agent_foundation/tests -p test_schema_probe.py -v
```

New owner-scoped execution guard: `data/generated/d024-schema-audit-probes-v2/`.
Old v1 guard/receipts are preserved. Existing USD0.18 cap includes the old unknown
HTTP400 reservation **USD0.0278528**; screenshot USD0.08 is aggregate usage and the
owner confirmed it has no separate charge. No release or zero-charge assumption.
Each new request reserves full model-context input plus 8,192 capped output tokens
before dispatch; known usage settles that request, unknown billing retains its
reservation and stops. No second model/fallback if the next reservation cannot fit.
No automatic retry. Prepared execution (authorized only for this recorded scope):

```sh
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python tools/probe_package_schema.py --execute-authorized-audit-v2
```

The request uses the actual production schema with a small canonical qualification
brief, unchanged package Writer instructions, temperature0, both output caps8192,
stream=false/store=false. It is a schema probe, not the full accepted research
context, operational source check, Reviewer test or content acceptance run.
Common messages and per-model request/schema hashes are saved before dispatch;
complete raw responses are saved before parsing. Qwen is only a comparison probe:
application roles remain Qwen controller, Hermes Writer/Reviewer/revision.

### Corrected hosted outcomes — completed; stopped after two calls

Current public catalog rechecked immediately before inference: exact two model IDs,
context limits and uncached prices unchanged. Catalog SHA-256:
`75818db5c912d5249da37ada7349e0014cc66f996cd39b7c84bce7f746f1c157`.
Qwen:262,144 context,$0.10/$0.30 input/output per million tokens;
Hermes:131,072 context,$1/$3 per million. [Official catalog](https://tokenfactory.nebius.com/api/public/models_info).

| Model | HTTP / request → response shape | Provider schema / original backend schema | Probe reference checks | Actual usage in / out | HTTP latency | Usage-based estimate USD |
|---|---|---|---|---:|---:|---:|
| Qwen/Qwen3-30B-A3B-Instruct-2507 | 200; five nested objects → five nested objects | PASS / PASS | **REJECTED**: campaign_brief reference uses `content.audience_hypothesis`; path must be relative to content (`audience_hypothesis`) | 2,063 / 1,835 | 30.839045s | 0.0007568 |
| NousResearch/Hermes-4-405B | 200; five nested objects → five nested objects | PASS / PASS | **PASS**: valid field paths, complete eligible ID references | 2,053 / 977 | 23.27346s | 0.004984 |

Hermes HTTP latency above is taken from the receipt, while total validation-inclusive
elapsed time is23.278946s. Qwen total elapsed30.845017s. No empty citation arrays,
duplicate content-field references or ineligible IDs in either returned package.
Both responses finish_reason=stop, untruncated/unredacted. Exactly two calls,
one per model, zero retries/repairs. The conditional channel probe was **not needed
or executed**. No controller/Reviewer/full-agent calls were made in this checkpoint.

Request: `POST /v1/chat/completions`, two messages, same system/user text for both
models, `response_format.type=json_schema`, strict=true, actual five-format projected
production schema, temperature0, max_tokens8192/max_completion_tokens8192,
stream=false/store=false. Each output format is an object with `format`, `content`
and `claim_references`; no escaped JSON string format values. Only model ID differs
between the two requests. Provider tokenizers report different input counts.

Common logical-messages SHA-256:
`dc7c3e69087a44ae7058a34667b13b29993b1f138d41cd90f425834045058b90`.
Provider Writer schema SHA-256:
`9ac65a76cefdbdf7831cc18552eed9a5a14ec84979f0c1ba42ab8c03d94108e0`.
Qwen request SHA:
`13e9e23427411d0ac5a249e805520cfd210fcce654b4dd3fa76690d83bc3b3ae`.
Hermes request/response hashes are in the protected identity receipt and summarized
in the exact identities below. Full source payloads/credentials are not published.

The provider accepted the complete retained keyword set, including minItems and
maxItems, on both tested models. Actual samples satisfy those constraints; this
proves acceptance and sample conformance, **not enforcement of every possible
invalid output**. Schema keyword documentation uncertainty remains recorded above.
Qwen illustrates why valid JSON Schema does not establish valid evidence bindings.

Probe backend checks use unchanged `validate_draft` against canonical safe evidence
plus both objective IDs for every format. They do **not** execute full operational
`admit_package`, authoritative source reads, live Reviewer, human acceptance or the
entire autonomous workflow. Full original runtime authority remains independent
of any model projection; its code/templates/prompts are unchanged.

**Spending:** new known-usage estimate **USD0.0057408**. Retained old unknown HTTP400
reservation **USD0.0278528**. Total accounted **USD0.0335936**; unreserved remainder
**USD0.1464064** of the existing USD0.18 ceiling. New Qwen reservation0.0278528 and
Hermes reservation0.147456 were each admitted sequentially before dispatch; released
only against that request's consistent usage. No assumption about prior billing,
cache discounts, console rounding or extra credit. These are usage estimates, not
an isolated console invoice. The old reserve is still held.

**Writer route decision:** retain the owner-selected **Hermes full-package Writer
route** for a separately authorized integration test; no need to activate the split
fallback based on this probe. Qwen remains controller. Reviewer/revision remain
separate Hermes calls, but the Reviewer schema has **only offline qualification**.
No profile flag, model routing or full-run authorization was changed. We have not
accepted the marketing content or demonstrated a complete live package review.

**Content inspection (human-readable observations, not fabricated Reviewer output):**
Hermes's email says “Try it today”; its blog says “sure to become a new favorite”;
positioning says “unique twist”. These need review for implied availability/urgency,
unsupported preference and differentiation. Its LinkedIn body references both
eligible facts correctly, while word counts remain advisory. Schema success does
not clear those substantive concerns. No regeneration/correction performed.

Complete raw responses, exact requests, schema audit/removal paths, reservations,
usage/timing and identity receipts are protected under
`data/generated/d024-schema-audit-probes-v2/` (0700 directory/0600 files).
`readable-returned-drafts.md` in that directory renders every field/reference from
both complete candidates without requiring JSON inspection. Originals remain exact.
The execution guard is consumed; it must not be deleted or reused.

Fresh verification: **278 PASS /1 SKIP** in279 agent-environment tests. The skipped
independent-jsonschema test was run using the already-installed UI validator and
**passed** in the **9/9 focused UI-environment probe tests**. No packages installed;
backend/schema/template/prompt/evidence/history/credential/MEMORY hashes unchanged.
No full live run, LangSmith, source writes, dependency changes or Git publication.


## What changed

The same FoundationSession/LangGraph now streams updates into Streamlit `st.status`
in its normal script. The existing run view was replaced in place: working,
waiting, ready and stopped; actual action purposes and source names; per-format
state; collapsed technical details. No background worker, new pipeline or dependency.
A single atomic package call truthfully marks all formats Writing together, rather
than pretending separate calls happened. Unsupported/unregistered public research
is not displayed as a model decision to skip. No fabricated trace links.

Versioned v2 controller/Reviewer prompts and package/live profiles preserve every
v1 file. Package controller actions include a bounded business-purpose `why`;
the Reviewer explicitly examines uncited fields too. The Writer text, five content
templates and accepted US context projection are unchanged. Narrow field coverage
rejects the preserved uncited “bringing … cherry experience” hook and clear explicit
product assertions; ordinary discover/introducing/new wording alone passes. These
checks are not a semantic entailment classifier. Original complete evidence still
drives backend validation independently of the model input.

Explicit Try again replays only the failed Writer action once on the same graph,
retaining research, original candidate/diagnostic, call/search counters and spend.
The corrected candidate still faces every backend check and separate review. No
automatic repair, citation cleanup or retry. Unknown transport/billing, tool failure,
missing permission, exhausted budget or a second Writer rejection cannot retry.
A recovered rejection is preserved as a safe native tool-history result so the
controller can continue; it is never relabeled successful.

UK uses the existing interrupt/Command(resume=...) on the same run. Choices are
availability-free drafting, recheck readiness, or stop. Frozen Missing yields:
“Readiness still shows availability unconfirmed. Continuing without availability
wording.” The operational verdict remains Clarify, promotional_draft_allowed stays
false, and a separate exact-request/launch-bound permission allows only availability-
free drafts when the other three checks are Approved and no other condition exists.
The US-only projection is never forged for UK: UK retains complete scoped context,
including caveats/conflicts. India Hold and publishing=false remain enforced.

## Historical first hosted probe: actual result and stop

Exactly **one** generation request was attempted: Qwen3-30B-A3B-Instruct-2507,
production package schema, 8,192 completion cap, zero retries. Nebius returned
HTTP400 in **0.85002s**:

> Grammar error: Unimplemented keys: ["uniqueItems"]

No model output or usage was returned. Known usage cost cannot establish this
request's billing. The **$0.0278528 reservation remains retained** against the
$0.18 batch ceiling. Unknown-billing policy stopped all further paid work: Hermes
and the conditional channel probe were **not called**. No whole-agent live run.

Private immutable receipts: `data/generated/d024-schema-probes-v1/` (0700 directory,
0600 files), request identity
`c1ee2f4481dab52c8d44c54fcce4ffb73e75e755d091cd92ae9325c5959bfee2`.
The original request/response remain exact; the maintained command now prepares the
corrected provider dialect and cannot reuse its consumed output guard.

The existing role transport now supplies `response_format=json_schema`. Its provider
projection omits only unsupported `uniqueItems`; backend duplicate checks remain.
It does not unwrap quoted JSON, delete citations or change accepted content schemas.
[Nebius structured-output documentation](https://docs.tokenfactory.nebius.com/ai-models-inference/json)
describes this API, but the corrected dialect is **offline-verified only**. No claim
that Hermes accepts it, that every schema keyword is enforced, or that writing is
factually grounded. The agreed split fallback has not been activated or qualified.

## Verification

| Check | Actual result |
|---|---|
| Harness/adapter/probe tests | **274 PASS**, no sockets in offline tests |
| Streamlit tests | **41 PASS**, including four states, inline same-run UK, rejected retry, actual paused graph continuation |
| Existing root tests | **111 PASS** |
| Total | **426 PASS**, fixture/mock coverage, not live quality |
| Known-usage mocked live recovery | 5 failed-attempt calls → retry + review =8; explicit revision + fresh review =12; original failure and costs retained |
| UK | Same run reaches five-format fixture review, Clarify retained, availability excluded; recheck failure stops |
| Stop | No model call from an untouched created run; next-action permission removed |
| UI visual inspection | Safari dark desktop: working, UK waiting and inline choices, package ready, injected Writer stop; actual feedback → fresh v2 assessment |

Visual inspection used the same renderer and actual offline graph checkpoints,
not fabricated statuses. Screenshots were rendered in the conversation. The working
fixture pauses before the selected Writer action; it is explicitly a simulation,
not evidence of live autonomy. AppTest also covers this checkpoint continuing into
review. Mobile CSS remains responsive, but no mobile-device certification is claimed.

Protected baseline hash check: 172 source/generated/private/credential/memory/lock/
v1 prompt/profile files unchanged at inspection. No source writes, package installs,
workspace runtime dependency, Git staging/commit/push or MEMORY append.
Clean canonical checkout also passes **274 harness +41 UI tests** without workspace,
private/generated artifacts, .env or approved PDFs. Final Python syntax, local links,
ignore rules, credential exclusion and Git whitespace checks PASS; staging is empty.
Safari also verified the final stopped-state action alignment and explicit retry
reaching fixture review. No real mobile-device check was performed.

## How to inspect locally

```sh
LAUNCHLENS_UI_MODE=offline PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python -m streamlit run streamlit_app.py
```

Open http://127.0.0.1:8520. Keep Demo simulation selected. US Standard review shows
five drafts and fixture findings; Review package reveals the content. Optional
feedback requests one revision and fresh review. UK pauses inline. US Bad Writer
response tests Try again; Bad Writer twice tests the final stop. These are authored
fixtures, never a fallback from live failure.

Optional offline visual launcher (same screen, not an additional product route):

```sh
tools/ui/.venv/bin/python -m streamlit run tools/preview_run_states.py --server.port 8521
```

Use `?case=working`, `waiting`, `ready`, or `stopped`. No credentials/private files.

Offline commands:

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python -m unittest discover -s tools/agent_foundation/tests
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python -m unittest discover -s tools/ui/tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests
```

`tools/probe_package_schema.py` defaults to no network; its `--execute` guard is
consumed. Do not delete that guard or replay the command as new authorization.

## Original batch handoff boundary (historical)

The following preserved handoff predates the corrected audit/two probes above.
Its no-whole-run boundary still applies; Writer qualification status is superseded
by the actual corrected results, without claiming Reviewer/content acceptance.


Inspect the working UI and offline results. Next paid work needs explicit owner
approval after accounting for the retained probe reserve: one corrected Hermes
schema probe before a fresh whole-package run. If its full schema fails with known
billing, the pre-agreed brief/channel fallback requires the bounded channel probe.
No automatic budget expansion or further parameter experiments.

The new role plan keeps **12 total calls /4 searches**: 7 controller, 2 Writer
(including explicit formatting retry), 2 Reviewer, 1 revision. Worst-case reservation
is **$0.9051136** using published full-context bounds; **$0.92 is a proposal only**,
not authorization or expected spend. The old $0.80 authorization is consumed. The
v2 profile remains hosted_schema_qualified=false and live factory/UI stay blocked;
no private live authorization was issued. Smaller verified bounds could lower a
future proposal, but no optimization or unapproved assumption was adopted here.

LangSmith remains the next observability checkpoint after the core live gate,
followed by live acceptance, export and submission evidence. No calendar deadline,
trace, publishing permission or final model-quality acceptance is implied.

### Corrected probe exact identities

- Qwen/Qwen3-30B-A3B-Instruct-2507: request `13e9e23427411d0ac5a249e805520cfd210fcce654b4dd3fa76690d83bc3b3ae`; response `955069d9a59262f82df8b640671a53c1be4e37f461bbbfe3547304ba62ca0fae`.
- NousResearch/Hermes-4-405B: request `868d7a356f0a6fa64c4b4e633e99685e457a513737efd2d664d3309188303c04`; response `ff00ff31359587da03a7efbf3c9ee5407d3406c5ccd399c9a6d47a91a5b5c1cb`.

### Final preservation and regression note

403 preexisting files remain byte-identical to the pre-task snapshot, including
all backend/runtime validators, schema templates, prompts, profiles, source evidence,
old receipts, credentials, dependency locks and MEMORY.md. Nine existing files
changed: the probe command/tests, current report/plan/milestone/status pointers and
two continuity notes. New private outputs are ignored, permissions0700/0600;
credential-value exclusion, exact request digests, local links, empty Git staging
and diff whitespace checks PASS. No Week2 files changed.

One intermediate279-test run failed the existing
`test_stream_updates_observe_selected_actions` assertion looking for a pending
`generate_package` snapshot. Its13-test recovery module recheck PASS; final full
rerun **278PASS/1SKIP**, with the independent-jsonschema test separately PASS in
the9-test UI-environment suite. The earlier full run also passed. No graph/runtime
file changed. This is an observed intermittent progress-test failure, not a resolved
bug or a hosted schema failure; preserve it for the next UI/integration checkpoint.
No additional inference was made during verification.

## Owner-authorized Reviewer probe and offline stream correction — November 9, 2026

Owner explicitly authorizes exactly one Hermes Reviewer probe, using the preserved
Hermes package, production Reviewer schema/prompt, zero retries/repairs and the
remaining original USD0.18 cap. Separately authorizes offline diagnosis/fix of
`test_stream_updates_observe_selected_actions`. No full agent run or Git publication.

Pre-call checks: exact preserved Hermes request/response hashes verified against the
immutable identity receipt. Package hash
`d391a0ece822ab0efb722bd7b91b16d540d9c5a4d766acead903e78564c6a041`.
The unchanged package and original probe facts/qualifiers/source URLs/restrictions
are supplied in the production Reviewer message structure, with original Writer
instructions, existing common review criteria and computed editorial warnings.
This is an isolated review of that small probe brief, not a fresh Notion/Pinecone
research or operational-authority test. No requested-finding list or extra evidence
is added to the model input; phrase coverage is inspected after inference only.

Model `NousResearch/Hermes-4-405B`; exact SHA-bound production
`package_reviewer_v2.txt`; actual `package_schema(True)` (provider-only uniqueItems
omission, backend intact), strict JSON Schema, temperature0, both completion bounds
4096 as configured for the Reviewer role, stream=false/store=false. Offline
Draft2020-12 metaschema checks PASS. Prepared request SHA
`27499450ad119a88518e237bc2f7ba97696048469b965468674c352bd99a935e`.
New immutable guard `data/generated/d024-hermes-reviewer-probe-v3/`; one request only.
Probe-only timeout120s accommodates the larger assessment; shared transport default
stays45s, overrides bounded to180s. No automatic retry or output-token increase.

Prior accounted USD0.0335936 includes old unknown HTTP400 reserve0.0278528 and
settled Writer-probe estimate0.0057408. Reviewer worst-case full-context reservation
USD0.139264 gives maximum accounted USD0.1728576, below0.18. Known consistent usage
will settle only this request; unknown transport/billing retains its reserve and
stops. Complete raw response precedes parsing. The unchanged backend assessment
validator checks each format's dimensions, exact quote/path, eligible IDs, duplicate
findings and status consistency, separately from JSON Schema conformance.

Offline stream diagnosis: forced stale checkpoint reads reproduce the old failure:
10 real graph updates, Writer selection present in the streamed decide update but
absent from callback snapshots; final run still reaches human review. The old loop
read get_state separately after each update, without a synchronization guarantee.
The correction assembles a deep-copied observational view from the actual trusted
node update and previous view, with partial clarify/resume updates merged. Graph
checkpoints retain sole execution authority. Callback mutations cannot affect the
graph or later views. No permission/action policy or model decisions changed.
16 recovery tests PASS, including deterministic stale-checkpoint reproduction,
callback mutation isolation, UK interrupt/partial resume, retry/counter/India guards.
13 focused probe tests PASS with existing UI jsonschema, no network. Final regression
and actual Reviewer results will be recorded below; no content acceptance implied.

### Actual Reviewer result — one call; no retry

**JSON Schema PASS; backend acceptance REJECTED.** Hermes returned all five review
objects with schema-valid fields, types/enums and array lengths. Both the original
Reviewer schema and provider projection pass independent Draft2020-12 validation.
HTTP200, finish_reason=stop, untruncated/unredacted. 5,623 input /1,507 output tokens,
33.819689s through captured response/validation. Exact HTTP latency is recorded below.
New usage-based uncached estimate **USD0.010144**. Cumulative accounted within the
original0.18 ceiling is **USD0.0437376**, including the unchanged old unknown reserve
**0.0278528**; unreserved remainder **0.1362624**. Reservation0.139264 settled only
against this request's consistent usage. Console billing is not inferred.

| Returned finding severity | Count |
|---|---:|
| Blocking | **0** |
| Advisory | **9** |

These are **raw, rejected model findings**, not accepted review records. All nine
are editorial length suggestions: four short-format word-count advisories, three
long-ad-CTA advisories and two long-ad-body advisories. The model marks grounding,
qualifications, voice, tone and consistency pass across all formats, but marks each
completeness dimension needs_changes despite providing no blocking findings.

| Requested phrase | Present in the unchanged package | Reviewer flagged it |
|---|---|---|
| “Try it today” | Email body | **No** |
| “sure to become a new favorite” | Blog conclusion | **No** |
| “unique twist” | Campaign positioning and email body | **No** |
| “innovative” | Blog introduction | **No** |
| “Introducing” | LinkedIn body, email subject, blog title | **No** |
| “new flavor” | Audience hypothesis, email body, blog introduction | **No** |

Manual review of every rationale confirms no equivalent availability, preference,
uniqueness/innovation or novelty finding under different wording. In context,
“Introducing” alone need not be a factual violation, and hypothetical-audience
language is distinct from product claims. That nuance does not excuse the missed
availability/preference concerns. This sample does **not pass substantive Reviewer
qualification**; it does not establish model-family reliability either.

First actual backend rejection: `campaign_brief`, `invalid_reference`, `findings`.
All nine returned finding paths use `content` or prefixed paths such as
`content.body`, instead of a relative text-leaf path. Four claimed quotations are
word-count summaries absent from any draft field. The remaining five quotations
exist in the draft but still have invalid paths. Separately, all five
needs_changes completeness assessments lack the required blocking finding.
No path normalization, fabricated quote, severity change or other repair occurred.
The application rejects the assessment; no draft is marked reviewed or approved.

This is a real, isolated production-prompt/schema Reviewer call, **not** the full
controller→Writer→Reviewer autonomous journey, source refresh or revision test.
Exact original Hermes package/facts/qualifiers were preserved; no target-answer
hints were added. Full live gate remains closed and model routing unchanged.
Protected raw response, exact request/reservation/usage and human-readable output:
`data/generated/d024-hermes-reviewer-probe-v3/readable-review.md`.
No further paid call is authorized by this probe; no automatic retry/revision.

### Offline progress fix — actual verification

The intermittent test was not weakened or retried into acceptance. A forced
stale-checkpoint fixture reproduced its failure before the code change. The update
itself contained the selected Writer action; the separately read checkpoint view
did not. The callback now receives the accumulated actual node updates, deep-copied
for observation. Execution/checkpoint authority, policies, counters and decisions
stay unchanged. New tests force lag, attempt callback mutation and exercise UK
interrupt/partial resume. Existing replay, stop, India, retry and evidence tests pass.

- **16/16 recovery tests PASS**.
- Original formerly intermittent assertion: **50/50 repetitions PASS** after fix.
- **286/286 harness/adapter/probe tests PASS**, including independent JSON Schema
  checks in the existing UI environment (no skips).
- **41/41 Streamlit tests PASS**. No browser/server changes or dependency installs.

Final preservation/clean-checkout checks are recorded at handoff below. Earlier
intermittent-failure notes describe the pre-fix state. Reviewer rejection remains
open; the offline progress bug is fixed within this scope. No Writer regeneration,
new Reviewer prompt, validator weakening, full live run, Git publication or MEMORY
append was performed.

Reviewer HTTP latency: **33.819689s**.
Reviewer response SHA-256: `f786604ef0eaec17bc457f52f0bfd0e2909886aa931d0ca738ac80aeed5b8c54`.

Final handoff checks: clean canonical copy passes **286/286 harness tests** without
workspace, private/generated receipts, .env or PDFs. All **416 other preexisting
file hashes unchanged**; twelve existing files changed within the authorized probe,
stream fix/tests and documentation/continuity scope. Raw prior receipts, source
artifacts, prompts, backend schemas/validators, profiles, dependencies, credentials
and MEMORY.md are unchanged. New private artifacts0700/0600 and ignored; actual
credential-value exclusion, local links, request identity, diff whitespace and
empty staging checks PASS. No additional provider call, server/browser action,
Git staging/commit/push or dependency installation. Stop for owner review.

## M2-D025 — standing approval and current delivery goal

Owner approved new working rules and one complete live US run reaching Package
ready in the app, under USD1.00 total, no per-call check-ins. This supersedes previous
stop-after-probe/per-call approval boundaries for this goal. The canonical current
plan records decision, rationale, alternatives and scope. Implementation uses the
same graph, adapters and UI: bounded logged normalization; findings-only Reviewer;
code-derived statuses; nullable quotes for format findings; nonfatal incomplete
review; all five deterministic risky-phrase categories visible even when cleared.
Raw responses/history retained; no invented evidence, permissions or approval.

New SHA-bound v3 prompts/config/profile preserve v1/v2 bytes. Normalization does not
rewrite prose or add evidence IDs. Empty references are removed, then remaining
original backend evidence/field/launch validation still runs. Reviewer material
quote/path issues remain unaccepted raw findings, producing Review incomplete.
Invalid Reviewer evidence IDs remain a policy error. Technical Writer format failure
is a recoverable handoff, not a policy stop, with at most one bounded known-usage
retry under standing approval. Unknown transport billing retains reservation.

Private provisioning contract: build-standing-authorization.json and
build-budget-20261109.json in data/private/,0600. The existing RunBudget uses locked
per-call reservations in that ledger, shared across runs/processes; no workspace
runtime dependency. Opening0.0437376 includes retained0.0278528unknownreserve;
ceiling1.00, initialremaining0.9562624. Auth scope exactregisteredUS/date/objective;
no private old authorization or prior receipt overwritten. No keys in authorization,
budget ledger or docs. Current work/test/live results will be recorded below.

### M2-D025 actual completion — November 9, 2026, 16:21 PST

**GOAL REACHED: live US app visibly shows “Package ready for your review”.**
This is package availability for human inspection, not content acceptance or a
complete independent review. No further model calls were made after that outcome.

The actual browser Start agent path used the existing LangGraph/FoundationSession,
real Notion reads and Pinecone retrieval. The Qwen controller selected read_pmm_brief,
check_launch, search_product_evidence, generate_package and review_package. Hermes
Writer generated all five deliverables; a separate Hermes Reviewer call returned
findings. No scripted/fixture output was substituted into the live run. No revision
or second Reviewer call was made on this completed run.

| Verified item | Actual result |
| --- | --- |
| Scenario | CC-CHERRY-FLOAT / US / 2026-12-14 / flavor_discovery |
| Run | 888bd53c-d3b5-45cf-8d6a-b3bded59c777 |
| Controller | Qwen/Qwen3-30B-A3B-Instruct-2507, 5 calls |
| Writer | NousResearch/Hermes-4-405B, 1 call |
| Independent Reviewer | NousResearch/Hermes-4-405B, 1 call |
| Launch | Proceed from authoritative operational records |
| Deliverables | Campaign brief, LinkedIn, email, blog, three ad variations |
| Writer / Reviewer returned JSON schemas | Both PASS, zero JSON Schema errors |
| Writer backend admission | PASS against original authoritative evidence |
| Final state | awaiting_human_review; seven model calls, one evidence search |
| Human acceptance / publishing | Both false |
| Successful run model estimate | USD 0.0447171, conservative uncached-input pricing |

**Review remains incomplete.** Of 19 deterministic scan hits, 14 received valid
cleared judgments and five remained unassessed. All hits remain visible, including
cleared ones. Seventeen validated findings comprise 12 cleared judgments and five
advisories; the raw response has 20 findings. Campaign Brief contains two invalid
wording quote/path bindings; Ads contains one invalid scan judgment. Email, Blog
and Ads also have unassessed scan hits. LinkedIn has a complete structural review;
the other four formats display Review incomplete. Raw findings remain available.
Code derives six dimension statuses; the model cannot set those statuses. Neither
cleared scan judgments nor valid IDs prove semantic correctness. Novelty,
preference and differentiation wording still requires human inspection. No claim
of trustworthy Reviewer coverage or ready-to-publish content is made.

The actual Reviewer input contains risk_scan and no editorial_warnings. Actual
Writer and Reviewer requests and complete unmodified responses, hashes, usage,
latencies, source logs and state checkpoints are protected in
`data/generated/live-package-BUILD-US-b5dec476a9ff/` (gitignored, files0600).
The browser Review package control exposes all five tabs. No runtime dependency
on workspace exists. Source documents, credentials and historical receipts remain
unchanged.

**Earlier attempts preserved, not erased:** BUILD-US-b3c0f91a5074 stopped on an
overlong controller display-purpose string; BUILD-US-083513618735 produced five
drafts then stopped because review_package omitted its display-purpose string.
Both proposed business actions were valid, not evidence or launch failures.
Narrow normalization now shortens only overlong display text (retaining original)
and supplies a clearly labeled registry-purpose fallback when the agent omits
its explanation. Action names/arguments and all permission checks remain validated.
The successful run logged that missing-purpose fallback for review_package;
there were no Writer content normalizations in this particular response. Quoted
JSON, content-prefixed paths and empty citation normalization are verified offline.
A proposed broad controller exception recovery was rejected by automatic approval
review; it was NOT applied. Only these bounded display-metadata changes were made.

**Budget:** 17 new calls across the three attempts (14 controller, two Writer,
one Reviewer), all HTTP200 with known usage. New model usage estimate USD0.0721833.
Opening accounted USD0.0437376 plus new usage = **USD0.1159209 / USD1.00**;
remaining **USD0.8840791**. Opening amount includes an older unknown HTTP400
reservation USD0.0278528, retained without refund. These are usage-based estimates
and reserved amounts, not console billing attribution. Every new call was reserved
before dispatch; no unknown new charge or outstanding new reservation remains.
No additional execution is authorized by this result or by unused ceiling alone.

**Fresh verification:** 296 harness tests + 41 UI tests + 111 root tests =
448 PASS. Offline inventory/simulation tests now mock authorization explicitly,
so the owner's private live permission cannot influence their results. Dedicated
live-wiring tests retain independent mocked provider coverage. Original frozen
input, credential, lock, MEMORY and pre-existing private/generated artifact hashes
match the pre-task baseline. Read-only Git diff whitespace and empty staging checks
PASS. No install, source write, staging, commit or push. LangSmith remains a later
observability task; no trace link is fabricated. Stop for owner content review.

## M2-D026 — Reviewer quality (#1), November 9, 2026

**Implemented and live-tested; changes requested, no content acceptance. Review-page
restructure (#2) deferred.** All12 explicitly listed phrases pass exact-offset
regressions. Availability/urgency, invented product facts and preference/prediction
matches cannot receive effective Reviewer clearance: even omitted/malformed/cleared
model opinions retain deterministic human-clearance findings. No human-approval
control or bypass of product evidence/launch policy is introduced. Other categories
remain contextual judgments. Frozen prior package now scans33matches/14protected;
its source/Writer/Reviewer receipts remain unchanged.

**Final role mapping:** controller Qwen/Qwen3-30B-A3B-Instruct-2507; Writer and
revision NousResearch/Hermes-4-405B; separate Reviewer
Qwen/Qwen3-30B-A3B-Instruct-2507. Reviewer is a different model from Writer, though
it shares the controller's model ID. All use the existing Nebius endpoint. Account
catalog and official public catalog HTTP200 confirm exact IDs. Qwen30 is active,
not deprecated, JSON-mode enabled,262144context,.10/.30USDperM. Qwen235 alternative
was rejected because its serving entry is deprecated. Official sources:
[model catalog metadata](https://tokenfactory.nebius.com/api/public/models_info),
[Qwen guidance](https://nebius.com/services/token-factory/models/qwen-models-inference).
Catalog/pricing receipts in data/generated/d026-reviewer-quality-v1/.

GPT-OSS120B was the initial qualified candidate: catalog active/JSONmode,.15/.60USD
perM. Its actual integrated Reviewer call returned only an opening brace/whitespace,
finish_reason=length at8192completiontokens. Complete response and paid usage kept;
no findings were invented. It is not the final Reviewer. V4profile preserves that
experiment; v5profile selects Qwen30 without changing the v4Reviewer prompt/contract.
No new framework, dependencies or direct OpenAI API/key route.

**Actual execution, separated accurately:** two full US app attempts stopped before
review on unchanged Writer citation checks: ads concepts.0.headline then blog title
(field_claim_coverage). Neither was repaired or hidden. Third full US attempt through
existing CLI/harness generated five valid Hermes drafts and reached
awaiting_human_review; GPT-OSS review was incomplete. Source run
5c1898e9-cfe8-43fd-9597-7c94b31cdf47, receipts
 data/generated/live-package-BUILD-US-52a4c1d1d913/.
Then one Qwen Reviewer-only call re-reviewed that exact admitted package using the
production ContentCall/LiveTransport/RunBudget, original authoritative binding and
same context. No further research/Writer call. This isolates Reviewer behavior;
it is not a second complete autonomous Qwen-reviewed run or an app-session restore.

**Qwen result:** HTTP200, JSON Schema PASS, backend finding/quote/path checks PASS;
24findings:4blocking/20advisory, all24scan matches assessed, zero unassessed. Four
protected matches(lineup twice,favorite twice) remain human_clearance_required;
none is effectively cleared. Additional novelty/differentiation/intensity language
has contextual advisories. Review status changes_requested; human_accepted and
publishing_allowed false. Reviewer interpretations and suggestions still require
human assessment (e.g.classic favorite may refer to soda floats). One test does not
prove consistent semantic accuracy. No automatic rewrite/revision followed.

Reviewer receives code-computed measured_lengths for every actual template target,
not editorial_warnings. Positive length-praise patterns contradicting measured
out-of-target content are excluded from accepted findings, with raw material and
validation issue retained; accurate negative observations remain allowed. Targets
remain advisory. Actual Qwen response made no length-target-compliance claim.
This deterministic textual check is bounded, not a general semantic truth detector.

New preserved review: data/generated/d026-qwen-reviewer-us-v1/ includes source
binding, complete request/response, accepted/raw findings, usage and
**readable-review.md** (all findings, computed counts and complete unchanged drafts).
Qwen:15553input/4037output,80.973seconds,USD0.0027664estimate. No false claim that the
current browser session automatically contains this CLI/Reviewer-only result; use
the readable artifact for #1review. The #2screen/history access work remains pending.

**Verification:**302harness+41UI+111root=454PASS; provider/backend metaschemas and
actual Qwen output schemaPASS. All12phrases covered offline; each present live hit
is traceable to exact text/offset.359pre-change source/oldprompt/config/history/
credential/lock/MEMORY hashes preserved, credential exclusion/private0600receipts/
Git whitespace/empty staging checksPASS. No source edits/install/Git publication.

**Budget:**18new calls (three full attempts plus one Reviewer-only), new usage
estimateUSD0.0722899. Cumulative accountedUSD0.1882108/1.00, remaining0.8117892,
including oldunknownHTTP400reserve0.0278528. No new unknown charge; no reset/refund.
These are conservative usage estimates/reservations, not console billing. Further
calls stopped after the successful Qwen assessment. Private authorization defaults
to data/private/reviewer-quality-qwen-authorization.json, created with current
scope/expiry by the existing template/validator; shared locked ledger unchanged.
Old authorizations/receipts retained. No workspace runtime dependency. Stop for owner
review of #1; no #2implementation or further paid calls inferred from unused cap.

## M2-D027 — Expanded review, Writer diagnosis and grouped PMM page

November 9, 2026. **Implemented / owner review pending.** Owner approved these three
steps in order under the existing cumulative USD1 ceiling. No new full Writer run,
source change, automatic policy relaxation, Git publication or content acceptance.

**1. Same-package re-review.** Added announce, launch, family, latest, stands out and
fondly remember. The complete “announce the launch” match is protected availability;
contained announce/launch tokens do not create duplicate novelty decisions. Other
matches are contextual candidates, not automatic factual verdicts. Same unchanged
Hermes package/source run5c1898e9-cfe8-43fd-9597-7c94b31cdf47 and original authoritative
input binding; one Qwen/Qwen3-30B-A3B-Instruct-2507 Reviewer call, v5Reviewer prompt,
unchanged production output schema. Controller remains Qwen30; Writer/revision
remain NousResearch/Hermes-4-405B. Historical prompts/profiles/captures preserved;
v5execution/v6live profile version the new instructions. Historical v4package input
binding is explicitly revalidated, never silently rewritten into the new contract.

HTTP200; provider/backend schema and backend quote/path/ID checks PASS.31valid findings,
31/31scan hits assessed,8blocking/23advisory;8protected occurrences across4groups.
All requested newly present wording is flagged, including announce the launch,
family, latest, stands out and fondly remember. No malformed/unassessed finding.
Input16551/output4266tokens;76.90884seconds;estimateUSD0.0029349. No retries or further
inference. Cumulative accountedUSD0.1911457/1.00; remaining0.8088543, including the
unchanged oldunknownHTTP400reserve0.0278528. Usage estimates/reservations are not
console billing attribution. Full live Start remains closed: its historical default
owner authorization does not match the new profile scope. The one-off Reviewer
permission remains a protected receipt, not a grant for a fresh full-agent run.

Reviewer must provide a short drop-in replacement, preserve simulated brand voice,
add no new claim and differ from the original. Code rescans every proposed hint;
repeated/flagged/instructional/overlong hints are hidden. Hint screening additionally
rejects isolated new/introduce, consumer recall and smooth/velvety replacement claims,
where short fragments lack surrounding context.7of31suggestions hidden;24eligible
occurrence hints (15distinct group hints). Raw suggestions/captures preserved.
Visible label: “Reviewer hint (advisory)”; nothing auto-applied. Scanning is a bounded
screen, not proof that a replacement adds no unsupported meaning. Reviewer still
over-interprets Introducing as forbidden; its opinions remain contestable human hints.
It now acknowledges fictional US authorization instead of calling it pending.

**2. Both Writer failures reproduced offline, validation unchanged.**

| Preserved attempt | Exact rule/path | Observed cause |
| --- | --- | --- |
|2198f9d509f3|field_claim_coverage / content.concepts.0.headline|“Cherry Float Inspired by Classic Soda Floats” in the ad headline had no headline reference; only ad bodies were referenced.|
|fba6c6480fd7|field_claim_coverage / content.title|“A New Flavor Inspired by Classic Soda Floats” in the blog title had no title reference; introduction/body/CTA references do not cover its title.|

Both formats already cite PROD-002 and PROD-003 elsewhere, satisfying the separate
objective_claim_coverage union check. These failures are not caused by requiring
both IDs in every format. Relaxing that union rule would not remedy them. No rule,
prompt, evidence, source or citation repair changed. Latest three comparable full
Writer attempts:1admitted/3; too small to forecast future success, and not an overall
historical LinkedIn/model success rate. Citation reliability remains an open demo
risk. Existing retry eligibility excludes field/evidence policy failures; no new
retry permission or automatic repair was introduced in this checkpoint.

**3. Existing review page replaced, latest supplied screenshot governs.**31phrase
occurrences become10package-wide decision cards, including unique across6places.
One group choice plus explicit occurrence overrides; human Request changes / Keep
wording are exact-content/review-bound annotations. They never edit drafts, clear
launch restrictions, add evidence, grant publishing or approve the package. Any
new draft/review invalidates previous choices; original findings stay intact.
Protected categories cannot be model-cleared. Explanations, locations and eligible
advisory hints appear in cards; highlighted complete drafts follow in five tabs
with actual attention counts. Cleared groups, raw findings, risk scan, original
statuses/ledger and diagnostics are disclosed under collapsed sections. Existing
feedback and one revision use the same harness/budgets, with choices supplied as
human wording preferences and a fresh review of the resulting version. No new
pipeline/framework/dependency or auto-edit/apply-suggestion action.

Live decision clicks save protected local audit receipts; fixture clicks stay in
session memory. Current-session choices survive navigation/rerender. They are not
a cross-session approval workflow. A saved review has explicit read-only agent
status: wording decisions are available, but graph restoration/paid revision of
that CLI run is not connected. Current live/offline runs retain the existing
revision capability. No Continue to approval/publishing action was added.

**Access and reproducibility.**http://127.0.0.1:8520 → Live agent → **Saved review**
(when no current task is selected); exact saved US package visible without Start
agent. Optional pointer data/private/current-review.json is0600 and contains source
and review relative paths plus SHA256, restricted to data/generated/. The loader
checks hashes, safe paths/permissions and original source/evidence/review binding
before display; it never loads credentials, restores an executable graph or calls
models. New clean checkouts need neither pointer nor receipts; use Demo simulation
for the same screen. For actual preserved results, provision the pointer from the
owner-authorized protected source/review receipts, copying neither secrets nor
restricted data into docs/workspace. No required workspace runtime dependency.

Protected source: data/generated/live-package-BUILD-US-52a4c1d1d913/state-10.json.
New receipts/readable review: data/generated/d027-qwen-reviewer-us-v1/.
Original review-result.json captures the initial accepted response; the separate
review-result-display.json applies final conservative hint screening to that same
raw response, without another call. No historical capture was overwritten.

**Verification:**313harness+45socket-blockedUI+111root=469PASS. Expanded phrase,
protected-clearance, bad-hint, six-occurrence grouping, override/stale-binding,
HTML escaping/highlight fidelity, original field rejection, historical authority,
missing/tampered/private artifact, one-revision and no-inference navigation tests.
Provider/backend metaschemas and actual response schemaPASS.498preexisting source,
oldreceipt/prompt/credential/MEMORY hashes preserved. Git diff whitespace and empty
staging PASS. No packages installed, source dataset edits or Git publication.
Browser verified the real saved review,10cards/31occurrences, six-place unique group,
blog tab highlighting and collapsed technical sections in the existing dark theme.
No human content decisions were made by Codex on the real package.

Next: owner inspect the page and findings. Live UK/India, a new live revision,
LangSmith, Git sync and submission remain subsequent work, not results claimed here.

## M2-D028 — First-review handoff and live human revision wiring

November 9, 2026. Owner authorized Writer field-citation instructions, the existing
live review/revision connection, then exactly one fresh US run stopped at Version 1.
Standing cumulative USD1 budget; no per-call check-ins. No new pipeline, framework,
dependency, approved dataset change, Git publication or content acceptance.

**Decision M2-D028.** Hermes remains Writer/revision; Qwen30 remains controller and
independent Reviewer. Clarify exact-field references rather than relax validation.
Keep human choices grouped, with occurrence exceptions, and revise only after an
explicit human click. Rationale: address the two diagnosed uncited headline/title
failures and let the PMM direct the complete package before spending its revision.
Alternatives rejected: automatic citation invention, generating a replacement run
on feedback, silently truncating choices, or auto-revising before owner inspection.
Status: implemented and verified; owner content decisions remain pending.

**Writer and revision instructions.** New package_writer_v2.txt and
package_revision_v3.txt explicitly require claim_references for headlines, titles,
subject lines and CTAs that assert flavor/inspiration facts. A body citation cannot
cover another field; flavor=PROD-002, inspiration=PROD-003, both when asserting both.
Creative fields remain uncited. Backend admission, source authority and the output
contract are unchanged. Versioned execution v6/live profile v7 preserve predecessor
bytes and exact old input/prompt bindings (v4/v5 still revalidate).

**Live revision connection.** The actual current LivePackageRun owns the review
page. Request revision passes all effective Change and Human prefers keeping
choices, including occurrence locations/offsets, plus notes to the existing
FoundationSession. Its guarded owner command records exact version/review binding
before inference. The same revision Writer returns a complete Version 2; a fresh
independent Reviewer checks that exact new package, shown on the same review page.
Original drafts, reviews and decision receipts remain retained; new choices are
bound afresh. Keeping wording is a creative preference, never factual evidence,
launch permission, human acceptance or publishing. Advisory hints are not applied.

Grouped feedback is compacted by phrase/choice, never silently truncated. Package
feedback has an explicit 12,000-character bound so complete decisions and the
1,500-character notes can be delivered; historical single-LinkedIn feedback remains
2,000. The backend checks authoritative original evidence independently of the
projected Writer view. Unit/UI tests cover feedback exceeding the old bound,
changes plus kept wording, occurrence override, stale-version rejection, no calls
on choices/rerender, one revision and fresh Version 2 review. These mocked Version 2
results establish wiring, not live revision quality; no live revision was made.

**First-review boundary.** Current profile hands Version 1 to the human even when
Reviewer findings need attention; no automatic Reviewer-directed revision consumes
the owner's one correction. All findings/protected human-clearance requirements
remain visible. One fixed private Start authorization/output directory prevents a
second fresh run even under the standing ledger; no automatic Writer retry was
authorized for this run. Original failures and all previous private permissions
remain intact. Current live object's one revision stays available for the user.

**Actual fresh app run.** Run c64221d2-43d8-4570-8be6-16014d5673af, US / December 14, 2026 /
flavor_discovery, launched from the actual Streamlit Start agent button.
Model-selected actions: read_pmm_brief → check_launch → search_product_evidence → generate_package → review_package.
7 model calls / 1 evidence search; one Writer attempt, one Reviewer attempt,
zero revision attempts. All five formats admitted, exactly three ad variations.
Package ready for your review at Version 1. Review complete=False;
status=review_incomplete; 21 scan occurrences / 8 phrase groups.
**Observed Reviewer failure:** Reviewer returned truncated JSON at its 8192-token completion limit (finish_reason=length). No complete model assessment was admitted; Review incomplete is explicit. Deterministic scan hits and protected human-clearance findings remain available. Full raw output was preserved; no retry or repair.
The 0 blocking / 8 advisory / 0 cleared counts here are
code-preserved scan/fallback findings, not successful semantic judgments by the
truncated Reviewer. HTTP200 and known billed usage do not make the review complete.
Human content approval and publishing remain false. Review judgments are still
advisory/contestable; package readiness does not assert factual perfection.

The exact previously problematic ad headline and blog title now carry PROD-003
references on their own fields; the factual email subject also has PROD-003.
The creative fixed LinkedIn CTA has no reference entry. No citation was added by
repair code. This is one successful structural result, not a reliability guarantee.

Actual roles: controller Qwen/Qwen3-30B-A3B-Instruct-2507; Writer/revision
NousResearch/Hermes-4-405B; Reviewer Qwen/Qwen3-30B-A3B-Instruct-2507. Same Nebius
transport, structured-output schema, accepted context projection and frozen sources.

**Access.** http://127.0.0.1:8520 → Live agent → Current run → Review package.
Choose Request changes / Keep wording (and occurrence exceptions), add optional
notes, then Request revision. That explicit click is the next inference boundary;
Codex made no wording decisions and did not click it. Keep this current browser
session: its executable graph is session-owned. Historical Saved review remains
inspection-only and is not a restored agent. No server restart is required now.

**Verification and cost.** 319 harness +46 socket-blocked UI +111 root =476 PASS;
backend/provider JSON Schema metaschemas PASS, fresh authoritative package binding
PASS. The focused six-test revision suite was rerun after strengthening the long
feedback assertion. 534 old source/prompt/config/receipt/credential/lock/MEMORY file
hashes preserved. No credentials are included in product configuration or reports.
Receipt directory0700/files0600. Code/tests/docs are canonical; private runtime
receipts live in data/generated/ with explicit scoped authorization in data/private/;
no required runtime/build/test dependency on workspace/ introduced.

New model estimate USD0.0268591; cumulative accounted USD0.2180048/1.00,
remaining USD0.7819952. Includes unchanged historical unknown HTTP400 reserve
0.0278528; no refund/reset. Input 103945 / output 10026 tokens.
Figures are conservative usage estimates/reservations, not console attribution.
Complete requests, raw responses, candidate/validation, action/state/capture and
spending remain in data/generated/live-package-D028-US-v1/. Calls stopped at the
requested Version 1 boundary. The human may now request the approved one revision;
UK/India, LangSmith, Git sync and submission remain separate work.

## M2-D029 — Compact grouped Reviewer and completed Version 1 review

November 9, 2026. **IMPLEMENTED / COMPLETE REVIEW; OWNER CONTENT DECISIONS PENDING.**
Owner authorized deduplicated phrase/category groups with locations, one judgment
per group, explicit meaning-difference exceptions, reason≤25 words, suggestion≤12,
and a16,384-token Reviewer backstop. Re-review only the current unchanged Version1;
same cumulativeUSD1 budget, no new Writer or research loop. Decision M2-D029 adopts
that protocol in the existing ContentCall/harness. Rationale: avoid repeating each
occurrence's explanation and filling8,192tokens. Alternatives rejected: only raising
tokens, dropping caveats/evidence, inventing a completed truncated review, or
regenerating the package. Prior failures and original payloads remain immutable.

**Data and enforcement.** The Reviewer receives9distinct phrase/category groups
covering21exact locations; each location references the single complete package
field, without repeating that field as scan context. Original product evidence,
qualifications, source restrictions and computed lengths remain. One default
judgment is expanded deterministically to exact original quotes and offsets.
Per-location exceptions require meaning_differs=true and a short explanation.
Unknown/duplicate groups, missing coverage, incorrect locations/quotes, overlong
reasons/suggestions or contradictory length praise cannot mark a review complete.
Evidence-ID violations remain rejected. Provider schema uses the existing retained
keyword dialect; word limits are independently enforced by Python. Additional
material findings outside group judgments are bounded to12, retain exact quotes,
and use the same short-text limits. Dimension statuses remain computed in code;
protected categories always retain human clearance, including model-cleared cases.
Raw grouped judgments are preserved separately from expanded per-format findings.

New package_reviewer_v6.txt, package_execution_v7.json and live_package_profile_v8.json
version these changes. Writer/revision prompts, product content/schema, frozen source
bytes and evidence admission are unchanged. Only Reviewer completion rises to16,384;
Writer/revision remain8,192. Exact roles remain Qwen30controller/Reviewer,
Hermes405BWriter/revision, all through Nebius. Historical v4/v5/v6 input and prompt
bindings remain revalidatable. No dependency, framework, database or source change.

**Actual hosted result.** Exactly one Qwen/Qwen3-30B-A3B-Instruct-2507 Reviewer call,
no Writer/controller/research call. HTTP200, finish_reason=stop; actual response
schema and original-authority validation PASS.9group judgments cover all21locations;
zero meaning exceptions.12additional raw findings; existing duplicate-finding
normalization retains raw rows while ignoring exact repeated entries. All five
formats have complete review, zero validation issues and zero unassessed matches.
Actual maximum reason=20words; suggestion=10words across ALL returned judgments,
including additional findings.1,802outputtokens versus the earlier8,192-token
truncation;14,240inputtokens;25.218576seconds.16,384was a backstop, not consumed.
Status=changes_requested; this is completed assessment, not content approval.
Reviewer still overinterprets Introducing/newness and repeats some additional
wording observations across dimensions. The complete results remain advisory for
the PMM; semantic perfection or consistent model reliability is not established.

**Same current package and live revision retained.** RunID
c64221d2-43d8-4570-8be6-16014d5673af and packageSHA
4af28a197998c0e5dd81c3e04441f914aecfeabdb2d914f16f46977158d88115 are unchanged.
Version1, all five drafts byte-equivalent at the content level; zero revisions or
human wording choices. The old incomplete assessment remains in reviews/history
and its original protected receipts. The owner recheck is explicitly logged as an
owner command, not invented autonomous model behavior. Current counters are8/12
model calls: controller5,Writer1,Reviewer2,revision0; search count remains1.
A third Reviewer slot is reserved for the already-approved human revision's fresh
assessment. Shared12-call andUSD1limits remain unchanged; role caps do not add calls.

Deploying the Reviewer code reuses the existing FoundationSession/checkpointer
contract with a narrowly verified current-Version1 checkpoint. The private
current-live-run.json pointer binds state, capture and scoped permission by SHA;
exact original authority, known usage, standing-ledger claims, role counts, runID,
review completeness and latest receipt are rechecked before resume. No new run,
research, generation or paid call occurs on resume/navigation. Stale counters or
changed receipts fail closed. Previous controllers/Writer responses, both reviews,
all attempts and actual costs are retained. This is current-Version1 handoff, not a
generic run-history service. The remaining one human revision stays available and
uses fresh grouped review. Historical incomplete Saved review remains separate.

**Access:** http://127.0.0.1:8520 → Live agent → Current run → Review package.
Actual browser verified Package ready without Review incomplete; the same Version1
and complete grouped findings are present. Request revision awaits the owner's
choices/notes; Codex did not select wording decisions or invoke revision. Publishing
and human approval remain false. Explicit Current run can resume after browser
reload without new inference; a newer revision checkpoint invalidates the old pointer.

**Verification:**328harness+47socket-blockedUI+111root=486PASS. Nine focused grouped/
checkpoint tests cover deduplication, exact expansion, explicit meaning exceptions,
word limits, bad IDs/quotes/coverage, protected clearance, stale/tampered receipts,
no-call resume, and recheck→human revision→fresh review within12total mock calls.
Actual backend/provider JSON Schema metaschemas and returned schema PASS.
596 historical source/prompt/config/receipt/credential/lock/MEMORY hashes preserved;
private0700directory/0600receipts, credential exclusion and ignore checks verified.
No staging/commit/push, package install or workspace runtime dependency introduced.

**Budget and protected records:** new estimateUSD0.0019646; cumulative
accountedUSD0.2199694/1.00, remainingUSD0.7800306. Prior unknown
HTTP400reserve0.0278528 retained; no reset/refund. Estimates are not console billing
attribution. data/generated/d029-grouped-review-v1/ holds the source binding, call08,
raw response, usage, state/capture01 and summary. Source remains the protected D028
state/capture10. data/private/d029-review-refresh-authorization.json is the scoped
permission; current-live-run.json contains only safe relative paths/hashes. These
optional artifacts are provisioned from an authorized completed run; clean checkout
works without them via Demo simulation. No runtime dependency on workspace/temp
scripts. Stop at Package ready, complete review, Version1. Owner decisions and
one revision are next; no further model calls were made.


## M2-D030 — Required review, saved Version 2 recovery and run tabs

Date: November 9, 2026 (America/Los_Angeles). Owner explicitly authorized this
bundle and one saved-Version-2 review under the standing USD1 build ceiling.
Status: IMPLEMENTED / OFFLINE PASS / LIVE REVIEW INCOMPLETE / OWNER REVIEW PENDING.
No content acceptance or Git publication.

### Decision and resulting behavior

The controller chooses research and when to draft inside the registered task.
After package admission or revision, the existing LangGraph now routes to a
code-owned required-review node. Every review then waits for the owner; blocking
findings cannot initiate another automatic revision. Used generation/revision
actions are omitted from the state-specific native tool list and checked again
at dispatch admission. Required review is labeled harness_required, not a model
decision. Original source/evidence/launch/contract validation is unchanged.

Rationale: a required independent review must not depend on another model choice
or lose its reserved capacity to a duplicate revision. Alternatives rejected:
increasing controller limits, hardcoding research order, a new orchestration
framework or regenerating saved drafts. Role ceilings/shared12-call cap unchanged.
A new normal package path uses6modelcalls through first review and3for explicit
revision/re-review, rather than7+4 with controller-selected reviews. These are
offline verified path counts, not measured success rates or cost guarantees.

### Review and run UI

One existing run screen has Activity | Review | Package below its status card.
Activity selects while running; Review selects on human handoff, including the UK
question. Tab/navigation changes execute no providers. The stopped screen offers
Review Version 2 only for a valid saved, not-yet-reviewed V2 with known accounting
and a remaining Reviewer slot. No new Writer or research is involved in recovery.

Overlapping spans within the same field merge into one occurrence/card using the
complete longer span and union of categories/findings. Human protection survives
if any component is protected; raw findings remain unchanged. Across-package
phrase decisions and occurrence overrides remain exact-version-bound. Override
buttons appear only for2+places. Decisions read Will be rewritten in Version 2 /
Kept as is; Create Version 2 replaces Request revision and disappears after use.

Every attention card shows a screened advisory suggestion, up to2bounded local
alternatives when an existing hint is unsafe, or The Writer will rephrase it.
Locally authored alternatives are labeled Alternative wording (advisory), not
attributed to the Reviewer. No hint is applied automatically, no extra inference
is used for hints, and a clean phrase scan does not establish semantic support.
New scan phrases stay tuned / where you can find are protected availability hits.

### Actual saved-run recovery

Same run: c64221d2-43d8-4570-8be6-16014d5673af. Same saved Version2 package SHA256:
49ef28d514903ee4807a0ae159800dd82649d489efc18b8f5bd707c56065411f.
Loaded state-07/capture-07 from data/generated/d029-grouped-review-v1/; all old
receipts and both versions retained. The old state counted one rejected pre-HTTP
controller attempt as turn12 although there were11paidcalls. Recovery logs this
difference explicitly, preserves that failure event and every actual paid role/
spending counter, then consumes only the12th actual call for the Reviewer. No
spending refund, increased limit, fresh Controller, Writer, revision or source call.

Exactly one Qwen/Qwen3-30B-A3B-Instruct-2507 Reviewer call: HTTP200, finish=stop,
17,330input/2,176outputtokens,39.910956seconds overall recovery. Prompt/model/
16384outputcap unchanged. Backend/provider schema definitions checked offline;
returned JSON matches schema. Six phrase groups/11locations received judgments.

**The semantic review is INCOMPLETE, not a full review PASS.** The response added
11occurrence overrides marked meaning_differs=false, violating the explicit
exception protocol, and6additional quotes do not occur in Version2 (they refer to
older wording). Exact-quote/protocol validation was retained. All11scan matches
have default assessments, but no format is falsely marked fully reviewed; raw
output and invalid findings remain in Technical details. Status awaits human
review; human acceptance=false, publishing=false. No repeat model call or rewrite.

Current counters: controller7 / Writer1 / Reviewer3 / revision1 =12/12actualcalls,
one evidence search. New usage estimate USD0.0023858; cumulative accounted
USD0.2474739/1.00, remainingUSD0.7525261, including unchanged historical unknown
HTTP400reserve. These are conservative estimates/reservations, not console charges.
The current run has exhausted its call limit even though the dollar balance remains.

New protected receipts: call-12-*, state-08.json, capture-08.json and
d030-recovery-summary.json in the same directory. Prior current pointer archived
as d030-previous-current-pointer.json. data/private/current-live-run.json binds
the newest V2 state/capture and existing authorization; raw assessment revalidates
before restoration, including its incomplete status. No workspace dependency or
general run-history service. App127.0.0.1:8520 → Current run → Review / Package.

### Verification and preservation

497offline tests PASS:334harness,52socket-blockedUI,111root. Added regressions for
mandatory review/no extra controller choice, replay blocking, known-accounting
legacy recovery, exact original authority, unknown-billing rejection, overlap
category/protection union,2-place overrides, one-place controls, labels/tab state,
UK clarification visibility, incomplete-review preservation and no inference on
refresh/navigation. Existing adversarial source/launch/budget checks still pass.
Updated scripted action/count assertions for the newly required graph edge.

Actual private Version2 rendered through Streamlit AppTest: five drafts,10attention
cards, Review selected, all3run tabs present, exact incomplete warning, no second
revision/recovery button. Zero provider/source calls or state changes during that
check. Native-browser final capture was not completed while the owner was using
another Chrome window; no pixel-perfect/browser-rendering claim is made. The
existing LaunchLens server alone restarted on8520 with new code; Week2 untouched.

All723preexisting baseline files were checked:719unchanged; only the intended
build ledger, current pointer and2development context/progress files changed. Sources, original response/state/capture
receipts, authorizations, MEMORY and historical datasets remain unchanged. No new
dependency, model, source integration, framework, automatic repair/retry, Git
staging/commit/push or publishing. BUILD_CONTEXT/progress reflect the actual
incomplete live assessment. Stop for owner inspection; do not claim a complete
Version2semantic review or silently spend again to obtain one.


## M2-D031 — Current-Version-2-only review and isolated findings

**November 9, 2026 · Owner-authorized direction implemented · Result awaiting owner inspection.**
Decision: review only the current version; discard unverifiable findings individually;
reserve mandatory reviews separately from task-loop calls. Rationale: prevent old
wording from contaminating a new assessment and avoid losing valid findings or
required review to controller exhaustion. Alternatives rejected: another Writer,
rewriting obsolete quotes, discarding the whole usable assessment, resetting call
history or adding an unbounded retry. Latest explicit owner instruction supersedes
D030's no-further-call boundary only for this saved-V2 re-review.

### Changes and verification

- `prepare_call()` rebuilds the phrase groups from the exact saved V2 and supplies
  V2 text, scoped authoritative evidence, policy, computed lengths and schema.
  V1 assessments and quoted owner feedback are absent. No prior findings, no
  changes-summary prose and no source/history regeneration. Writer/Reviewer models,
  prompts, schema, temperature and completion limit remain unchanged.
- Finding-level validation preserves valid group defaults and valid additional
  findings; invalid overrides, quotes, paths, evidence references or length praise
  are dropped individually. Raw responses remain protected. UI displays
  **“N findings couldn't be verified”** when needed. Missing scan judgments remain
  visible for human assessment; protected categories still require human clearance.
  A wholly unreadable review stays explicitly incomplete. Code computes statuses;
  structural acceptance is never product-truth validation or human approval.
- New pinned `package_execution_v8.json` / `live_package_profile_v9.json` retain
  predecessors. The task pool remains **12 non-review calls** (controller and Writer
  actions); required Reviewer calls have a separate **4-call cap**. Controller role
  ceiling is 12, Writer 2, revision Writer 1, Reviewer 4, with the task pool also
  enforced. Absolute maximum is 16 paid calls, subject to the unchanged USD1 ceiling.
  Conservative sum-of-role reservation USD0.8761344 over-reserves the tighter task
  pool. Every paid call retains its original event and dollar accounting. No counter
  reset/refund, no automatic re-review, no new Writer authorization.
- Fresh offline suites: **505 PASS** — 341 harness, 53 UI, 111 root. Tests cover
  V1 sentinel exclusion, V2-only groups, valid/invalid finding isolation, unknown
  IDs, source tampering, unreadable responses, independent cap exhaustion, one-shot
  V2 recheck, no Writer/research and visible UI notice without inference.
  Historical saved-review loader regression: 11 PASS after its policy selection
  was pinned; historical receipts are not silently reassessed under new rules.
  Both backend and provider JSON Schemas passed offline schema checking.

### Actual single live re-review

Same run `c64221d2-43d8-4570-8be6-16014d5673af`, same V2 SHA256
`49ef28d514903ee4807a0ae159800dd82649d489efc18b8f5bd707c56065411f`.
Exactly **one Qwen/Qwen3-30B-A3B-Instruct-2507 Reviewer call**; no Controller,
Writer, revision, Notion or Pinecone calls. HTTP200, finish=stop, response schema
PASS. **6 groups / 11 locations assessed; zero unverifiable findings and zero
unassessed scan hits.** All eleven expanded findings are model-rated blocking:
consumer preference, novelty, product format, and availability/urgency wording.
The result is **Package ready for human review / changes requested**, not content
acceptance. Some findings may be over-cautious; suggestions remain advisory and
screened (e.g. suggestions repeating “favorite” or “format” are hidden). No text
was changed and no semantic reliability claim follows from one successful review.

Actual usage: **13,721 input / 477 output tokens**, **9.376845 seconds** overall.
New uncached usage estimate **USD0.0015152**; cumulative accounted **USD0.2489891
/1.00**, remaining **USD0.7510109**, including the unchanged old unknown-HTTP400
reservation. Estimates/reservations are not an attribution of console billing.
Paid history now totals **13**: controller7, Writer1, Reviewer4, revision1;
**9/12 task calls and 4/4 required reviews**. All prior twelve accounting events,
review history, both draft versions, failure records and original feedback are kept.
No additional call after this result. Review-call cap exhausted; no content approval
or Git publication is inferred from the remaining dollar balance.

### App, protected provisioning and stop

Existing app restarted at <http://127.0.0.1:8520>: **Live agent → Current run → Review**;
Package tab contains the unchanged five drafts. Actual saved-V2 Streamlit AppTest
PASS: Review selected, six decision cards, five drafts, no global incomplete warning,
zero network calls and no state mutation. No native-browser screenshot/layout claim.

Optional private handoff pointer `data/private/current-live-run.json` now binds
`data/generated/d029-grouped-review-v1/state-09.json` / `capture-09.json` and the
new scoped `data/private/d031-current-v2-review-authorization.json`. Old pointer
archived, old authorization untouched. `call-13-*`, `d031-prepared-review-context.json`
and `d031-review-summary.json` retain exact request/response/accounting evidence.
Files remain private/ignored, not runtime dependencies on workspace. A clean
checkout uses safe fixtures; live restoration requires explicit protected receipts,
matching hashes, existing provider credentials and current scoped authorization.
Prior source files/receipts and MEMORY preserved; no install, source write or Git
staging/commit/push. Stop at this reviewed V2 for owner inspection.


### M2-D031 owner acceptance and Git publication authorization

November 9, 2026: owner said “approved git sync” after the V2 review result.
The completed implementation/checkpoint is owner accepted for scoped repository
preservation. This is not human acceptance of the generated marketing package,
resolution of its flagged wording, permission for a third draft/re-review, or
approval of future observability/submission work. Original technical results,
limitations, failed attempts and pending content decisions remain intact.
See repository-sync-2026-11-09.md for this publication's exact verification scope.


## M2-D032 — Run-page card stack and internal package handoff

Date: November 9, 2026. Status: implemented and verified; owner UI acceptance pending.
Owner authorized the attached run-page layout, dark theme, UI-only work and four
screenshots. No inference, source refresh, Git publication or next milestone.

### Decision and implementation

Replace the existing run/review page, retaining the existing harness and three tabs.
Activity is selected during execution and Review at human handoff. The actual
ledger supplies research, human feedback, Version 2 creation and required review
steps; no fabricated skipped tools or model judgments. The status remains above
the tabs. Home layout and launch policy remain unchanged.

Review now presents one phrase group at a time, progress segments, Previous/Next,
auto-advance, a screened advisory replacement, Writer-rephrase and Keep wording.
Grouped locations and existing occurrence overrides remain available. A choice
records a version-bound preference; it does not edit a draft or create evidence.
The recap reopens any choice. Create Version 2 retains the existing single-revision
and budget guards and stays locked until must-decide groups are resolved.
Current Version 2 cannot create Version 3.

Package shows current per-format attention, View controls, actual changed-text-field
counts, preserved V1/V2 comparison, internal-use approval and labeled Markdown/copy.
Approval requires acknowledgement, complete matching review, authoritative binding,
resolved required choices and no pending rewrites. It is a separate UI-owned record;
it neither sets the harness's human_accepted flag nor grants publishing permission.
Any change to content, review or decisions invalidates it. Explicit live approval
writes an existing protected receipt; restoration of that UI approval after restart
is not implemented. Suggestions remain advisory and are not semantic guarantees.

Rationale: reduce PMM review to a manageable decision stack and a clear handoff.
Alternative retained in history: the long phrase-card list and full draft dump.
No new agent, pipeline, provider, dependency or workspace runtime requirement.

### Verification and preservation

- 347 harness + 59 UI + 111 root tests PASS: 517 total. UI socket connections
  blocked. Tests cover navigation, grouped/occurrence choices, must-decide locking,
  one explicit revision, V2 comparison, independent authoritative binding, approval
  invalidation, simulation-labeled exports and no network activity.
- Native Safari checked the four fixture views at normal/reduced zoom, with no
  horizontal clipping. Verified actual V1/V2 diff expansion and Copy all -> Copied.
  Screenshot captures use the existing offline simulation, not newly generated
  live content or owner approval. Current live V2 was not altered.
- All 743 pre-existing protected/generated/source/continuity files matched the
  checkpoint hashes before documentation updates. Only BUILD_CONTEXT and
  IMPLEMENTATION_PROGRESS receive this checkpoint afterward. MEMORY, saved V2,
  current-live pointer, authorization, credentials, budget and receipts preserved.
- Zero model or external source calls; zero installs, Git staging, commits or pushes.

Screenshots: [Activity](screenshots/d032/activity.png),
[Review card stack](screenshots/d032/review.png),
[Review recap](screenshots/d032/summary.png),
[Package and exports](screenshots/d032/package.png).

Open the app at http://127.0.0.1:8520 -> Current run -> Review or Package.
Optional offline visual fixture: run the maintained tools/preview_run_states.py
with Streamlit on port 8522; cases activity, review, summary and package.
Use the existing tools/ui environment. No private workspace inputs are required.
Clipboard success depends on browser permission; a failure is displayed with a
Download Markdown alternative. Approval and export never publish.

Stop for owner review. No new live run, revision, content acceptance or Git sync.


## M2-D033 — Compact current-version Review and full-draft modal

Date: November 9, 2026. Status: implemented, verified; owner UI review pending.
Owner authorized five UI refinements only; no model execution or Git publication.

Review now contains the card stack and end screen only. The full-draft section and
cleared-findings list are removed from that tab. Each card's See full draft opens
its format in a dismissible modal, with the exact current-version phrase highlighted
and the modal's own text viewport scrolled to it. Closing preserves the selected
card, decisions and run. Package's five View actions open the same full-draft
viewer, with all current highlights. Original text is escaped and preserved, not
summarized. Format-level findings without a quote open the draft at its beginning.

One status description remains in the status card. Duplicate pending/mock captions
are removed. Fixture origin and raw authored explanations remain under Technical
details. Demo card Why text is phrased as a contextual check; live rationale is
retained unless it is a fixture/debug explanation. This presentation change neither
clears findings nor alters their severity. Advisory suggestions remain advisory.

Review takes the current run snapshot and requires matching review-version/hash
bindings before showing decisions. Version 2 resets the V1 card position/decisions;
no V1 findings or obsolete Create Version 2 form are shown in the V2 recap. A pending
V2 review displays a pending message instead of reusing V1. Historical text remains
available through Package comparison; no Version 3 is introduced.

Rationale: keep the PMM focused on one decision, with full context available on demand.
Alternative: the previous inline full-draft section made every Review visit long.
No new pipeline, model, dependency, source, launch policy or budget behavior.

Verification: 349 harness + 63 UI + 111 root tests PASS (523 total). Focused tests
cover no appended drafts, exact phrase focus/escaping, current V2 selection, stale
review rejection, unchanged calls/state and fixture explanations kept technical.
Native Safari verified See full draft at the selected V2 blog phrase, closing and
returning, Package View from the beginning with highlights, recap and single status.
An initial browser check exposed outer-page scrolling; corrected the viewer to
scroll its own iframe window only. The corrected behavior was visually verified.
Screenshots use existing offline fixtures, not a newly generated live package:
[Review](screenshots/d033/review.png), [focused full draft](screenshots/d033/full-draft.png),
[recap](screenshots/d033/summary.png), [Package](screenshots/d033/package.png).

All 743 prior protected/source/continuity files hash-identical before the two
continuity-note updates. Saved live V2, findings, pointer, receipts, credentials,
spending ledger and MEMORY unchanged. No model calls, installs, staging, commits
or pushes. Existing app refreshed on port 8520; open Current run -> Review/Package.
Stop for owner inspection; no new live run or content acceptance.


## M2-D034 — Shared header and Home-aligned detail layout

Date: November 9, 2026. Status: implemented and verified; owner UI inspection pending.
Owner approved one shared header across Home, Setup and Current run, evenly spaced
navigation and detail content aligned with Home's main product card. Layout only.

Removed the run-only 720px header restriction. Brand/tagline and the navigation
box now use the same full-page header columns on every route. Navigation controls
share equal widths; Current setup is retained before a run exists and Current run
when one is available. Preparation, active run and saved review use Home's existing
2:1 column proportions and responsive stacking. Detail content aligns at Home's
left margin instead of floating in a centered narrow frame. Reduced detail gaps,
heading spacing and status/review-card padding; dark palette/interactions unchanged.
Rationale: consistent application shell, with readable task content. Alternative:
the former centered run-only frame created different header widths and cramped nav.

Verification: existing 63 UI regression tests PASS with network connections blocked.
Native Safari compared Home, Setup and Current run at the same desktop width:
header/navigation edges match and both primary cards occupy the same left column.
Screenshots are existing offline fixtures: [Home](screenshots/d034/home.png),
[Setup](screenshots/d034/setup.png), [Current run](screenshots/d034/current-run.png).
No new mobile-browser verification claimed. No new tests or dependencies needed for
this presentation-only change; agent/harness behavior unchanged.

All 743 earlier source/private/generated/continuity files hash-identical before
the two continuity updates. Saved live V2, decisions, receipts, pointer, credentials,
budget and MEMORY preserved. No model calls, installs or Git publication. App8520
refreshed for owner review; no further run, content approval or milestone inferred.


## M2-D035 — Human-triggered revisions without a version ceiling

**Owner direction:** Remove the full-package one-revision limit. The PM/PMM decides
whether to request another revision or accept the current wording. Implementation
is complete; further live revision behavior and content acceptance await owner use.

The existing harness now accepts V2→V3 and subsequent explicit human revisions.
Each request binds the current version, digest and selected decisions; the controller
cannot initiate the revision. The harness always reviews the new version and waits
for the human. Duplicate/stale requests remain rejected. A recommendation alone
never launches a rewrite, marks content approved or publishes it. Approval requires
the current applied version, human acknowledgement and resolution of must-decide
items; requested rewrites cannot be approved as if already applied. Evidence and
launch restrictions cannot be overridden by keeping wording.

Versioned package execution v9, live profile v10 and controller prompt v4 preserve
older configurations. The arbitrary package revision/required-review caps are
replaced by explicit human commands and cost admission. The research-controller
limit remains 12; each extra revision reserves its Writer and mandatory Reviewer
cost together before dispatch. Standing-budget reservations are locked and bound
to the run/current version; repeated clicks or concurrent processes cannot duplicate
a cycle or reset accounting. Unknown usage remains reserved. Provider model IDs,
prices, token limits, original qualification expiry and evidence validators remain
unchanged: controller/Reviewer Qwen3-30B-A3B-Instruct-2507, Writer/revision Hermes-4-405B.

The protected D035 authorization is restricted to the existing saved run; it cannot
start a new run or raise the USD1 ceiling. The original pointer is backed up; only
its authorization binding changed. Saved V1/V2 drafts, review/call receipts, previous
authorizations and the spending ledger remain unchanged. Subsequent successful
checkpoints atomically advance the pointer after state/capture receipts exist.
The UI restores exact-version decision receipts, offers dynamic Create Version N
controls, and compares each current version with its predecessor.

**Verification:** 358 harness + 64 UI + 111 root = **533 passing offline tests**.
Coverage includes V2→V3→V4, mandatory fresh review, stale/replayed requests, parallel
cost admission, same-version reservation deduplication, preservation of history and
current-version human approval. Actual saved V2 UI check: Create Version 3 enabled,
six of six decisions restored, zero must-decide left; socket connections blocked,
zero network, unchanged state/counters/ledger. No real V3 or provider call was made.

**Handoff:** Refresh http://127.0.0.1:8520 → Current run → Review. The six V2 rewrite
choices are retained. Create Version 3 is an explicit paid action, subject to the
existing grant and available reservation. Current cumulative accounted spending
remains USD0.2489891/1.00 (remaining USD0.7510109, including the previously held
unknown-charge reserve); these are ledger estimates, not console charge attribution.
No new model reliability or semantic-quality result is claimed. No Git publication.


## M2-D036 — MVP current package, three revisions and optional advisories

**Decision D036 — owner approved, November 9, 2026; implemented, owner use/review
pending.** The owner replaces the earlier unlimited-revision/history UI direction
with a smaller MVP: current version only, three revisions per run, and advisory
Reviewer notes that never block approval. Rationale: keep the PMM experience simple.
The previous uncapped revision approach and Versions/Compare UI are superseded;
protected historical data is retained rather than deleted or rebound.

- Removed the Package Versions row, Compare control and change counts. Current
  draft View links, highlights, approval and labeled exports remain. Activity is
  still the actual action log; no prior-version selector/draft comparison is shown.
- Three revisions means the initial V1 plus at most V2, V3 and V4. The harness,
  content adapter and live guard enforce the cap before further paid execution.
  Attempted revisions count toward it. At the limit the UI shows Revision limit
  reached; no editable next-version note suggests an executable fourth revision.
  Every admitted revision still gets a fresh required review and human handoff.
- Approval ignores optional advisories whether undecided, kept, or marked for a
  possible rewrite. Must-decide status is occurrence-specific, including mixed
  groups: optional occurrences do not keep a required occurrence unresolved after
  the PMM has decided it. A required requested rewrite remains unresolved until
  applied; explicit Keep resolves that wording decision, without changing evidence
  or launch permission. Invalid content, mismatched/incomplete current review and
  launch restrictions remain independent integrity controls.
- Package execution v10 and live profile v11 preserve old policies and all prompts,
  model routes, frozen evidence, prices/token caps and previous qualification dates.
  The D036 private authorization is bound to the existing run, with unchanged USD1
  ceiling and expiry; only the current pointer's authorization binding was updated,
  with a protected original-pointer backup. No new-run permission or budget reset.

**Actual offline verification:** 361 harness + 65 UI + 111 root = **537 PASS**.
New coverage checks three successful revisions then refusal of the fourth without
new Writer/cost reservation, live mock guard refusal, optional-advisory approval,
mixed mandatory/advisory occurrences, current-only UI and approval at the revision
limit. Final focused seven-test UI rerun passed after copy clarification. The first
harness run used the minimal harness environment and failed because jsonschema was
absent (five other skips); rerunning in the existing UI environment, which already
contains the dependency, passed all 361 without skips. No package installation.

**Saved-run check:** socket connections blocked; actual saved V2 loads with six
choices intact, current draft View links, no Versions/Compare, 1 of 3 revisions used,
and Create Version 3 enabled. Draft state, all call counters and ledger unchanged.
No actual V3, provider inference or new semantic-quality result is claimed. Accounted
spending remains USD0.2489891/1.00, remaining USD0.7510109 including the old held
unknown-charge reserve; these are ledger estimates, not console attribution.

**Handoff:** refresh http://127.0.0.1:8520 → Current run → Review or Package. Existing
six V2 rewrite choices remain available to apply to V3. No Git staging/commit/push,
source/dependency changes or MEMORY append. Build/progress notes updated.


## M2-D037 — UI refinements and one fresh US run

**Status: UI implemented and verified; fresh live Version1 acceptance not reached.**
Owner approved these UI fixes and one fresh US run under the standing USD1 ceiling.
No second run, regeneration, validation weakening or content acceptance is claimed.

### UI and harness behavior

- Home has no top Execution data bar. Mode: Live agent/Simulation is a compact
  dropdown beside GTM Launches. Source-check timestamp is inside Source documents.
  The existing shared header, dark palette and current-only package remain.
- Activity uses plain fallback reasons, caps displayed reasons at20 words, and labels
  owner-triggered review rechecks “Re-check (requested by you)”. Raw reasons stay in
  protected captures/Technical details; no fabricated skipped actions are introduced.
- At the three-revision limit, cards offer Keep wording or Edit it myself. Inline
  full-field edits go through the existing harness's authoritative content/evidence/
  launch checks; accepted text replaces the current version, preserves prior receipts,
  and gets a fresh deterministic scan. No paid Writer/Reviewer call is made on save.
  UI/export explicitly says human-edited, re-scanned, no new AI review. Findings on
  changed fields are not inherited; unchanged-field decisions transfer only when
  exact context, location and category match. New scan hits require fresh decisions.
  Approval acknowledgement resets after edits; stale edits and tampering fail.
- Final-version must-decide items resolve by explicit Keep or valid edits that remove
  the concern. The old requested-rewrite dead-end text is replaced with the actual
  Keep/Edit choices. Optional advisories remain nonblocking. Evidence, launch rules,
  current binding and complete review prerequisites remain; human editing cannot
  manufacture evidence or publishing rights. Manual-rescan derivations are verified
  on private checkpoint restore rather than presented as new Reviewer judgments.
- Suggestions use the risk scan; “stay informed” is protected availability language
  and is hidden as a suggested replacement. The three-model-revision cap remains.

### Exact live execution and observed failure

Controller and independent Reviewer adapters remain
`Qwen/Qwen3-30B-A3B-Instruct-2507`; Writer/revision remain
`NousResearch/Hermes-4-405B`. Original prompts, model settings, qualification/expiry,
content contract and evidence validation stayed unchanged. The fresh authorization
consumed one unique output directory, using the existing standing ledger.

| Observed step | Result |
| --- | --- |
| PMM read | Completed against Notion |
| Launch check | Proceed for US / December14,2026; publishing disabled |
| Product evidence search | Completed against Pinecone |
| Writer | HTTP200; complete candidate retained; 10,116 input +1,597 output tokens |
| Package admission | Rejected: blog `content.sections.1.heading`, rule `field_claim_coverage` |
| Reviewer/revision/approval | Not invoked; no package admitted |

The exact rejected heading is **“Inspired by Classic Soda Floats”**. The candidate
has **zero claim_references entries for `sections.1.heading`**. This is the narrow
existing per-field citation rule, not a JSON-shape rejection, source outage or proof
that every generated sentence is wrong. References on other fields do not satisfy
this heading. No automatic reference was added, no rule relaxed and no paid retry
was performed. This evidence failure intentionally does not qualify for the existing
harmless-format retry path.

Actual counts:4 controller calls,1 Writer,0 Reviewer,0 revision. New usage estimate
**USD0.0201168** (WriterUSD0.014907); cumulative ledger **USD0.2691059/1.00**, remaining
USD0.7308941, retaining earlier unknown-charge reserve. These are usage-based ledger
estimates, not attributable console billing. No new unknown charge occurred.

Protected raw candidate, original request/response, diagnostics, usage and state/
capture receipts: `data/generated/live-package-d037-fresh-us-v1/`. A labeled readable
rejected-candidate Markdown is there for private inspection. Current-run pointer is
now bound to this failed attempt; previous V2 pointer is backed up privately, not
lost. Failed first-draft receipts restore read-only with the execution guard closed;
no Try again or implicit generation is enabled for this evidence failure.

### Verification and handoff

**543 offline tests PASS:**364 harness,68 UI,111 root; final13-test focused persistence/
stopped-restore rerun also passed. Added coverage for stale/invalid manual edits,
unchanged counters/cost on save, new protected scan matches, suggestion filtering,
manual-edited approval provenance, mocked live persistence/restore, Home mode
navigation, short Activity text and read-only evidence-failure restore. No packages
installed. Early test-only issues (Home-only mode expectations and mock transport
response type) were corrected; final suites passed without ignored failures.

Actual saved failed-run AppTest: proper stopped message, no draft/approval/retry,
no execution bar, closed guard, zero socket calls and unchanged state/counters.
Native Safari verified actual Home and stopped/Activity layouts at desktop width;
all five source documents were freshly read as accessible by the homepage. No new
mobile-layout claim. Screenshots:
[Home](screenshots/d037/home.png), [stopped run](screenshots/d037/stopped.png),
[Activity](screenshots/d037/activity.png).

Open http://127.0.0.1:8520 → Current run to inspect the actual failure. The requested
Version1 human-review handoff remains incomplete; the rejected candidate is not an
approved draft or a reviewed package. Further paid execution is stopped for owner
review. No datasets, credentials, dependencies, MEMORY or Git publication changed.


## M2-D038 — Section citations and saved US Version 1 recovery

**Result: Package ready / Version 1 / owner content review pending.**

Owner direction supersedes D037's strict heading coverage and citation-stop rule
only as follows. For blog `sections.N.heading`, citations on **that same**
`sections.N.body` satisfy structural reference coverage. Other sections, the blog
title, introductions, headlines, subjects, hooks and CTAs retain their own checks.
Reference validity, authority, qualifications, launch constraints and semantic
Reviewer checks remain. This is citation coverage, not proof of entailment.

The standing-budget live adapter automatically retries the Writer at most once
**only** when a complete candidate inspection finds missing citations and no
other structural, invalid-ID, CTA, link, wording or evidence failure. It reuses
saved research and supplies the exact validator diagnostic; it never adds a
citation, edits text, resets counters, extends authorization or repeats research.
Unknown transport/billing and mixed failures stop. Existing explicit technical
retry controls remain distinct; format-only failures do not automatically retry.
The automatic retry shares the two-Writer-attempt limit and existing USD1 ledger.

**Actual saved-run outcome.** Run `41a5e49a-739e-41a0-9d36-f2530348b3ee` retained
US / December14,2026 / flavor_discovery, PMM, launch Proceed and Pinecone evidence.
Original Hermes candidate revalidated successfully under the new heading rule;
its content and references are byte-equivalent under canonical serialization
(SHA256 `68a2d1e9bad0c568105776f12ca0ff5817507cc7795bb287b8abbb35174e3c42`).
No new Writer call or automatic retry was necessary. Original rejection and raw
response remain preserved; a separate revalidation event records the change.
The existing graph then ran its required independent Reviewer and returned to
the human at Version1, with no revision or content acceptance.

| Actual new work | Result |
|---|---|
| Research / Controller / Writer calls | 0 / 0 / 0 |
| Reviewer | 1, `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| Writer remains | `NousResearch/Hermes-4-405B` |
| Five formats | Admitted, Version1, complete independent review |
| Reviewer outcome | Changes requested; 12 grouped phrases for human attention |
| Reviewer input / output tokens | 13,779 / 1,616 |
| Reviewer latency | 39.235887 seconds |
| New usage-based cost estimate | USD0.0018627 |
| Cumulative accounted / remaining | USD0.2709686 / USD0.7290314 of USD1 |
| Actual aggregate calls | 4 Controller, 1 Writer, 1 Reviewer, 0 revisions |
| Human acceptance / publishing | False / disabled |

**Offline verification:**372 harness +68 UI +111 root tests PASS (551 total).
Eight focused cases cover own-section inheritance, isolation of all other fields,
missing-only vs mixed failures, exact diagnostic delivery, single retry/replay,
known accounting, bound saved-run recovery and required review without new writing.
An old stopped-display fixture now uses an independent prohibited-link failure;
its former heading error is intentionally accepted by the owner-approved rule.
Mocks establish retry wiring, not live retry reliability. The actual live result
establishes saved-candidate admission and completed review, not a Writer retry.

Protected receipts remain in the original ignored
`data/generated/live-package-d037-fresh-us-v1/` directory, including new call06,
state/capture files and `d038-result.json`. A new private owner-bound resume receipt
and pointer backup preserve old approvals and the same spending ledger. No runtime
workspace dependency, new integration, model/prompt/template/dependency/source
change, MEMORY append, staging, commit or push. App: localhost8520, Current run →
Review (decisions) or Package (full drafts). Stop for owner inspection.

Native Safari verified Current run → Review defaults to Version1,12cards/3must-decide, and Package shows all five View controls. No decisions, approval or revision clicked. [Review screenshot](screenshots/d038/review.png) · [Package screenshot](screenshots/d038/package.png). Reloading Home performed its ordinary source-access reads; saved-run recovery itself made zero research calls.


## M2-D039 — Phrase-span cards and offline regrouping

**Date:**November10,2026. **Authority:**latest explicit owner instruction.
**Status:**implemented/verified; owner review pending, no content acceptance.
**Decision:**group on exact scan terms or a short Reviewer key phrase; keep full
sentences as context, not group titles. **Rationale:**the previous overlap merge
inflated a phrase into a whole quote and duplicated the same decision across
formats. **Alternatives:**retain12 sentence cards or make another model call;
neither is needed for this presentation correction.

The unchanged saved US Version1 now has6 cards across15 phrase occurrences:

| Phrase | Places |
|---|---:|
| family |2|
| guided the development |1|
| lineup |1|
| introducing |3|
| new |4|
| unique |4|

The card keeps exact text offsets, full original context, raw findings, category
union and human-clearance protection. Reviewer sentences are attached to their
short scan spans instead of swallowing the sentence. For unlinked long quotes,
a short exact term from the Reviewer's rationale or a recognized key phrase is
used; no quotation or location is invented. Group choices and occurrence overrides
remain exact-version bound. Old receipts are preserved; the new card-policy
identity prevents replaying choices made against obsolete group IDs.

Suggestions now replace **only** the selected phrase. A larger Reviewer replacement
can be narrowed only if all surrounding text is retained exactly. Every proposed
replacement is scan-screened and must pass span/lexical checks for every grouped
occurrence; stale spans, full-sentence substitutions and duplicate boundary or
sentence phrases are rejected. The card previews the complete sentence after the
change; the occurrence expander also shows each preview. This does not apply edits.
For example, Introducing → Meet previews the full original hook with only that
word changed. The old lineup → distinct option hint is hidden because it produced
“a distinct option within the Coca-Cola distinct option”. Where no candidate fits,
the explicit Writer-rephrase option remains. Hints remain advisory; deterministic
fit checks do not establish semantic support or perfect grammar.

New configured scan terms: presenting (novelty/launch language), guided the
development and designed to (invented product/company facts, human clearance).
The saved package contains guided the development; it is freshly flagged and
explicitly labeled **not assessed in the saved AI review**. The saved AI review is
not rewritten or presented as a new assessment. Scan provenance permits legacy
raw reviews, groups and hidden-hint results to revalidate under their original
scan; future assessments carry the new scan marker. Current cards use the fresh
scan and retain original AI dispositions where they actually exist.

The end-screen remaining budget shows **$0.73**. Technical display copies round
USD fields to two decimals; original accounting, receipts and cost calculations
retain USD0.7290314 remaining and USD0.2709686 accounted. No model calls or charge.

**Verification:**381 harness +70 UI +111 root=562 offline tests PASS. Nine new
phrase/span cases and two UI cases cover6-card grouping, exact offsets, sentence
previews, rejecting ill-fitting hints, applying suggestions to every occurrence,
new scan protection, legacy reproducibility and display-only rounding. An actual
saved-V1 AppTest verified6cards, sentence preview and$0.73 with zero socket calls,
no changed state, no counters or ledger changes. Native Safari verified6cards,
new-match labeling and the real sentence preview on the unchanged saved package.
No human choice, revision, approval, export or model execution was triggered.

[Phrase card](screenshots/d039/phrase-card.png) ·
[Sentence preview](screenshots/d039/sentence-preview.png).

All prior protected source/data/generated/private files and MEMORY.md were
hash-identical before continuity updates. Same current-run pointer, V1 draft,
raw review, failures, historical versions, credentials and ledger preserved.
Canonical implementation reuses the existing review/UI/harness; no framework,
service, dependency, prompt, model or corpus change. No Git publication. App8520:
Current run → Review. Stop for owner inspection.


## M2-D040 — Activity phases and recovered steps

**Owner scope (November 10, 2026):** Activity UI only; no model calls. Fold a recovered
failure into the successful action in the same run/version, retain a short recovery
note, and collapse finished phases while expanding the current version.

**Implemented:** the existing timeline now groups events under Research, Version 1,
Version 2, etc. The actual saved run is currently Version 2. Research (3 steps) and
Version 1 (2 steps, 1 recovered) start collapsed; Version 2 (human feedback, writing,
and independent review) starts expanded. Expand any phase to inspect its steps.
The original rejected Version 1 response is shown once as a successful writing step:
“Passed after the heading-citation rule update; no rewrite.” It has a green check,
not a red failure. Original events/failure history remain unchanged in Technical details.
Only a later success of the same action/version folds prior failed_safely events;
unresolved failures, unrelated failures and conflicts remain visible. A normal retry
uses different wording and never claims that no rewrite occurred.

**Verification:** all **77 UI tests PASS**, including seven focused phase/recovery
regressions. Socket-blocked AppTest on the actual saved Version 2 verified phase
expansion, recovery wording, no recovered red icon, zero network calls, and unchanged
state/capture/accounting. Native Safari verified defaults and manually expanded
Version 1 to inspect the recovery. All 736 pre-existing protected file hashes match,
including saved drafts, reviews, events, budget/receipts, datasets, credentials and
MEMORY. No model calls, source/dataset changes, dependency additions, owner wording
choices, approval, Git staging/commit/push or runtime dependency on workspace.
The normal homepage performed its existing read-only source checks on reload;
this was not inference. Desktop screenshot QA only; no new mobile verification.

Screenshots: [Default phases](screenshots/d040/phases.jpg),
[Expanded recovered step](screenshots/d040/recovery.jpg).

**Navigation:** http://127.0.0.1:8520 → Current run → Activity. App restarted with
updated UI. Stop for owner review; package content still awaits human acceptance.


## M2-D041 — Direct current-version approval and restored acceptance

**Owner decision (November 10, 2026):** accept the version being reviewed as-is,
record that decision and update its status. Wording choices are instructions only
for an explicitly requested new version. Approval must not force V2→V3 or another
wording-card pass. A later requested revision remains optional. Scope: current
version UI, existing three-revision limit, no new history selector or model calls.

**Implemented:** the Package acknowledgement explicitly accepts current wording,
including flagged phrases. Approve package records keep-wording dispositions that
supersede earlier rewrite intentions without changing a single draft character.
Earlier choices remain in the decision event history; the receipt records the
prior decision digest, accepted decisions, exact content/review binding, version,
time and internal-only status. Previewing or checking acknowledgement does not
persist decisions; explicit approval is the committing action. This works for
current V1–V4. Existing authoritative evidence, launch and complete-current-review
checks remain; approval never publishes and does not expand execution budgets.

Approval stays bound to its accepted text/disposition while the owner prepares
possible future rewrite choices. Those choices alone do not revoke approval or
change text. A generated or manually edited version must establish its own approval.
Protected decision/approval receipts restore the exact approved status on reload;
stale bindings, tampered content/evidence, Hold and publicly readable receipts are
rejected. The new acknowledgement has a distinct review-bound key, so a previously
checked generic checkbox is not reused as new accept-as-is consent.

**Actual saved run:** the owner's Version2 internal approval receipt already
existed before this change. It was previously not restored into the visible status.
The updated app restores that genuine receipt and shows **Package approved for
internal use** and **Your approval of Version 2 is recorded**. Repeat approval
controls are hidden. No new owner approval, wording decision, revision or model call
was made by the assistant. Version3 remains available only on an explicit request.

**Verification:**387 harness +79 UI=**466 tests PASS**, including6 new acceptance/
receipt tests and2 new app regressions. All current versions, no-acknowledgement,
prior rewrite/occurrence overrides, preservation of decision history and draft
bytes, later revisions, approval persistence and policy failures covered offline.
Actual saved-V2 socket-blocked AppTest restored the pre-existing receipt with
zero network and unchanged run/capture. Native Safari verified approved status,
all five formats, confirmation and exports; no approval/revision/export clicked.
745 pre-existing protected file hashes match (drafts/reviews/choices/receipts,
budget, sources, credentials, MEMORY). Diff whitespace PASS. One initial test run
used an isolated environment missing jsonschema; the complete rerun used the
existing UI environment with that package, with no installs. Root ingestion tests
were not rerun for this approval-only change. No new mobile verification.

Screenshots: [Approved Version2](screenshots/d041/approved.jpg),
[Recorded approval](screenshots/d041/confirmation.jpg).

App restarted on http://127.0.0.1:8520; refresh → Current run → Package.
No Git staging/commit/push or MEMORY append. Stop for owner inspection.


## M2-D042 — Two-column Current run and shared actions panel

**Owner scope (November 10, 2026):** UI only. Current run uses the Home-style
65%/35% grid: tabs/content left, shared status/actions right on every tab; remove
the top status card, stack at narrow widths, supply one screenshot per tab.

**Implemented:** Current run now uses the full page width rather than nesting
inside the old detail column. The right panel holds real status, current version,
revisions used, cents-formatted budget left, all five deliverable statuses, existing
review/recovery controls, as-is approval, Markdown download/Copy all and optional
next-version action. Existing UI handlers were moved/reused; no new orchestration,
model behavior or execution policy. On approved Version2 the primary action is
Download Markdown, with all five deliverables Approved and optional Create Version3.
The left Package tab retains full-draft View controls. Existing Review notes/choices
feed the same bounded revision command now placed in the right panel. Direct as-is
approval is independent of that optional revision, as approved in D041.

The old package-run top status card is absent. At <=800 CSS pixels, the columns
stack with status/actions first and tabs below. Native responsive reflow was checked
using a resized Safari window and increased browser zoom, then restoring normal
zoom and the prior window size. This verifies narrow CSS reflow, not physical-device
coverage. Dark palette and Home header alignment remain. Original non-package legacy
views are outside the requested package-run redesign.

**Verification:** **81 UI tests PASS**, including two new shared-panel/layout tests.
Existing approval, explicit revision, retries, recovery and tab/navigation checks
remain passing with sockets blocked. Actual saved-V2 AppTest verified the shared
panel, five Approved statuses, $0.71 display and Download on Activity/Review/Package;
zero network, unchanged state/capture/accounting, genuine owner approval restored.
Native Safari verified all three desktop tabs and stacked narrow reflow. No choices,
approval, revision, generation, downloads or exports were executed during visual QA.
745 protected file hashes unchanged: saved run/drafts/reviews/decisions/approval,
budget, accepted sources, credentials and MEMORY. Whitespace diff check PASS.
No dependencies, source edits, model calls, Git staging/commit/push or workspace
runtime dependency. Broader non-UI suites were not rerun for layout-only work.

Screenshots: [Activity](screenshots/d042/activity.jpg),
[Review](screenshots/d042/review.jpg), [Package](screenshots/d042/package.jpg),
[narrow status panel](screenshots/d042/narrow-top.jpg),
[tabs below the panel](screenshots/d042/narrow-tabs.jpg).

App restarted on http://127.0.0.1:8520. Refresh → Current run. Current Version2
remains approved for internal use; V3 remains optional. Stop for owner inspection.
