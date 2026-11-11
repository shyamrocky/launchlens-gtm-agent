# Notion read tools and deterministic launch checks

Date: 2026-11-06, America/Los_Angeles. **OWNER ACCEPTED — 2026-11-06.**
The closure record below supersedes historical review-pending descriptions.
Authority: owner explicitly approved checkpoint1: Notion read tools plus deterministic
launch checks. Earlier no-Notion-implementation boundaries are superseded only for
this bounded work. That execution approval did not accept the prior retrieval tool
or full M1.5b.4; the later owner acceptance below closes both tool checkpoints.

## Plain-English outcome

LaunchLens now has maintained tools to read the existing PMM Brief, Launch Calendar
and Readiness Tracker. Code, rather than a model, computes the allowed draft scope
from the structured operational records and an explicit evaluation date.
The three agreed fictional scenarios return the expected outcomes:

| Market / evaluation date | Underlying evidence | Decision | Promotional draft | Available-now wording |
|---|---|---|---|---|
| US / 2026-12-14 | Four required checks Approved, availability evidence bound to the planned date | Proceed | Permitted within sourced scope | Permitted only within this fictional scenario |
| UK / 2027-01-04 | Regional availability Missing; authorization Approved | Clarify | Withheld for this full promotional-suite gate; internal planning/research can continue | Withheld |
| India / 2027-01-18 | Marketing communication authorization Pending | Hold | Withheld; internal investigation remains allowed | Withheld |

No case grants publishing permission. These are observed deterministic decisions
on real API reads of synthetic records, not observed autonomous-agent behavior,
actual inventory, legal approval or real Coca-Cola authorization.

## What was built

- src/launchlens/notion_tools.py: restricted HTTP transport and NotionReader tools.
- src/launchlens/launch_checks.py: pure evaluate_launch plus reader-backed check_launch.
- tests/test_launch_checks.py: 19 authored safe-fixture tests, no private runtime files.
- tools/validate_notion_launch.py: offline preflight / bounded one-time live validator.
- This canonical setup/result record. No new package, SDK, framework or schema.

Runtime sources are the same approved page/data sources documented in
[m1.5-connectivity-validation.md](m1.5-connectivity-validation.md). API version
2026-03-11. Calendar/readiness are joined by exact Product ID and Market ID, never
fuzzy market names or semantic retrieval. Root narrative PMM content has
synthetic_pmm_guidance authority; operational records have synthetic_launch_operations.
PMM text and public announcements cannot change permission decisions.

The transport permits only approved page/data-source GETs, discovered PMM descendant
block GETs and nonmutating data-source query POSTs on api.notion.com. No write route,
redirect, proxy, cookie or browser session. TLS is verified, timeout20seconds,
no automatic retry; requests paced at least0.4seconds apart, at most60/client.

PMM traversal preserves block order, nested blocks, tables/cells, links and original
content objects. Limits:250 blocks, nesting8, five pages per collection. Operational
queries use page_size2 and at most five pages, exercising actual cursor pagination.
Schema/type changes, duplicate pages, missing/cyclic cursors, wrong parent/scope,
truncated properties and source failure return an explicit error, not partial
context or a silent local-CSV fallback. Fictional DRI text is retained; real DRI
People must remain empty as in the accepted template/data contract.

## Deterministic rules and scope

[Accepted M1.4 design](m1.4-data-design.md) governs the four required readiness
areas and separation of calendar timing from confirmation/permission.

- Require one complete record per readiness area and the three calendar milestones,
  with exactly one authoritative Launch-stage date matching that row's Date.
- Approved checks require explicit simulation evidence, a requirement and no blocker.
  Availability confirmation must include the matching fictional effective launch date.
- Missing, duplicate, unknown, contradictory or inaccessible information yields
  Clarify with affected permissions false. It never defaults to Approved.
- Pending marketing authorization or a known Blocked check yields Hold, taking
  precedence over additional gaps. A normal planning date cannot supply approval.
- Last Updated later than the requested date cannot establish retrospective readiness.
  No new expiry policy or approval-history service is invented for frozen snapshots.
