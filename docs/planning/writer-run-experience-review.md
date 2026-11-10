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
