# M2 - Autonomous GTM agent implementation plan

## Owner acceptance and scoped Git sync — 2026-11-08

Owner described the completed UI as a good milestone and explicitly requested Git
sync. The real inventory/brief UI and its source-access/presentation refinements
(UI-D002 through UI-D006) are **OWNER ACCEPTED / CLOSED** for this bounded slice.
UI-D001 is preserved as design history. This accepts registry-driven discovery,
read-only source checks, launch-aware brief selection and the reviewed layout;
it does not accept M2.3b content or authorize agent/Writer/Reviewer integration.

Publish only the canonical UI code/configuration, isolated locked Streamlit profile,
UI/source tests and supporting design/setup/acceptance records after exact-diff,
confidentiality, reproducibility and private-visibility review. Unfinished Writer
experiments, credentials, workspace, generated receipts and environments remain
local. No source writes, inference or next milestone is authorized. This latest
owner instruction supersedes earlier UI-only pending-review/no-publication text;
previous verification and audit history remain intact.


## Homepage refinement — 2026-11-08

Owner authorized the six presentation refinements and real per-source access checks.
[UI-D003](ui-inventory-implementation.md) records local technical PASS:299offline
checks, complete PMM read, matching PDFs and234unchanged operational values. No
agent/generation/Reviewer integration, model adoption, new dependency, source write,
M2.3b acceptance or Git sync. Stop for owner review; main roadmap remains unchanged.


## Scoped real inventory delivery — 2026-11-08

Owner authorized building the real inventory/brief homepage ahead of the remaining
Reviewer work. [UI-D002](ui-inventory-implementation.md) records canonical files,
source authority, isolated Streamlit setup and actual technical-PASS verification.
Registry discovery, live Notion dates/readiness, source links and brief selection
now work locally; this is only the discovery/brief slice of integration. Full
agent/Writer/Reviewer/revision/export integration is not implemented or authorized
by this checkpoint. M2.3b generation/content acceptance remains pending. Stop for
owner review; do not infer paid calls, model adoption, next milestone or Git sync.



## Owner acceptance and Git sync authorization — 2026-11-06

**M2.2 OWNER ACCEPTED / CLOSED.** The owner explicitly accepted the completed
research and harness repairs and directed Git sync. This includes the original
US research checkpoint, H-01/H-02/H-03 repair/comparison, and UK/India/controlled
readiness-failure validation. The original technical report and its measurements
below remain unchanged; earlier pending-review and no-publication statements are
historical and superseded only for this acceptance and authorized private sync.

M2.3a content contracts were already owner accepted and are included in this sync.
No live rerun, source/dataset change, final model adoption, full M1.5b.4 acceptance,
M2.3b implementation/generation, Reviewer or UI is authorized. Next: present the
M2.3b generation prompt and exact inputs for owner review before execution.

Date: 2026-11-06 (America/Los_Angeles).
The [north star](northstar.md) governs the goal; [milestones](milestones.md) records
execution authority and formal acceptance. This plan owns the consolidated current
state, remaining risks and delivery priorities. Detailed checkpoint reviews below
retain their original verification evidence and historical boundaries.

## Current state and owner-selected delivery priority - 2026-11-06

Latest increment: owner approved M2.3a five-template design with three refinements
and authorized local definition/validation. [Content-contract review](m2.3a-content-contracts-review.md):
five JSON configurations, shared structural/evidence-reference validator and12new
tests implemented;186offline tests PASS. No generation/Reviewer/UI implemented.
M2.3a OWNER ACCEPTED / CLOSED (2026-11-06). Earlier next-M2.3 wording below
is refined to M2.3a definitions → M2.3b LinkedIn → M2.3c Reviewer/revision.

**Research foundation working; GTM content generation, Reviewer and user experience
remain to be built.** The model chooses permitted next actions; LangGraph retains
state; the harness enforces supported-task admission, evidence authority, launch
permissions and execution limits. One Cherry Float task, US/UK/India, explicit
scenario date and flavor_discovery objective. Publishing always remains disabled.

Owner direction: **complete the usable MVP first, then optimize measured cost and
latency.** This supersedes the earlier recommendations to perform another context-
selection change or cache-measurement checkpoint before drafting. Preserve the
existing repair; do not weaken correctness, launch restrictions or required review
for speed. Cache instrumentation, context pruning, search tuning, framework changes
and extra hosted comparisons are not authorized by this documentation update.

### Completed work and acceptance distinctions