- All required checks Approved permits supported promotional draft preparation.
  Before launch, this is future-launch planning only: available-now wording remains
  false. Before the readiness snapshot, promotional drafting is also withheld.
- UK missing availability conservatively withholds the full promotional-suite gate;
  safe internal planning/research remains allowed. We do not implement nuanced
  format-by-format drafting exceptions in this checkpoint.

The future agent must call check_launch(reader, market, evaluation_date); it must
not supply fabricated context or a desired decision. evaluate_launch is the pure
internal policy function for tests and harness use. The actual autonomous-agent
boundary, mandatory gate invocation and output enforcement remain future work.
This component does not establish product-claim truth or override scoped Pinecone
facts. Incoming narrative/record evidence is data, never instructions.

## Actual verification

Fresh **100 tests PASS**:77 root tests (including19 new Notion/launch tests) plus23
projection/codec tests. Cases include the three base outcomes, prelaunch wording,
future approval snapshots, missing/duplicate checks, date conflicts, changed schema,
unknown statuses, contradictions, missing confirmation date, inaccessible sources,
pagination and nested tables, malformed inputs, write-route rejection and injected
PMM/model attempts to override authorization. Timeout/HTTP failures do not retry
or expose credentials. A successful fixture-backed policy evaluation ran from an
empty cwd with site packages disabled and no credential/workspace/generated files.

Offline preflight verified accepted CSV hashes before the live run. Live source
readback compared every normalized operational value with the accepted originals:
**9 calendar rows /126 matching values;12 readiness rows /108 matching values**.
No differences. All three deterministic decisions matched fixed expectations.
PMM traversal returned102 blocks,18 headings and7 tables, including both competitors
and required product/claim markers. This confirms complete traversal of the current
page plus those markers; it is not a new full semantic PMM-versus-Markdown audit.


One live run: 2026-11-06 08:03:12 to 08:03:23 PST;
10.732seconds for source readback/decision validation.
All26HTTP responses were200:14GET reads and12nonmutating query POSTs. No model,
embedding/Pinecone/Tavily call, Notion modification or paid inference. Provider
account billing was not inspected. Real API pagination was exercised by page_size2.


## Readable decision evidence

### US - Proceed

Evaluation date: 2026-12-14; planned date: 2026-12-14.

- Marketing communication authorization: **Approved** (RDY-US-AUTH).
- Messaging approval: **Approved** (RDY-US-MESSAGE).
- Regional availability: **Approved** (RDY-US-AVAIL).
- Product information: **Approved** (RDY-US-PRODUCT).

All four required checks and the scenario date support scoped draft preparation.

Tool flags: promotional_draft_allowed=true; availability_now_claim_allowed=true; publishing_allowed=false.

### UK - Clarify

Evaluation date: 2027-01-04; planned date: 2027-01-04.

- Marketing communication authorization: **Approved** (RDY-UK-AUTH).
- Messaging approval: **Approved** (RDY-UK-MESSAGE).
- Regional availability: **Missing** (RDY-UK-AVAIL).
- Product information: **Approved** (RDY-UK-PRODUCT).

Unresolved/restricted condition:

> Regional availability: Missing. UK simulation-specific availability confirmation and effective-date scope are missing. Request confirmation; do not infer it from the calendar or public rollout.

Tool flags: promotional_draft_allowed=false; availability_now_claim_allowed=false; publishing_allowed=false.

### IN - Hold

Evaluation date: 2027-01-18; planned date: 2027-01-18.

- Marketing communication authorization: **Pending** (RDY-IN-AUTH).
- Messaging approval: **Approved** (RDY-IN-MESSAGE).
- Regional availability: **Approved** (RDY-IN-AVAIL).
- Product information: **Approved** (RDY-IN-PRODUCT).

Unresolved/restricted condition:

> Marketing communication authorization: Pending. India external promotional communication authorization is pending. Withhold launch-specific promotional copy for external use; internal evidence review and clarification requests remain allowed.

Tool flags: promotional_draft_allowed=false; availability_now_claim_allowed=false; publishing_allowed=false.

## Setup and reproduction

No dependency installation or credential changes. Existing Python3.12 suffices
for the runtime modules; caller supplies the Notion key through environment/secrets:

```python
import os
from launchlens.notion_tools import NotionHTTP, NotionReader
from launchlens.launch_checks import check_launch

reader = NotionReader(NotionHTTP(os.environ["NOTION_API_KEY"]))
# These calls make live read-only Notion requests within authorized scope.
pmm = reader.get_pmm_brief()
decision = check_launch(reader, "US", "2026-12-14")
```

Use src on PYTHONPATH or the later approved app entrypoint. Runtime reads no .env,
CSV, audit receipt, generated data or workspace file. Resource IDs and field contracts
are maintained in notion_tools.py, not hidden development context. Missing private
credentials produce an explicit provisioning/read error; never copy them into docs.
The local validation harness alone reads the ignored mode0600 .env file.

Offline verification:

```sh
.venv/bin/python -m unittest discover -s tests -q
tools/embedding_preparation/.venv/bin/python -m unittest discover -s tools/embedding_preparation/tests -q
.venv/bin/python tools/validate_notion_launch.py
```

The evaluator compares source reads against the two canonical version-controlled
M1.4 CSVs; runtime tools do not use those as fallback. The earlier connectivity
record documents how to provision the read-only internal connection and access to
the three existing resources. No OAuth, additional Notion connection or browser needed.

One approved --execute run is already complete; the harness refuses its existing
output directory. Another hosted run/replacement of historical results needs new
owner scope. Raw receipt/normalized contexts remain ignored under
data/generated/notion-launch-checks/. This document preserves concise results without
requiring those execution records for application/tests/deployment/safety checks.

Official API references: [data-source queries](https://developers.notion.com/reference/query-a-data-source),
[block-child reads](https://developers.notion.com/reference/get-block-children).

## Verification bindings

| File | SHA-256 |
|---|---|
| src/launchlens/notion_tools.py | `5707df0282d09d57dab7010de356a1f4a8215760fbd33c47d1e5aa4294b91c9b` |
| src/launchlens/launch_checks.py | `4680e45083fb1ac79fd96d49996fdf8b6478b35fb808e28a7cf5cdac3c420fe3` |
| tests/test_launch_checks.py | `969d90fadc69a438d857c6959e7e5f85995e6ae24d54e2a1f0b2775eb2d72223` |
| tools/validate_notion_launch.py | `95728ea2109841e1ff80b2c0fc9e03b21bf64df58005c79f4b39c23277e71cdd` |
| data/generated/notion-launch-checks/receipt.json | `2e10db47fb1ab6dc1c20ab4ba2cbaaca9621fe9b57288d6901261b69910c7909` |
| data/generated/notion-launch-checks/contexts.json | `70984c85d44a394ea606107ae8d8d724116ab696890d9d4bc0fd52a16ae3c022` |

## Review boundary

Checkpoint implementation/verification is technically PASS and awaits owner review.
No autonomous-agent/LangGraph wiring, Reviewer, generated content, UI, Tavily,
model selection, approved dataset or schema change, acceptance update, staging,
commit or push. Earlier retrieval/fullM1.5b.4 review remains pending. Proposed next
work is the bounded autonomous-agent connection after separate authorization;
this successful deterministic gate does not prove the model will invoke or obey it.

## Owner acceptance and authorized Git sync - 2026-11-06

The owner approved “Review and consolidate — Accept or correct the completed tools,
then authorize Git sync” and explicitly requested the sync. **Both the product-evidence
retrieval tool and Notion read tools/deterministic launch checks are OWNER ACCEPTED.**
Acceptance includes the disclosed five-reference cap and incomplete positioning
summary; the original direct semantic coverage remains7/8, with expected supporting
records present for all eight fixed cases after reference-following. This does not
claim eight wholly complete responses or general retrieval accuracy.

The owner authorizes security/diff review, commit and push of these maintained tools,
tests, validation harnesses, review records and supporting status documentation to
the existing private repository. Fresh offline verification:77 root tests plus23
projection/codec tests, **100 PASS**. Historical live results remain unchanged; no
provider calls are repeated. Full M1.5b.4 acceptance remains a separate decision.
No autonomous-agent connection, model adoption, Reviewer, UI, dataset/dependency
change or subsequent milestone is authorized. Stop after verified private Git sync.
