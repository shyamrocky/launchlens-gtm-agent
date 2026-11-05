# LaunchLens milestone plan

Authority: owner-provided revised M1 sequence, 2026-11-04
(America/Los_Angeles). This document is the canonical milestone plan.

## Current status

M0 repository bootstrap is complete. The owner subsequently authorized a bounded
M1.1 Product Brief Dataset for Cherry Float, distinct from fictional launch context.
On 2026-11-04, the owner formally accepted Product Brief v0.2 and Synthetic PRD
v0.2 as the LaunchLens datasets delivered under the bounded M1.1/M1.2 scopes.
The owner authorized final confidentiality/Git diff review and commit/push of the
unchanged artifacts and supporting documentation to the existing private GitHub
repository; that approved sync completed at c123b7c. The later explicit owner request
authorized the bounded M1.3 GTM brief below. A subsequent explicit request now
authorizes a reviewed private-GitHub update of PRD v0.3, GTM v0.2 and supporting
records; the original no-push boundaries below are historical.
Accepted-file draft/pending labels remain untouched; these records capture owner
acceptance. Schema Validation and External Tool Connectivity remain unstarted.

## Owner-provided M1 sequence (original planning labels)

The table preserves the original sequence. The later owner-scoped M1.3 GTM brief
uses the same identifier for a different bounded task, recorded separately below.
It does not authorize or complete the original Schema Validation checkpoint.

| Order | Milestone | Execution status |
|---|---|---|
| M1.1 | Dataset Content Design | Product Brief v0.2 OWNER ACCEPTED (2026-11-04); bounded dataset scope |
| M1.2 | Codex-Assisted Dataset Generation | Synthetic PRD v0.2 OWNER ACCEPTED (2026-11-04); other datasets not started |
| M1.3 | Schema Validation | Not started |
| M1.4 | External Tool Connectivity | Not started |

## Owner-scoped M1.1 Product Brief Dataset

The latest owner request authorizes public-source research and a 2-3-page,
text-based Cherry Float Product Brief, editable Markdown and a claim-source CSV.
Keep product truth separate from fictional simulation truth. Record source dates,
market/variant scope, qualifications and unknowns. The historical pre-launch frame
is scenario metadata, not permission to invent product facts or readiness.

See [the review and verification record](m1.1-product-brief-review.md), including
the subsequent explicit owner approval of v0.2. Product Brief acceptance alone
does not authorize any later dataset. The subsequent formal acceptance request
authorizes the current commit/push to the existing private repository; the original
dataset-generation requests did not grant publication permission.

## Owner-scoped M1.2 synthetic PRD

Authority: explicit owner M1.2 Synthetic PRD Creation prompt and architectural
clarification, 2026-11-04. Create only an independently authored 1-2-page PRD,
editable Markdown, PDF and short validation report. Preserve Product Brief v0.2
and its evidence manifest without edits. PRD authority is hypothetical product
intent/requirements/objectives; Product Brief authority is publicly supported
product characteristics and factual claims. Do not resolve factual conflicts by
using synthetic intent as evidence. See [the PRD review](m1.2-prd-review.md).

Status: PRD v0.2 OWNER ACCEPTED on 2026-11-04 following M12-01/M12-02 corrections
and local verification. See the review record and preserved independent v0.1 audit.
Stop before another dataset, agent implementation, formal schema validation or
external connectivity. No PMM Brief, Launch Calendar, Readiness Tracker or marketing
copy has been created; only the approved private-repository sync is authorized.
The original general M1 sequence remains unchanged; this request authorizes only
one bounded M1.2 dataset, not all remaining synthetic content.

## Latest owner-scoped M1.3 - Notion GTM brief

Authority: explicit "M1.3: Populate Notion GTM Plan" owner request, 2026-11-04.
Inspect the exact existing Notion page read-only and create one paste-ready
Markdown GTM/PMM brief plus review, preserving observed headings/order/table
columns. Use accepted PRD intent and Product Brief facts within their distinct
authority. No Notion edits, other datasets, agents, external integration or
commit/push/publication. Formal Schema Validation is not part of this task.

