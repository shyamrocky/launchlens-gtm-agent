Current publication checkpoint — November 11, 2026: owner requested Git sync of
M2-D059 after the completed app restart/local health check. Fresh verification:
730 offline tests PASS. No additional restart or live calls for publication.
[Publication scope](planning/repository-sync-2026-11-09.md#tracing-polish-publication--november-11-2026).
Earlier pending/restart/local-only labels below are dated implementation history.

# Optional LangSmith tracing

Owner authorized bounded observability on November 10, 2026 (M2-D056).
M2-D058 restart/health is complete; owner requested scoped private Git sync.
722 fresh offline tests pass; live child metrics after the latest repair remain
unverified. [Publication record](planning/repository-sync-2026-11-09.md#langsmith-observability-publication--november-10-2026).
Earlier restart/implementation labels below describe their dated handoffs.
This adds telemetry to the existing graph and direct Nebius adapters. It changes
no prompts, models, call limits, revision rules, validation, UI journey or budget.
No dependency changes: the isolated agent/UI environments already pin LangSmith.

## Configuration

The app reads `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`
from the repository's private `.env`; exported environment values take precedence.
Only `LANGSMITH_TRACING=true` enables tracing. Missing/blank keys disable export;
missing project uses LangSmith's `default` project. `.env.example` contains empty
placeholders. Never put a real key in version-controlled files. Restart the app
after changing configuration. Existing offline simulation sessions remain offline.

The implementation does not change `.env` or enable tracing for you. Enabling it
allows synthetic drafts/evidence to leave the computer for LangSmith. No saved
runs are replayed/backfilled and tracing does not provide missing resume support.

## Trace contents and identity

A root is named `{use_case_id} · {scope} · {run_id}`. Explicit scope type/value
is preferred; existing requests derive their scope from their own dimension IDs
(e.g. `market_id` becomes `market=UK`). A scope-free request uses `all`. Product,
use case, scope, actual launch decision and configured run model IDs become
metadata/tags. There are no hard-coded market branches in observability.

The root UUID is derived from the run ID, independent of session object identity.
Clarification Continue, review choices, Create next version and Try again attach
to that root. New runs create their root directly, with no preliminary read.
Same-process resumes use the cached root. Each live run's private artifact folder
stores `langsmith-trace-context.json`: schema, run ID, deterministic root ID, root
start time and dotted order only. It is created once with mode0600. Later processes
and UI actions load/validate those same identifiers and post directly; the exporter
never invokes `read_run` or `GET /runs/{run_id}`. A same-ID root POST on reattachment
is idempotent; it does not create a second trace. Root updates use minimal patch records on the supported `/runs/batch` ingestion
endpoint with one attempt. The original saved start time stays fixed and the latest
end time only advances, so latency includes human pauses and later resume segments.
The engine and UI share one exporter for each key/project/client configuration;
all observed redaction secrets are unioned, never discarded. Root metadata merges
known values: a null/stale snapshot cannot erase gate/model metadata. Authoritative
launch checks annotate the root immediately, including Clarify before interruption.

The context file is separate from graph checkpoints, approval/decision receipts and
accounting. Model inputs and strict saved-state schemas do not gain tracing fields.
Missing, invalid or unwritable context cannot fail a run: an in-memory identity is
used with a safe warning on invalid/unwritable files, which are never overwritten.
An older run with no saved context retains its deterministic trace ID, but its old
remote dotted order cannot be recovered without a lookup. Newly saved context is
stable thereafter. No historical traces are replayed or backfilled.

LangGraph node callbacks produce `node:decide`, `node:dispatch`, `node:clarify`,
`node:required_objective_evidence`, `node:required_review` and
`node:required_refine` when those nodes actually execute. A filtered callback is
used instead of the SDK's implicit full-state recorder. Native autotracing stays
disabled so it cannot bypass the privacy filter or duplicate roots.

Direct LLM spans are `controller`, `Writer`, `Reviewer`, `revision Writer` and
`citation repair`, with model ID, input/output/total token usage and elapsed
latency. Children are posted once, completed, including `start_time`, `end_time`,
parent/root IDs, type, outputs and metadata, rather than relying on a later child
PATCH. Callback completion remains safe across LangGraph copied contexts.

LLM outputs contain OpenAI-style `usage` (`prompt_tokens`, `completion_tokens`,
`total_tokens`) plus canonical `usage_metadata` (`input_tokens`, `output_tokens`,
`total_tokens`). The same canonical metadata is attached to the run metadata with
`ls_provider=nebius` and its actual request's `ls_model_name`. For current package
roles, input/output/total USD costs are explicitly estimated using the unchanged,
existing frozen profile rates and the actual returned usage. These fields do not
read/mutate ledger internals, reserve funds or change billing. Unknown usage/prices
produce no invented cost. See [LangSmith LLM metadata](https://docs.langchain.com/langsmith/log-llm-trace#provide-token-and-cost-information)
and [explicit cost fields](https://docs.langchain.com/langsmith/cost-tracking).
A `controller_action` span records its selected action and supplied short
business-purpose `why`; it does not request private chain-of-thought.

Tool/event spans cover `Notion read`, `Pinecone search`, `launch gate check`,
`risky-phrase scan`, `required claim fetch`, `human_interrupt`, `human_resume`,
`human review decision`, `exact-replacement apply`, `approval` and `download`.
These appear only when the associated operation executes. Every completed child
includes outputs; gate checks include `gate_decision`, evidence fetch/search steps
include `evidence_hit_count`, and scan lists include `hit_count`. Per-format executions are children of one lazy
`risky-phrase scan` parent for each execution segment, including nested harness
contexts. Its counters summarize scan invocations and returned hits; they are not
unique review-card counts. Splitting the pure scan by format preserves its original
result order, IDs, exclusions and decisions. No scans means no empty group.
Failed children
still include an end time and a safe failure status. Exact-replacement
preparation may execute more than once and may have no replacements selected.
Approval/decisions are observed after successful UI commands, without serializing
receipts. Download uses Streamlit's deferred-data hook to observe the request
rather than rendering a button; exported bytes, labels and `on_click=ignore`
(no rerun) are preserved.

## Failure isolation and privacy

Run execution only enqueues records with a nonblocking put. One daemon worker
per configuration performs sanitization and SDK/network work. The queue holds at
most 256 operations; overflow drops telemetry. There is no foreground flush, join,
retry or shutdown wait. Background HTTP timeouts are 2 seconds to connect and
5 seconds to read; transport retries remain disabled. Failed operations are dropped
individually. Later queued records continue, and a failed client factory may be
initialized for a later record; no permanent disable flag remains. A slow client
can lose traces but cannot hold up agent execution.

Failures produce a warning with a fixed operation/reason category, for example:
`LangSmith export failed: operation=create reason=timeout; later exports remain enabled`.
These warnings contain no raw exception message, stack trace, key, email, request
payload, project name or protected path. The in-memory failure count is diagnostic
only; it is not written to a run or ledger.
Delivery is best effort, not an audit system or a guarantee of complete traces.

Exported graph state uses an explicit allowlist. Ledger/spending/budget fields,
headers, credentials, receipt fields and private artifact paths are excluded.
JSON embedded in messages is sanitized recursively. Configured secret values and
email addresses are redacted from strings; arbitrary objects and exception text
are never serialized. SDK environment/runtime enrichment is disabled. LangSmith's
own key is used only by its authenticated client, never in trace payloads. No
other service credential, protected receipt or ledger file is uploaded.

## Offline verification and scope boundary

Maintained synthetic tests exercise actual graph/live adapters, clarification
resume, both revision origins, citation repair, real source adapter entry points,
SDK serialization, generic/scope-free metadata and restart reattachment. They
compare enabled/disabled model requests and package/accounting results, block
sockets, and inject missing keys, SDK failures, a slow worker and queue pressure.
UI regression clicks actual suggestion → Create next version → approval, checks
the receipt locally, and executes the deferred download request without a rerun.

No live LangSmith/model/source calls are part of implementation verification.
Restart and owner review are the next steps; recording, Git sync, fixes to known
content/reload limitations and further inference remain separately authorized.

## Changed files and checks — original M2-D056

- New exporter: `src/launchlens/observability.py`.
- Graph and call integration: `src/launchlens/agent_foundation.py`,
  `src/launchlens/live_package.py`, `src/launchlens/live_research.py`.
- Tool/UI hooks: `src/launchlens/launch_checks.py`,
  `src/launchlens/package_content.py`, `src/launchlens/field_revisions.py`,
  `src/launchlens/agent_run_ui.py`.
- Offline regressions: `tools/agent_foundation/tests/test_observability.py`,
  `tools/ui/tests/test_tracing_ui.py`.
- Setup/records: `.env.example`, `README.md`, `AGENTS.md`, this guide,
  `docs/planning/m2-agent-implementation-plan.md` and
  `docs/planning/writer-run-experience-review.md`.
- Local continuity only: `workspace/BUILD_CONTEXT.md` and
  `workspace/IMPLEMENTATION_PROGRESS.md`; no MEMORY append.

Full clean-copy verification: **709 offline tests passed** (478 harness,
117 UI, 114 root), followed by the added injected-credential provisioning test
and the affected adapter/UI suites. Final harness count is 479; the total is
**710 distinct passing tests**. All verification used a canonical temporary copy
without `.env`, private runs or workspace. Root document/chunk prerequisites were
regenerated there only; original generated artifacts were untouched.

Commands use `PYTHONPATH=src` and the existing Python 3.12 environments:
`python -B -m unittest discover -s tools/agent_foundation/tests`,
`python -B -m unittest discover -s tools/ui/tests`, and
`python -B -m unittest discover -s tests`. The root suite uses its original
`.venv`; harness/UI suites use `tools/ui/.venv`. No installations or lock edits.

## M2-D057 — Recoverable export and optional reattachment

Historical checkpoint: restart subsequently completed; owner then reported live
India root/children visible. M2-D058 below supersedes optional lookup and child
update behavior. Earlier diagnosis and verification remain historical evidence.

**Authority/status:** owner approved the bounded diagnosis fix on November 10,
2026. Implemented locally; restart/owner review pending. The app has not been
restarted and no new live connectivity/model/source call was made during this fix.

**Diagnosis evidence, preceding this implementation:** the running app read the
three private settings and reached the exporter. Its 500ms preliminary root lookup
timed out in reproduction at502ms; a longer lookup returned the expected missing
India root at952ms. The original exception was swallowed, so its exact contents
were unavailable. Separately, one owner-authorized synthetic connectivity trace
was accepted (HTTP202) and read back successfully in the configured US workspace.
Endpoint/key/project access worked. That single diagnostic write is separate from
the offline verification here and does not prove the revised exporter live.

**Change:** only `src/launchlens/observability.py` changes runtime behavior, confined
to telemetry delivery. Initial root creation skips lookup; progressed-run first
attachment retains optional lookup and original order when available. Lookup
failure falls back to same-ID creation. Each client/create/update failure is logged
using fixed safe categories and affects only that operation. Background timeouts
are2s/5s, with no SDK retry, foreground wait or requeue of failed operations.
Existing graph, adapters, prompts, models, validators, UI flow, revision allowance
and budget accounting remain unchanged. No automatic replay/backfill of the India
run or other saved work is implemented or executed.

**Offline regressions:** seven additional tests cover new-run no-lookup creation,
failed lookup with continued exports, a blocked lookup while an actual harness run
finishes, factory/create/update recovery and safe logging, expected missing roots,
and timeout/retry settings. Existing real graph clarification-resume and exporter
restart tests remain; the former asserts no lookup on either initial execution or
same-process resume, and the latter checks original dotted order after reattachment.
SDK serialization still intercepts HTTP, and injected error messages include fake
credentials, email, private paths and draft bodies that must never reach logs.
Existing UI suggestion→submit→approval→download remains covered; only its diagnostic
assertion changes to reflect recoverable failures instead of permanent disabling.

**Changed files for this fix:** `src/launchlens/observability.py`,
`tools/agent_foundation/tests/test_observability.py`,
`tools/ui/tests/test_tracing_ui.py`, this guide, the two existing planning status
documents, README and AGENTS. BUILD_CONTEXT/IMPLEMENTATION_PROGRESS are local
continuity updates; MEMORY is not appended. No environment, dependency/lock,
prompt/model/profile, ledger, saved response, checkpoint, receipt or approval edits.
Git sync and further inference are not authorized by implementation completion.

**Verification:**717 distinct offline tests PASS:486 harness (including24 focused
tracing tests),117 UI and114 root. The canonical temporary copy has no private
.env, saved runs or workspace. Root document/chunk prerequisites regenerated there
only. Installed-byte, protected-file, syntax, whitespace and documentation checks
accompany the handoff. Live delivery of this repair is not claimed; app restart
and owner inspection are next. The prior connectivity test already exists remotely
and was not repeated for implementation.

## M2-D058 — Completed child metrics and lookup-free saved trace identity

**Authority/status:** November 10, 2026. Owner reports India root/children visible
in launchlens-demo, but no child latency/tokens/cost, and a deprecated GET warning.
Owner authorized both fixes and regressions. Implemented locally; restart and owner
live inspection pending. No live trace/model/source calls or Git sync during this
implementation. Owner report establishes visibility, not correctness of old metrics.

**Evidence and scope:** app logs showed repeated child update failures. The old
SDK child-update path did not carry complete identity fields, while child creations
carried no end/usage until that later update. This repair posts each completed child
in one supported create payload, with timing, usage/cost and outputs together.
Root updates retain start time, type, name, trace/order and project identity.
The old exact HTTP error was not recorded; no specific remote rejection reason is
claimed. Both SDK serialization and copied callback contexts are regression-tested.

**Implementation files:** `src/launchlens/observability.py` implements completed
spans, canonical token/cost fields, safe summaries and persisted local trace context.
`src/launchlens/live_package.py` binds that context to the existing run store and
passes existing profile prices to telemetry; it does not read ledger data for costs.
`src/launchlens/agent_run_ui.py` passes the same store for decisions/approval/download.
No graph state, evidence/prompt/schema, model, validation, revision or budget changes.

**Tests:** updated `tools/agent_foundation/tests/test_observability.py` for completed
payloads and local context; new `test_trace_metrics.py` covers all five LLM roles,
end times/outputs, canonical tokens and USD estimates, source hit counts, exception
completion, copied callback contexts, installed-SDK wire payloads, an actual saved
review restore/revision with unchanged context bytes and zero lookup, invalid or
unwritable context fallback, and unknown usage. Existing clarification resume and
real UI suggestion→submit→approval→download flows remain covered. Lookup-specific
M2-D057 tests were replaced because the lookup code has been removed entirely.

**Limits:** applies to spans emitted after restart. Existing remote traces are not
rewritten; previously missing child completion/usage is not backfilled. Private
trace context is written only during subsequent authorized app use, not by this
implementation into the current saved run. Delivery remains bounded/best effort;
sidecar failure warns and falls back without blocking inference or approval.

**Verification:**722 distinct offline tests PASS:491 harness (including29 tracing
cases across the two tracing test modules),117 UI and114 root. Canonical temporary
copy without .env/private runs/workspace; root prerequisites regenerated there only.
Installed SDK HTTP payloads are intercepted, sockets blocked, and tests preserve
same enabled/disabled model requests/package results/accounting. Lookup API calls
are absent from exporter AST. No new live LangSmith/model/source verification or
historical backfill was performed. Restart/owner inspection remains the handoff.

## M2-D059 — Root lifetime, Clarify metadata and grouped scans

Owner authorized this bounded tracing polish with tests on November 10, 2026.
The earlier M2-D058 Git checkpoint is preserved at55f7825; this follow-up remains
local pending review/restart, without further publication or live calls.

App logs showed further root update failures but did not retain the exact remote
error. Root delivery now uses a minimal ingestion patch, avoiding the SDK update
path's additional nullable fields. This is a supported ingestion shape, verified
against the installed SDK's HTTP boundary offline; live success is not claimed.
See the [LangSmith API reference](https://api.smith.langchain.com/redoc).

The cached original root start and monotonically latest end span all segments and
human pauses. Fake-clock tests cover an initial5s segment, resume after300s, later
process restoration through650s and a stale clock/update that cannot shorten it.
The five-field private identity file remains unchanged. No run lookup is added.

Root gate metadata is captured from the authoritative gate tool result immediately,
including Clarify even before final state update. Later null snapshots do not erase
known gate/model fields. Actual UK clarification/resume and India Hold are tested.
One exporter is shared between model and human UI events, while retaining the union
of known secret values for redaction.

All format scans in a segment fold under one `risky-phrase scan` parent. Children
are named `scan <format>`, with hit counts and completed timing. Repeated scan calls
and nested execution contexts share that parent, which is not emitted for runs
without scans. Enabled/disabled scan outputs, hit IDs, ordering and source data are
compared across normal/suggestion/policy modes. Scanner patterns and business
validation remain unchanged.

Runtime changes are confined to `observability.py` and the scan's tracing decorator
in `package_content.py`. Existing fake-client/wire tests are adapted to ingestion;
new `test_tracing_polish.py` covers the three requested changes and strict minimal
payloads/no automatic retries. No prompts, models, graph state, UI flow, revision
rules, prices, dependencies or budget changes. No historical replay/backfill,
current-run mutation, service/model call, app restart or Git sync during the fix.

**Verification:**730 offline tests PASS:499 harness,117 UI,114 root, including eight
new polish cases and the existing tracing/SDK/revision/UI regressions. Canonical
temporary copy without .env/private runs/workspace; socket blocks and fake ingestion
state/clock verify original start, advancing end and retained metadata. No live API
validation, restart or Git sync. Metrics apply to subsequent emissions after restart.
