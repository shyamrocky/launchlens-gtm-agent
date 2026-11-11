## Owner-approved single-run ceiling — November 9, 2026

The owner approved **USD 0.80 maximum model spending** after the proposed single
US full-package live test was explained. One scoped authorization is provisioned
locally for US / December 14, 2026 / `flavor_discovery`, using the prepared profile,
unchanged prompts/contracts/projection and original validation. At most one explicit
feedback/revision and fresh review share this same ceiling and execution budget.
Zero automatic retries, repairs or fallback. The approval does not adopt model
defaults, accept content, authorize publishing or grant Git publication authority.

The user will initiate execution with **Start agent**. Provisioning and validating
the authorization made no source or model requests; no live run has started.
The private authorization has mode 0600 and expires **November 10, 2026, 11:08:35 AM
PST**, matching the existing qualification deadline. If unused then, requalification
is required; spending permission must not silently transfer to changed profiles.
The historical preparation report below preserves what was unapproved at that time.

# Live full-package preparation

Decision **M2-D023**, November 9, 2026, America/Los_Angeles.
Status: **PREPARATION AUTHORIZED; OFFLINE TECHNICAL PASS; OWNER REVIEW PENDING.**

The owner approved connecting the existing controller, Writer and Reviewer to the
live full-package path and verifying access, limits and spending controls without
inference. No paid call or Git publication is authorized. This supersedes M2-D022's
offline-only routing solely for guarded preparation. Historical results remain intact.

## Result and reuse

The existing FoundationSession/LangGraph now supports an explicit `live_package`
profile. The model chooses research, generation, review and revision actions; the
same harness enforces supported tasks, authoritative evidence, launch permissions,
version-bound reviews, replay protection and the 12-call / 4-search limits.
One Writer returns all five deliverables, a separate Reviewer examines them, and
one explicit feedback request may trigger a whole-package revision and fresh review.
The revision is offered only when its entire minimum call cycle still fits.

[Live adapters](../../../src/launchlens/live_package.py) reuse the existing one-shot
Nebius HTTP transport, Notion/Pinecone read tools, accepted Writer projection,
content contracts and backend validation against complete original authority.
[The profile](../../../data/templates/gtm/live_package_profile_v1.json) binds the exact
models, settings and qualification evidence. Package prompts, original templates,
projection policy, source data, historical responses and lockfiles are unchanged.
No additional framework, pipeline, database, dependency or ingestion was introduced.

Streamlit offers **Live agent / Demo simulation**. Navigation and rerenders never
start model calls. Live Start remains disabled without a fresh, scoped authorization;
a failed live run never falls back to fixtures. Simulation remains available.
Live Generate again requires a new authorization; reset closes the budget and leaves
protected results intact. Human acceptance/export are not implemented by this change;
publishing remains disabled.

## Actual read-only qualification

At **2026-11-09 19:08:35.820051 UTC**, two Python HTTP GETs completed:

| Resource | Result | Bytes | SHA-256 |
|---|---|---:|---|
| Authenticated `/v1/models` | HTTP 200; 25 account-listed IDs | 2,350 | `63c5ce651a7dcd7e8927df247cd13bfe574b6442990d298331cd526816c37cf1` |
| Public `models_info` | HTTP 200; both selected models active | 35,780 | `75818db5c912d5249da37ada7349e0014cc66f996cd39b7c84bce7f746f1c157` |

