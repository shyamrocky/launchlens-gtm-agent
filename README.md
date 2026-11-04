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
facts and synthetic scenarios. No dataset or specific product corpus is included
or selected by this bootstrap. Employer-confidential research and internal
documents are prohibited.

## Milestones and current status

- **M0 — Repository bootstrap:** minimal structure, working instructions, security
  exclusions and a Python 3.12 environment with no runtime dependencies.
- **M1 — Next implementation milestone:** its detailed scope and acceptance
  criteria require explicit owner approval before work begins.

Current implementation status: **repository bootstrap only**. No agents,
orchestration, ingestion, integrations or datasets are functional. The future
architecture does not authorize implementation during M0.

## Educational and independent use

This is an independent educational certification project. It is not an official
product of, endorsed by, or affiliated with any referenced product vendor.
Public-source attribution and applicable license notices must be preserved;
synthetic launch scenarios must be labeled as independently authored examples.
