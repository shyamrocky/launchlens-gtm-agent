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
M1.2 has an [owner-approved synthetic PRD v0.2](docs/planning/m1.2-prd-review.md) for hypothetical
product intent; it cannot override the Product Brief's factual claims. The PMM
Brief, Launch Calendar and Readiness Tracker are not created. Employer-confidential
research and internal documents are prohibited.

## Milestones and current status

- **M0 — Repository bootstrap:** minimal structure, working instructions, security
  exclusions and a Python 3.12 environment with no runtime dependencies.
- **M1 — Dataset and connectivity preparation:** follow the owner-provided
  [revised M1 sequence](docs/planning/milestones.md). Detailed execution scope and
  acceptance criteria require owner review before each milestone begins.

Current status: **M0 bootstrap complete; M1.1 Product Brief v0.2 and M1.2
Synthetic PRD v0.2 formally accepted by the owner on 2026-11-04**. The accepted
dataset files are preserved unchanged; their original draft/pending labels are
superseded by the acceptance recorded in the linked reviews and milestone plan.
No agents, orchestration, ingestion or external integrations are implemented.
Further dataset or milestone work requires separate owner authorization.

## Educational and independent use

This is an independent educational certification project. It is not an official
product of, endorsed by, or affiliated with any referenced product vendor.
Public-source attribution and applicable license notices must be preserved;
synthetic launch scenarios must be labeled as independently authored examples.