| Area | Current result | Acceptance / evidence |
|---|---|---|
| Source datasets | Product Brief v0.2, synthetic PRD v0.3, PMM Brief v0.2, nine calendar milestones and 12 readiness records | Owner accepted; source authority remains distinct from fictional operational permissions. See [dataset records](milestones.md). |
| External connectivity | Anonymous Drive PDF download/integrity checks; read-only Notion PMM/calendar/readiness; Pinecone authentication and storage checks | M1.5a owner accepted; [connectivity evidence](m1.5-connectivity-validation.md). Drive distribution is not a registered agent action. |
| Document/evidence preparation | Two PDFs, five extracted pages, 45 evidence chunks; focused embedding_text separate from full evidence_payload | M1.5b.1/B2/B3 owner accepted; full M1.5b.4 acceptance remains open. |
| Product retrieval | Semantic top-five search plus at most five supporting-reference targets, one hop; full citations, qualifications and authority returned; incomplete evidence explicit | [Retrieval tool](product-evidence-retrieval-review.md) owner accepted; fixed direct ranking 7/8, expected combined evidence coverage 8/8, with one response still explicitly partial for extra references. |
| Operational tools | Structured Notion reads and deterministic launch/date checks | [Notion tools](notion-launch-checks-review.md) owner accepted; frozen dates alone do not grant availability or approval. |
| Harness foundation | Registry, protected state, action validation, budgets, replay protection, clarification, fresh-run replacement/reset | [M2.1](m2.1-foundation-review.md) owner accepted and published. |
| Live autonomous research | Provisional Qwen/Qwen3-30B-A3B-Instruct-2507 selects tools/queries/order; actual actions observable | [M2.2a US](m2.2a-live-research-review.md) OWNER ACCEPTED / CLOSED (2026-11-06). |
| Harness repair | Reversible deduplicated model context; objective-specific completion; adapter identity/budget cleanup | [Repair](m2.2a-harness-repair-review.md) OWNER ACCEPTED / CLOSED (2026-11-06). |
| Live restrictions/failure | UK asks for availability clarification; India check triggers harness Hold; locally unavailable readiness triggers clarification | [M2.2b](m2.2b-live-restrictions-review.md) OWNER ACCEPTED / CLOSED (2026-11-06). Failure was simulated locally with a live model, not an observed provider outage. |
| Content contracts | Five directly loaded JSON templates; shared model envelope, evidence reference validation and advisory targets | M2.3a [implementation](m2.3a-content-contracts-review.md) OWNER ACCEPTED / CLOSED (2026-11-06). No actual drafts/review yet. |

Latest executed verification: **186 offline tests PASS** (89 root, 23 projection,
74 agent/adapter), including12new content-contract tests. Earlier M2.2b clean-copy
74 PASS without data, .env, workspace or inherited credentials remains historical;
M2.3a configuration reproduction is recorded separately in its review. Approved datasets and historical audit
artifacts remain unchanged. New required implementation/docs occupy canonical
repository locations; ignored audit records/workspace are not product dependencies.

### Context usage and caching: measured facts versus future options

The repaired US run used **80,202 total input tokens across five calls**, versus
188,689 in the original run (57.5% fewer). Its largest single input was **34,326**.
Fourteen full evidence packets remained intact. Model-chosen queries differed;
this is one observed comparison, not a controlled quality/cost benchmark. A separate
same-action offline replay measured 59.63% fewer request bytes, not hosted tokens.

| Turn / proposed action | Input tokens |
|---|---:|
| Check launch | 2,214 |
| Read PMM Brief | 3,525 |
| First product search | 13,628 |
| Second product search | 26,509 |
| Finish | 34,326 |

Current model input pools duplicate objects and reconstructs complete evidence, but
still carries the entire normalized 102-block PMM Brief and accumulated packets.
It does not yet select only stage-relevant PMM sections/fields. Full evidence stays
in harness state; embedding_text is a vectorization input, not automatically the
complete model prompt. No target token budget or further savings are claimed.

The read-only review found three distinct mechanisms:

- **Provider prompt caching:** reuse computation for identical prompt prefixes;
  potential latency/billing benefit, not durable memory or a larger context window.
  Nebius documents automatic, best-effort caching and reports
  usage.prompt_tokens_details.cached_tokens. Our adapter currently retains total
  usage but discards this detail. Therefore 80,202 is not a demonstrated uncached-
  token bill. Qwen-specific cache hits and applicable cached-input pricing have not
  been verified. See [Nebius cached tokens](https://docs.tokenfactory.nebius.com/cached-tokens)
  and [context-window distinction](https://platform.claude.com/docs/en/build-with-claude/context-windows).
- **Context handoff / prompt chaining:** supply the evidence/guidance relevant to
  a chosen action; a future Reviewer receives the draft, supporting evidence and
  restrictions rather than needing every research-turn detail. This remains a
  design option, not an implemented handoff contract or fixed action sequence.
- **LangGraph state:** application-owned evidence, permissions, progress and run
  lifecycle; preserving state does not automatically place all state in a model call.

Hint-only review: the inspected reference commit
0e2680c2bcefe92c968825c10205907098873fcd returns compact source-labeled passages,
uses a main DeepAgent and Reviewer delegation, and does not explicitly configure a
custom prompt cache or fixed chain. Its pinned DeepAgents 0.6.7 supplies automatic
conversation summarization; explicit Anthropic cache middleware skips other
providers. These are framework capabilities, not measured savings demonstrated by
that project. No reference implementation or prompts were copied or executed.
Sources: [reference agent](https://github.com/The-Gen-Academy/3D-GTM-Agent/blob/0e2680c2bcefe92c968825c10205907098873fcd/src/gtm_agent/agents/main_agent.py),
[pinned framework](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.6.7/libs/deepagents/deepagents/graph.py).

### Remaining risks and planned verification

| Risk / limitation | What must still be demonstrated |
|---|---|
| Search may miss supporting claims | Preserve the original 7/8 direct-ranking miss and explicit reference-cap limitations; do not treat search results as complete evidence. No new search tuning planned. |
| Correct evidence may yield incorrect wording | Drafts must preserve scope, qualifications and factual support. Valid claim IDs and intact packets do not prove prose entailment. Verify during M2.3. |
| Research permission checks do not prove generation enforcement | Draft/revise admission must enforce computed launch restrictions and prohibit unsupported availability claims. No draft action exists yet. |
| Reviewer effectiveness unproven | A separate call must identify meaningful defects, produce actionable critique and require correction; changed drafts need fresh review. Verify during M2.3, not by counting calls. |
| Limited live coverage | Existing bounded paths passed; live clarification continuation, human feedback/revision and broader service-failure behavior remain untested. One injected readiness failure is not every outage. |
| Repeated demo operation | Generate again/Reset passed offline; integrated live UI must discard prior review/acceptance, reject stale IDs and remain within budgets. |
| Context overhead and cache measurement gap | Repeated comprehensive context remains sizeable. After the usable build, measure total/cached tokens, latency and applicable prices before choosing changes. No claim of optimality or guaranteed cache hits. |

Frozen corpus/version changes, production approval lifecycle, generic products,
public research/Tavily and new infrastructure remain outside the current MVP.
Qwen is provisional; final adoption has not been recorded. Existing test passes do
not establish universal prompt-injection safety or production reliability.

### Remaining work and stop boundaries

| Step | Intended deliverable | Current authorization / status |
|---|---|---|
| Research closure / publication | Owner review of M2.2a, repair and M2.2b; scoped Git sync after credential/confidentiality/diff review | M2.2 OWNER ACCEPTED / CLOSED (2026-11-06); reviewed private Git sync authorized with accepted M2.3a. Full M1.5b.4 acceptance remains separate. |
| M2.3a | Define all five content contracts and shared validation, separate hard/soft rules and protect review ownership | OWNER ACCEPTED / CLOSED (2026-11-06); no generation. |
| M2.3b | Generate one US LinkedIn draft against the accepted contract with launch/evidence/CTA constraints | Next proposed build; not started or authorized. |
| M2.3c | Independent Reviewer critique → bounded revision; preserve evidence and require fresh review after changes | Not started; separate authorization required. |
| M2.4 | Campaign brief, LinkedIn, email, short blog, ad variations; Streamlit evidence/review display, human feedback, Generate again, Reset and export | Not implemented; separate milestone authorization required. |
| M2.5 | End-to-end US/UK/India/failure/feedback demonstration, sanitized observability, submission document and <=5-minute video | Not implemented; separate authorization required. Private repository must be accessible to course reviewers. |
| After usable MVP | Measure cache hits, total tokens, latency and billing; make only worthwhile focused optimizations | Deferred, not an extra mandatory platform milestone or permission to run calls now. |

Owner accepted M2.2 and authorized reviewed private Git sync with the already
accepted M2.3a on 2026-11-06. This acceptance commit checkpoints the research
adapters, repairs, prompt, tests, five templates/shared validator and supporting
documentation, based on published parent d1aa17cb00f8e959a83cf21bb7749668cd2a315b.
No new generation, provider call, dataset/dependency change or MEMORY append is
authorized. Publication does not authorize M2.3b execution.
Saving owner-selected priorities is not formal milestone acceptance or a final
model/architecture change. Proposed next action is review of the M2.3b prompt/inputs and bounded generation
authorization, with publication handled by explicit scoped approval. Earlier
no-template implementation descriptions are superseded only for completed M2.3a.

## M2.2b authorized execution/result - 2026-11-06

Owner explicitly approved one live UK, one India and one controlled tool-failure
case with the repaired harness, unchanged prompt/provisional Qwen and existing
limits. [Readable validation](m2.2b-live-restrictions-review.md): TECHNICAL PASS,
owner acceptance pending. UK chose check_launch → clarification; India chose
check_launch then harness Hold; locally unavailable readiness caused check_launch
→ clarification. Permissions remained false; zero drafts/searches.174offline tests
PASS; no runtime/dependency/source change required. Original US results preserved.
M2.2 research acceptance and M2.3 execution require owner review/authorization;
no more live runs, context tuning, drafting/Reviewer/UI or Git sync inferred.

## Latest bounded repair result - 2026-11-06

Owner approved the H-01/H-02/H-03 correction and one new US comparison.
[Repair review](m2.2a-harness-repair-review.md): TECHNICAL PASS, owner review pending.
State-derived focused model context, objective-specific completion and adapter/run
cleanup implemented;166tests PASS. One observed US comparison passed with80,202
input tokens versus188,689(57.5% reduction),same5turns/two searches,14 intact packets,
computed Proceed,publishing false. Original baseline/audit preserved. No additional
hosted cases,generation/Reviewer/UI or Git publication. Full M2.2 still incomplete.

## Product experience and shared vocabulary

The MVP is a guided application for supported GTM tasks. Its initial visible option
is Coca-Cola Cherry Float - GTM Package Preparation (display wording can be refined).
The user selects the supported use case, market, explicit evaluation date and a
supported campaign objective. The backend validates the selection before creating
an agent run. An optional creative instruction cannot change product/source scope,
market/date, launch permissions or supported actions.

| Concept | Meaning | Owner |
|---|---|---|
| Supported-use-case registry | Which GTM requests the application supports and their approved product/source bindings, input constraints and outputs | Maintained code; exposed directly through the UI |
| Current run | One session task with its current package, progress, unresolved conditions and result; no browsable run history | Harness-owned runtime/session state; explicit user generate/revise/resume/reset controls |
| Action/tool registry | Which operations the selected agent run may request and how their arguments/handlers are validated | Maintained code and harness |

A registered use case is not an in-flight brief. Reading a Notion PMM Brief does not
create a queued job. There is no background discovery/polling, scheduling or global
work queue in this MVP. These distinctions must remain explicit in code and UI.
Do not introduce a registry service, product database or generic onboarding framework.
Reuse existing source bindings and validation; do not maintain duplicate launch schedules.

## Decision record

| ID / date | Decision / status | Rationale | Alternatives considered |
|---|---|---|---|
| M2-D001 / 2026-11-06 | Owner agreed: harness-owned supported-use-case registry, direct UI selection and backend validation before model/tool calls | Guide the user to supported work; product existence and scope are deterministic | Model-mediated registry discovery deferred; unrestricted product requests excluded |
| M2-D002 / 2026-11-06 | Owner agreed: distinct new-run identities, revision and clarification resume; retention behavior superseded by M2-D004 | Repeatable demos without inheriting approval | Earlier keep-previous-result proposal superseded; durable history/queue deferred |
| M2-D003 / 2026-11-06 | Owner agreed to reviewed refinements: one main GTM Agent plus Reviewer, five delivery checkpoints and conservative restricted-market drafting | Reach a visible complete experience while preserving accepted permissions | Eight separate gates consolidated; optional restricted-market internal drafts deferred |
| M2-D004 / 2026-11-06 | OWNER APPROVED: one current package, Generate again replaces it, Reset demo clears local session task state; no draft archive/run browser | Keep the demo simple while preserving fresh-run isolation and replay protection | Retaining previous results and selecting historical runs removed from MVP |
| M2-D005 / 2026-11-06 | Implemented within owner-approved bounded M2.1 plan; acceptance pending: one flavor_discovery objective,12 decision turns/four searches, structural research completion and offline-only adapters | Concrete testable foundation before live variability | Broad objective catalog and live-model testing deferred |
| M2-D006 / 2026-11-06 | Implemented pending review: isolated tools/agent_foundation environment; original root profile restored unchanged | Accepted preparation manifest pins root metadata/lock; preserve historical evidence bindings | Updating old hashes or weakening validators rejected; existing isolated-tooling convention reused |
| M2-D007 / 2026-11-06 | OWNER APPROVED: adapt the owner-provided RAG prompt structure for LaunchLens research; implement prompt asset only. Qwen/Qwen3-30B-A3B-Instruct-2507 approved provisionally, not as final model selection | Reuse familiar grounding conventions while allowing model-selected actions under harness enforcement; prior tool smoke test supports a bounded trial | Unchanged RAG answering prompt rejected; live adapter/call budget, final model choice and generation/Reviewer prompts deferred |
| M2-D008 / 2026-11-06 | OWNER APPROVED bounded M2.2a: native Qwen tool adapter, accepted read-only sources, one US flavor_discovery run;12-turn/four-search cap. Implemented TECHNICAL PASS, acceptance pending | Verify real model-selected research under existing harness, then stop for readable review | Scripted live sequence, unrestricted app access, additional live cases/reruns and drafting deferred; observed context cost requires review |
| M2-D009 / 2026-11-06 | OWNER APPROVED H-01/H-02/H-03 bounded correction and one US comparison; implemented technical PASS, owner acceptance pending | Deduplicate model context without losing evidence; enforce selected-objective completion; clear adapter state/budgets on explicit run replacement/reset | Raw-history continuation, unrelated-claim completion and single-use adapter-only lifecycle rejected; no corpus/stack change or additional live run |
| M2-D010 / 2026-11-06 | OWNER APPROVED M2.2b: one UK, one India and one locally injected readiness-failure live case; implemented technical PASS, acceptance pending | Verify model-selected clarification and harness launch restrictions before drafting | Real service disruption, extra runs/resume, context tuning, new infrastructure and drafting deferred |
| M2-D011 / 2026-11-06 | OWNER-SELECTED DELIVERY PRIORITY: finish the usable MVP through bounded M2.3/M2.4/M2.5 checkpoints, then optimize measured overhead; current task documents state only | Preserve momentum toward the north star while retaining launch, evidence and review controls | Another pre-drafting context-selection/cache checkpoint deferred; no framework/provider switch, automatic milestone acceptance or implementation authorization |
| M2-D012 / 2026-11-06 | OWNER APPROVED M2.3a design and local definition/validation: five JSON contracts plus shared model envelope, hard structure/evidence bindings, advisory targets and explicit CTA/claim review rules; implementation OWNER ACCEPTED / CLOSED (2026-11-06) | Establish consistent creative deliverables while protecting factual authority and application-owned review/approval | Five unrelated envelopes, hard editorial lengths, model-owned approval, template embeddings and premature generation rejected; M2.3b LinkedIn/M2.3c review remain separate |

This supersedes the earlier instruction to preserve the previous result while a new
run executes. Planning approval does not authorize implementation or Git publication.

The model controls research/action choices within a validated task. The harness
controls admission, permitted actions, authoritative fields, budgets and completion.
Registered product existence is never inferred by the model. Later conversational
discovery could call the same read-only registry, but is not part of this MVP.

## Concrete user journey

1. Harness/UI lists supported use cases; currently one Cherry Float option.
2. User selects that case, US/UK/IN, an explicit scenario evaluation date and an
   allowed objective. The bounded M2.1 build plan supplies one initial objective:
   flavor_discovery - introduce Cherry Float's flavor and classic soda-float inspiration.
   Additional objectives require a separate scoped decision.
3. Backend validates the selection against maintained configuration. An unknown
   product/use-case ID (for example Nike), including a crafted backend request,
   is rejected before any model, Pinecone or Notion call. A failed request has no
   active agent run; its validation message may still be shown to the user.
4. A valid request creates a unique run ID and fresh state. Generate again replaces
   the current package after request validation; no previous run remains selectable.
   The agent receives the selected task, capability description and permitted actions.
5. The model chooses what to read/search next, interprets results and requests
   clarification, drafting, review, revision or completion. Tools supply evidence;
   the model cannot overwrite their results or supply its own approval verdict.
6. The harness checks every action. A successful readiness gate is required before
   promotional draft admission. Current initial policy: US proceeds when its records
   support it; UK asks for missing availability confirmation; India holds promotional
   drafts for pending authorization. These outcomes are computed from records,
   never hardcoded market-name routing. Human text cannot manufacture permission.
7. Permitted content is reviewed by a separate Reviewer call. Blocking findings
   prevent presenting the artifact as reviewed. Changes invalidate the relevant
   draft's prior review. Human acceptance is tied to the reviewed draft version;
   it cannot grant launch permission or publish anything.
8. UI shows the result, unresolved conditions, sources, actual actions and feedback
   controls. Source-backed restrictions remain in force during feedback revision.

The UI controls product/task selection; it does not prescribe research order or
search queries. Autonomous research/generation remains central to the north star.

## Run lifecycle and repeated generation

- Keep one current package only. No draft archive, run selector or previous-result
  fallback. Within the current run, retain only state/checkpoints needed for execution,
  bounded revision, review and replay protection; these are not a browsing feature.
- Generate again: validate the explicit user request first, discard the current
  package/task state and create a fresh unique run ID, evidence/readiness reads,
  budget, drafts and review status. Old feedback, review and human acceptance are
  not inherited. If generation fails or is held, show that current outcome; do not
  restore or mislabel the discarded package. Same inputs may produce similar wording.
- Revise with feedback: continue the current task, retain evidence/restrictions,
  change the intended draft and require fresh review of changed content.
- Resume clarification: continue the current paused task with new information;
  narrative confirmation cannot override authoritative operational permissions.
- Reset demo: explicit user action clears the current session task, drafts, feedback,
  acceptance, execution ledger and associated in-memory checkpoints, then returns
  to the initial guided form with no active run. It makes no provider call and does
  not modify the maintained registry, accepted local datasets, Pinecone or Notion.
  It does not delete hosted LangSmith traces or previously exported files.
- For the synchronous MVP, disable Generate again and Reset demo while execution
  is running; no background cancellation system. A discarded/reset run ID cannot
  resume or repopulate the current session. Only explicit user controls can replace
  or reset a task; the model cannot reset its budgets or hide a failed review.
- Replaying a completed action in the same run returns its recorded result;
  the same action ID with changed arguments is rejected. An uncertain in-flight
  action must not be blindly retried. UI rerenders must not start execution.
- Session action IDs/results provide replay protection, not crash-proof exactly-once
  execution across restarts. No durable history or production recovery service.

## State, authority and observability

State contains the validated request, scoped evidence and qualifications, harness-
owned launch decision, creative direction, versioned drafts, Reviewer results,
human feedback/acceptance, action ledger, execution status and remaining budgets.
Use explicit ownership and validated updates, not arbitrary model-dictionary merges.
Pinecone contains both public facts and labeled synthetic PRD intent; authority must
remain distinct. Notion PMM guides positioning; calendar/readiness supply fictional
operational permission; Reviewer evaluates proposed wording; human accepts drafts.

Preserve complete evidence packets in state. Focused model context must include
needed scope, qualifications, citations and authority, including partial-reference
warnings. A valid evidence ID does not prove semantic entailment; Reviewer and human
review remain necessary. Retain the accepted search limits and disclosed ranking miss.

Events come from actual execution and include safe action/result identifiers,
outcomes and timing. No fabricated action history or private reasoning logs.
Instrumentation begins in M2.1; sanitized LangSmith delivery is connected in M2.5.
No automatic credential/full-payload tracing. Tracing failure cannot grant permission.

M2.1 implements the presented12-decision-turn/four-search limits; rejected proposals
consume decision turns and attempted searches consume search budget. Limits can be
lowered in tests, not expanded by the model. Two Reviewer rounds remain a proposal
for the later generation checkpoint, not an implemented Reviewer budget. Budgets are bounded per
execution/feedback continuation; no automatic research-transport retry or unlimited
model repair loop. End meaningfully: completed for the authorized stage, needs
clarification, held or failed safely. M2.1 simulation completion is not a real GTM
package, review or demonstration of live-model autonomy.

## Five progressive implementation checkpoints

| Checkpoint | Bounded work | Owner-review evidence / exit condition |
|---|---|---|
| M2.1 - Foundation | Minimal LangGraph loop; supported-use-case and action registries; validated requests; state ownership; one-current-run replacement/reset and isolation; replay protection; scripted model/safe tool fixtures; bounded terminal states | Readable simulation, unknown-product rejection before calls, invalid-action/injection attempts blocked, completed-action replay invokes handler once, replacement/reset clears prior task state without external writes, old IDs cannot resume, all tests appropriate to scope pass |
| M2.2 - Live autonomous research | Approve one provisional Nebius model/live budget; connect existing read tools; model chooses queries/order within registry scope | Actual action history/evidence and computed US/UK/IN behavior; incomplete evidence/failures explicit; no copy generation yet |
| M2.3 - One reviewed LinkedIn draft | Permitted US draft, independent Reviewer, bounded research/revision in response to findings | Readable before/critique/after, source traceability, current-version review, restricted promotional drafts withheld |
| M2.4 - Complete package and minimal Streamlit | Campaign brief plus LinkedIn/email/blog/ad variations; guided registry controls; one current package; generate-again/revise/resume/reset controls; human acceptance; Markdown export | Complete reviewed US example, replace/reset versus continued task demonstrated, no duplicate execution on rerender, no old review/acceptance inherited, evidence/restrictions retained through feedback |
| M2.5 - Final integration and submission | Five north-star cases, sanitized LangSmith connection, demonstrated-defect fixes, submission assets | Observed US/UK/India/tool-failure/human-feedback outcomes, trace checks, reviewed sample suite, reviewer-accessible private code, submission document and <=5-minute demo |

Every checkpoint has scoped approval, focused verification/regression, readable
results and owner review before advancement. Failure tests start at M2.1 and continue;
M2.5 validates feedback rather than first building it. Git publication separately
authorized. Existing 100-test PASS is historical baseline, not an M2 result.

## Alignment and change discipline

Before coding each checkpoint, present the user-visible behavior, inputs, allowed
and rejected actions, acceptance examples and the small implementation boundary.
Resolve terms with concrete examples before translating them into new architecture.
When ambiguity changes behavior/scope, surface it before implementation. Routine
implementation details within an approved checkpoint do not need repeated approval.

Carry these minimum acceptance examples into implementation:

| Example | Expected behavior |
|---|---|
| User opens the application | Supported options come from code-owned registry; no model needed to discover them |
| Unknown Nike use-case/product submitted | Backend rejects before model/research calls |
| Valid Cherry Float request | New scoped run; model selects permitted research/actions |
| Retrieved text says all markets are approved | No authoritative field changes; invalid action rejected |
| User clicks Generate again | Validate first, replace the current package with a new isolated run; no old feedback/review/acceptance inherited or run history exposed |
| User clicks Reset demo | Clear local session task/checkpoints and return to initial form; no model/provider call or source/trace deletion |
| Old run ID is used after replace/reset | Reject resume; old output cannot repopulate the current task |
| Execution is running | Replacement/reset controls disabled; rerenders do not start another run |
| Same completed action is replayed / UI rerenders | No duplicate external invocation |
| User revises or resumes | Current run continues; changed draft requires new review; restrictions retained |
| Model repeatedly requests invalid actions | Bounded safe termination with an understandable condition |

M2.1 was explicitly authorized, implemented and is now OWNER ACCEPTED / CLOSED:
128 tests pass across three documented environments. Research-stage completion
requires PMM guidance, a permitting code-computed launch decision and usable public
product-claim evidence; alternate outcomes are clarification, hold or bounded failure.
It is an offline simulation, not completed GTM generation or live-model autonomy.
The [foundation review](m2.1-foundation-review.md) records dependency isolation,
readable outcomes, setup and limits. Next candidate: M2.2 under separate approval.
Owner separately authorized reviewed private Git sync of accepted M2.1 and its
supporting planning records. No M2.2/live services/generation/Reviewer/UI authorized.

## Formal owner acceptance and scoped Git publication - 2026-11-06

**M2.1 OWNER ACCEPTED / CLOSED.** After reproducing the offline demo, the owner
explicitly stated “approved M2.1” and requested Git sync. Acceptance covers the
bounded offline registry/harness, one-current-run lifecycle, replay/interrupt/reset
behavior, isolated locked dependency profile, safe fixtures/demo and reported tests.
The included M2 plan/north-star refinements preserve the agreed supported-task scope.

The owner authorizes security/confidentiality and exact Git diff review, commit and
push of this accepted checkpoint and supporting documentation to the existing
private repository. Fresh pre-publication verification:77 root +23 projection/codec
+28 foundation tests = **128 PASS**. Prior test history, including the dependency
hash failure and its isolation resolution, remains preserved. Source datasets,
accepted tool behavior, root/embedding profiles and generated evidence remain intact.

This does not accept full M1.5b.4 or authorize M2.2, live model/source calls, drafting,
Reviewer/UI, LangSmith delivery, further dependency changes or ongoing publication.
Next candidate: M2.2 live autonomous research, after provisional model and bounded
live-call scope are approved. Stop after verified private sync and report next steps.


## Approved research prompt implemented - 2026-11-06

Authority: owner approved the displayed LaunchLens research prompt and its registered
application/GTM-registry additions, then instructed "lets first implement the prompt".
This is a prompt-only increment within M2.2 preparation, not live-agent completion.
The owner also approved Qwen/Qwen3-30B-A3B-Instruct-2507 as the provisional model;
provider guidance and the prior smoke test do not establish GTM research quality.

Canonical maintained asset: [research prompt](../../src/launchlens/prompts/research.txt).
It adapts the owner-supplied grounded-generation-prompt-v2.2.txt section structure
and grounding principles, with explicit authorization to adapt that template only.
No Week 2 code, datasets, credentials or historical prompt files are modified.
There is one authoritative prompt copy; this document provides its operating notes.

The prompt describes Notion PMM/calendar/readiness, Pinecone product/PRD evidence,
and Drive PDF distribution without granting generic external-application access.
It distinguishes the supported-business-task registry from current work, uses exactly
the five existing research actions and makes model action choice versus harness
execution/permission/completion explicit. No fixed research sequence, unsupported
registry-discovery action, new status schema or summary-bearing finish argument.

Implementation boundary: a UTF-8 text asset only. It is not loaded by the accepted
offline harness yet. Live wiring must load this canonical asset, supply the validated
request, current evidence/outcomes, authoritative action contracts and remaining
limits, and preserve lower-trust data boundaries. Provider tool-call translation,
context-size handling and model behavior must be validated in separately approved
M2.2 work; the prompt does not implement or prove these behaviors. No environment
configuration, new dependency, integration, runtime loader or model call added.

### Readable example - illustrative, not an executed run

Input: Coca-Cola Cherry Float GTM Package Preparation; US; evaluation date
2026-12-14; flavor_discovery objective. The harness validates this selection first.
The model may choose any permitted research order, including checking launch early.

One valid proposed action:

```json
{
  "id": "research-flavor-01",
  "name": "search_product_evidence",
  "arguments": {
    "query": "Coca-Cola Cherry Float flavor and classic soda-float inspiration",
    "authority": "public_product_facts"
  }
}
```

Expected readable completion, conditional on actual successful source checks:
US draft preparation permitted under the simulation; public flavor/inspiration
claims traceable to PROD-002/PROD-003 with citations and qualifications; PMM audience
hypotheses remain unvalidated; publishing disabled; no marketing copy generated.
This would be a presentation of recorded research state, not an extra finish
argument or an observed autonomous result. The action remains finish with {}.

### Local verification and stop boundary

Prompt-only checks: UTF-8 readability, approved section/content preservation,
exact five-action names/argument fields and two search-authority values against
maintained registry contracts; example request/action accepted by the existing
validators; no obsolete Week 2 M7/M8 response contract or template placeholders.
Relative links, whitespace, ignore eligibility and protected-file/Git hashes are
checked at handoff. These are static/contract checks, not prompt efficacy tests.
No application suite rerun is necessary for an unconnected text asset.

Observed static/contract result: **PASS**. Ten prompt sections; all five action
names and exact argument fields match the registry; both search-authority values
match; example request/action pass existing validators; nine relative links resolve.
All84 protected baseline hashes outside the four authorized status/continuity edits
remain unchanged, including MEMORY, credentials, existing source/runtime profiles
and Git index. HEAD unchanged; nothing staged. Prompt is eligible for source control;
workspace notes remain ignored. Zero live calls, installs or behavioral test runs.

Prompt SHA-256: 2df27019194b29953336ec2f5701d10e69d087ebc28f0c79ef33abe8bc44c43c.

No live Nebius/Notion/Pinecone/Drive requests, dataset/profile changes, draft or
Reviewer generation, UI, tracing delivery, Git staging/commit/push or MEMORY update.
Next: separately approved M2.2 live adapter and bounded call budget, first one
readable US research run, then later UK/India/failure checks after review.


## M2.2a bounded execution - 2026-11-06

Owner approved minimal wiring and one live US research run. The maintained
[review](m2.2a-live-research-review.md) records actual actions, evidence, usage,
147 offline tests, setup and limitations. Native tool calls selected launch check,
PMM read, two different product queries and finish; code-computed Proceed with
publishing false. No drafting/Reviewer/UI. All14 packets matched approved bytes.
Measured188,689 input tokens exposes full-history context overhead; proposed
context projection is not implemented or approved by this result. Stop for owner
review before further live calls/cases or advancing. Full M2.2 acceptance pending;
full M1.5b.4 remains separate. Approved prompt and frozen corpus stay unchanged.


## Research harness audit - 2026-11-06, corrections proposed only

Owner requested a thorough implemented-path review before context changes. Fresh147
existing tests pass;10 additional offline composition probes made zero network
attempts. [Canonical audit](m2.2a-harness-audit.md) identifies H-01 repeated full
model context,H-02 missing objective-specific completion coverage,and H-03 missing
live adapter/session lifecycle integration. Prior observed US PASS remains scoped;
this is not full harness sign-off. No fixes or additional hosted execution performed.
Proposed next bounded checkpoint closes these with offline regressions and a readable
context example, then separately authorized one-US comparison. No approval inferred.
