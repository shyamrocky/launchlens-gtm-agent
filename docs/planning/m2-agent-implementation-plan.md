# M2 - Autonomous GTM agent implementation plan

Date: 2026-11-06 (America/Los_Angeles).
Status: M2.1 OWNER ACCEPTED / CLOSED (2026-11-06), following offline TECHNICAL PASS
and the owner-reproduced demo. See [foundation review](m2.1-foundation-review.md).
M2.2 and later checkpoints still require separate authorization. Historical planning
restrictions below are superseded only for this completed bounded foundation.
The [north star](northstar.md) governs the goal; [milestones](milestones.md) governs
execution approval. Existing accepted tools and datasets remain unchanged.

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