Status: GTM brief v0.2 WORKING REVISION PRODUCED; owner review pending. Browser inspection
succeeded; no API connectivity tested. [Template map and verification](m1.3-gtm-brief-review.md)
record 18 headings, six tables, three messaging pillars and unresolved launch
fields. Launch Calendar and Readiness Tracker remain separate future datasets.
Stop for owner approval; this scope does not rename the earlier sequence silently
or approve any subsequent implementation.

### Owner-approved competitive-context extension - 2026-11-04

The owner approved only Pepsi Wild Cherry & Cream and Dr Pepper Strawberries &
Cream, source-supported comparisons plus labeled positioning hypotheses, and the
final competitor column Proposed Cherry Float Differentiation. Incorporate these
in the local PMM template and align its positioning/pillars. The owner also requests
one minimal Market & Competitive Context subsection in PRD v0.3, explicitly
retrospective. This is the authorized exception to preserving PRD v0.2 unchanged;
accepted v0.2 remains at c123b7c, and Product Brief/manifest stay untouched.

Produced local PRD v0.3 Markdown/PDF and GTM v0.2. Revised artifact review remains
pending; competitive-content approval does not imply whole-document acceptance.
Historical M1.1/M1.2 acceptance/audits remain preserved in their review records.
No new competitors, full market study, Notion edit, commit/push, publication or
implementation. See the updated PRD and GTM reviews for source checks and hashes.

### Owner-authorized GitHub revision update - 2026-11-04

Following the core-content sync audit and review of version-pinned links, the owner
explicitly said to update GitHub. Scope: review and commit/push the existing PRD
v0.3 Markdown/PDF, GTM v0.2 and supporting documentation to the existing private
repository. Preserve authored artifact bytes, old accepted versions and audits;
no new dataset, code, service, public visibility or milestone advancement.

Provide a new commit-specific PRD URL for the owner to update in Notion; do not
change Notion in this task. Existing Product Brief/manifest links pinned to c123b7c
remain valid. The owner confirmed fictional dates/readiness may remain in Notion;
the local GTM need not duplicate their detailed table. Do not treat that authorized
scenario-only difference as a product-fact contradiction. Current revision/draft
labels remain unchanged; Git publication does not invent formal artifact acceptance.

## Proposed later checkpoint outcomes

These remain working interpretations for owner review, not separately approved
implementation scopes or completed results.

- M1.2: use Codex during development to produce the independently authored
  synthetic launch scenarios against the reviewed content design. Keep public
  facts distinct from synthetic assumptions and retain provenance. Review the
  actual generated content before moving on.
- M1.3: formalize and check the agreed schema, required fields, types, IDs,
  relationships and source/synthetic labels. Report failures and corrections;
  structural validity does not establish factual accuracy or marketing quality.
- M1.4: verify only the separately approved external-tool connectivity scope,
  including credential handling, bounded checks and useful error reporting.
  Select the exact services and any provider-call budget before execution.

## Canonical outputs and constraints

Accepted content designs and operating/provisioning instructions belong in docs/.
Reviewed public references and synthetic data use data/public_sources/ and
data/synthetic/ respectively; schemas use data/schemas/. Maintained validation
code and tests belong in src/, tools/ or tests/ as appropriate, never workspace/.
Private runtime artifacts require a documented provisioning/storage contract.

Follow [project governance](../project-governance.md). Preserve public-fact
provenance and independently authored synthetic labels. No employer-confidential
material, private-project copies or credentials may enter committed data.

The future architecture is unchanged. Initial sequence approval did not authorize
execution; the later Product Brief and PRD requests authorize only their bounded
outputs described above. No agents, application dependencies, external integrations
or paid model usage are authorized. Latest checkpoint: owner review of local
PRD v0.3 and GTM brief v0.2. The latest explicit owner request authorizes their
bounded private-repository update described above, then a handoff with the new
PRD URL. No automatic advancement or unrelated accepted-data edits.