Official sources: [account model endpoint](https://api.tokenfactory.nebius.com/v1/models),
[public model catalog](https://tokenfactory.nebius.com/api/public/models_info),
[Chat Completions contract](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion).
The 25-ID result is a new dated observation; it does not replace the historical
31-model inventory. Credentials and complete authenticated response contents are
not copied into documentation. There were **zero generation requests**.

| Role | Exact candidate | Published context | Input / output USD per million tokens |
|---|---|---:|---:|
| Controller | `Qwen/Qwen3-30B-A3B-Instruct-2507` | 262,144 | 0.10 / 0.30 |
| Writer, Reviewer, revision | `NousResearch/Hermes-4-405B` | 131,072 | 1.00 / 3.00 |

Account listing establishes authentication and discovery, not fresh inference
entitlement, quota, API compatibility or writing/review quality. No inference probe
was performed. Roles are proposed for this bounded test, not adopted defaults.
Writer and Reviewer are independent calls using the same model family; correlated
mistakes remain possible.

## Token and cost reservation

No exact provider input-token count is claimed. The conservative reservation uses
published context minus the completion cap as the upper input bound. Accepted
requests must satisfy that provider contract. Existing request-byte limits are
separate safety limits, not token counts or proof of context fit.

| Role | Max calls | Input upper bound per call | Completion cap | Role reservation USD |
|---|---:|---:|---:|---:|
| Controller | 8 | 261,632 | 512 | 0.2105344 |
| Writer | 1 | 122,880 | 8,192 | 0.147456 |
| Reviewer, including re-review | 2 | 126,976 | 4,096 | 0.278528 |
| Explicit revision | 1 | 122,880 | 8,192 | 0.147456 |
| **Total** | **12** | | | **0.7839744** |

**Revised proposed model-spending ceiling: USD 0.80, UNAPPROVED.** This is a
worst-case reservation, not expected spending. The earlier unapproved USD 0.50
proposal does not cover this method and is rejected before execution. This ceiling
covers Nebius generation roles; existing Notion/Pinecone service-plan charges are
outside it, with the existing four-search and read-only source limits unchanged.

The provider envelope adds equal `max_tokens` and `max_completion_tokens` caps to
the unchanged logical role request, accounting for visible and reasoning output.
No provider-enforced response schema or new thinking setting is introduced. This
translation follows the documented cap contract but its acceptance by these exact
hosted models remains part of the first separately authorized live test.
Usage must be present, internally consistent, within bounds and identify the exact
model. Reasoning tokens, when reported, must fit within completion usage and are
not added twice. Unknown billing, transport failure, malformed output/usage or
model mismatch stops execution with the entire reservation retained.

## Authorization and protected storage

The default command is pure offline preflight: no credentials, network or writes.
Future execution requires a separately owner-approved private file at
`data/private/live-package-authorization.json`, provisioned explicitly with mode
0600. The command below prints an **unauthorized** template; it creates no file.
Only after explicit approval may its owner flag, scope, expiry, ceiling and
acknowledgments be populated. Enabling a mode is never spending permission.

The authorization binds US / December 14, 2026 / `flavor_discovery`, approved source
permissions, profile/registry/projection/voice identities, a unique ID and whether
one explicit revision is permitted. Qualification and authorization expire within
24 hours of the dated checks above. Expired prices/access require requalification
and review, with no automatic refresh or model substitution.

Before any dispatch, the whole role plan is admitted and reserved. Claims are
locked, bounded by role and total attempts, and never refunded on uncertain usage.
A fresh protected output directory atomically consumes the unique authorization;
rerender, Reset or another process cannot reuse it. No authorization file or live
output directory was created during this checkpoint.

Protected artifacts are provisioned at runtime in
`data/generated/live-package-{authorization_id}/` (0700 directory, 0600 files).
They retain request identities, sanitized complete available response bodies before
parsing, telemetry, validation candidates/findings, state and spending records.
Credential echoes are redacted and cause a stop; oversized responses are marked
truncated and rejected. Provider exceptions are not copied as arbitrary diagnostics.
Future request hashes depend on actual research/drafts and are captured before each
send; they cannot all be precomputed now. No runtime dependency on `workspace/`.
The CLI stops after initial review; feedback/revision uses the same running UI
session. Cross-process resume is outside this checkpoint.

## Verification

**399 offline tests PASS: 255 agent + 111 root + 33 UI.** New checks cover guarded
native-controller/full-package/review/revision wiring, unchanged logical inputs,
source failures, authoritative backend validation, no demo fallback, atomic limits,
private authorization, expiry, raw capture, malformed/unknown usage, reasoning
accounting, credential exclusion and exact one-shot HTTP translation. New tests
block socket connections and assert zero attempts, including when tracing is set.
Mocks establish wiring and fail-closed behavior, not live compatibility or quality.

The existing source/format/launch/voice checks remain independent of model output.
No automatic retry, fallback model, formatting repair or regeneration was added.
A clean canonical copy passed **255 agent + 33 UI tests** without workspace,
credentials, generated/private artifacts or original PDFs, using the existing
provisioned interpreters. Root's 111 tests passed in the project checkout. No package
installation or lockfile changes. Syntax/JSON, 152 relative links, credential-value
and pattern exclusion, and `git diff --check` passed. Of 344 baselined files,
14 existing files changed before continuity updates; all 154 protected data,
prompt, environment, package-metadata, lock and MEMORY files were unchanged.
Fifteen canonical untracked files include the earlier M2-D022 additions; no files
were staged, committed or pushed. The protected historical inputs remain local.

The local Streamlit server was restarted at http://127.0.0.1:8520/ in explicit
Demo simulation mode to load the tested code. AppTest covered both UI modes;
no new manual browser certification or live source-refresh result is claimed.

## Reproduce and next boundary

Use the existing locked/provisioned tool environments; no installation was needed:

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/run_gtm_package.py
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/run_gtm_package.py --authorization-template
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python -m unittest discover -s tools/agent_foundation/tests -v
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python -m unittest discover -s tools/ui/tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Future command, **NOT authorized or executed**:

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/run_gtm_package.py --execute --authorization data/private/live-package-authorization.json
```

Alternative: start the existing UI, select Live agent and explicitly Start after the
same private authorization is provisioned. Keep that session for optional feedback.
Review this preparation and the revised ceiling first, then separately authorize
one live US five-deliverable run. Preserve every result and stop on failure without
retry/repair. Semantic content acceptance, human acceptance/export, sanitized
LangSmith and final certification evidence remain later checkpoints.
