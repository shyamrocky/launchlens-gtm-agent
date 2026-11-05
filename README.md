# LaunchLens — Launch-Aware GTM Agent

LaunchLens is an educational GTM assistant for researching product information,
generating marketing content and using a specialized Reviewer Agent to critique
and improve outputs. It is the Gen Academy Week 3 **Project 3D: GTM Agent —
Ideation to Copy** project.

## Planned architecture

The owner-provided future architecture is Streamlit for the interface, LangGraph
for orchestration and state, Nebius for LLM inference, Pinecone for product
evidence retrieval, and LangSmith for observability. Google Drive, Google Sheets
and Notion are planned external data sources; Tavily is optional public research.
These are architectural context only. No integration is implemented or installed
by M0.

## Dataset strategy

Use public product facts with independently authored synthetic launch scenarios.
Record provenance, applicable reuse terms and the distinction between sourced
facts and synthetic scenarios. M1.1 has an owner-approved v0.2 public-fact Product
Brief for Coca-Cola Cherry Float, with [evidence and review status](docs/planning/m1.1-product-brief-review.md).
The owner has accepted the [Synthetic PRD v0.3](data/synthetic/coca_cola_cherry_float_prd.md)
and [GTM/PMM Brief v0.2](data/synthetic/coca_cola_cherry_float_gtm_brief.md) as part of
closing the owner-scoped M1.3 milestone on 2026-11-04. The PRD defines hypothetical
product intent; the Product Brief remains authority for scoped public product
facts. The PRD adds concise retrospective competitive context, while the PMM brief
follows the existing Notion template with two sourced competitor comparisons and
proposed positioning. Earlier accepted PRD v0.2 remains preserved in Git history.

The scoped Notion competitor/positioning updates were verified after reload; the
owner's final screenshot confirms generic document labels. Current source links
use main. Fictional dates/readiness may remain in Notion without a duplicate local
schedule. [Final audit and closure](docs/planning/data-source-final-audit.md) preserve
actual verification and its limitations. Launch Calendar and Readiness Tracker
are not created. Employer-confidential research and internal documents are prohibited.

## Milestones and current status

- **M0 — Repository bootstrap:** minimal structure, working instructions, security
  exclusions and a Python 3.12 environment with no runtime dependencies.
- **M1 — Dataset and connectivity preparation:** follow the owner-provided
  [revised M1 sequence](docs/planning/milestones.md). Detailed execution scope and
  acceptance criteria require owner review before each milestone begins.

Current status: **M0 complete; Product Brief v0.2, Synthetic PRD v0.3 and the
owner-scoped M1.3 GTM/PMM Brief v0.2 OWNER ACCEPTED (2026-11-04)**. Formal acceptance
is recorded in the milestone plan and review records. Original dataset draft/pending
labels are preserved as historical metadata and superseded by those records.

The owner authorizes reviewed publication of the final reference cleanup, audit
closure and acceptance records to the existing private GitHub repository. The
owner-scoped M1.3 GTM task is distinct from the original M1.3 Schema Validation
plan; that validation and M1.4 connectivity remain unstarted. No agents,
orchestration, ingestion or external integrations are implemented. Further work
requires a separate scoped owner instruction.

## Educational and independent use

This is an independent educational certification project. It is not an official
product of, endorsed by, or affiliated with any referenced product vendor.
Public-source attribution and applicable license notices must be preserved;
synthetic launch scenarios must be labeled as independently authored examples.
