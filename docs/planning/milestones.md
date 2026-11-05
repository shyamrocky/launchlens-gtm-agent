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
repository. Remaining datasets and M1.3/M1.4 are not started; no next milestone is
authorized. Accepted-file draft/pending labels remain untouched; these records
capture the subsequent owner acceptance.

## Owner-provided M1 sequence

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
or paid model usage are authorized. Next checkpoint: report the approved private
repository sync, then wait for the owner's next scoped instruction. No automatic
advancement or alteration of accepted datasets.
