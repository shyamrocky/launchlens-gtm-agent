# LaunchLens — Launch-Aware GTM Agent

LaunchLens is an educational GTM assistant for researching product information,
generating marketing content and using a specialized Reviewer Agent to critique
and improve outputs. It is the Gen Academy Week 3 **Project 3D: GTM Agent —
Ideation to Copy** project.

The [LaunchLens north star](docs/planning/northstar.md) is the canonical goal,
MVP scope and completion checklist. Read it alongside the authorized milestone;
its targets are not claims of implemented functionality.

## Current checkpoint - 2026-11-05

Local document preparation, chunking and focused embedding preparation
(M1.5b.1/B2/B3) are owner accepted. Pinecone storage fidelity, the GTM semantic
baseline, bounded reference-following and a fixed keyword/hybrid comparison have
been tested; full M1.5b.4 remains pending owner acceptance. Semantic baseline:
7/8 predefined checks, with the missing supporting claim recovered in a separate
one-hop reference test. The combined application retrieval tool, autonomous agent,
Reviewer and UI are not implemented. Final chat-model selection remains deferred.

The owner approved committing/pushing this existing code and verification checkpoint
to the private repository after security review. This approval does not advance
implementation or accept pending milestones. The sections below preserve results
and stop boundaries from each checkpoint; later explicit records supersede earlier
unimplemented/unverified descriptions. See the [milestone plan](docs/planning/milestones.md).

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
actual verification and its limitations. The owner accepted and closed the scoped
[M1.4 calendar/readiness milestone](docs/planning/m1.4-final-validation.md) on
2026-11-05 after its final PASS audit: nine calendar milestones and 12 readiness
records, with all 234 saved Notion values matching the canonical CSVs. Working team
is Product Marketing (PMM); coordinators are fictional. The accepted datasets and
supporting documentation are authorized for publication to the existing private
repository. Employer-confidential research and internal documents are prohibited.

## Milestones and current status

- **M0 — Repository bootstrap:** minimal structure, working instructions, security
  exclusions and a Python 3.12 environment with no runtime dependencies.
- **M1 — Dataset and connectivity preparation:** follow the owner-provided
  [revised M1 sequence](docs/planning/milestones.md). Detailed execution scope and
  acceptance criteria require owner review before each milestone begins.

Current status: **M0 complete; Product Brief v0.2, Synthetic PRD v0.3 and the
owner-scoped M1.3 GTM/PMM Brief v0.2 OWNER ACCEPTED (2026-11-04)**. Formal acceptance
is recorded in the milestone plan and review records. **Owner-scoped M1.4 Launch
Calendar and Readiness Tracker OWNER ACCEPTED and CLOSED (2026-11-05)**.
**M1.5a — External Data Source Connectivity & Validation OWNER ACCEPTED
(2026-11-05)**: [verification record](docs/planning/m1.5-connectivity-validation.md)
covers anonymous Drive PDF downloads and read-only Notion API access. It preserves
PDF integrity/checksum results and exact calendar/readiness CSV comparisons.
Original dataset draft/pending
labels are preserved as historical metadata and superseded by those records.

The owner authorizes the bounded M1.5a verification-documentation and acceptance
sync to the existing private GitHub repository. Original milestone planning labels
remain recorded separately from the owner-scoped acceptance checkpoints. Source
connectivity has been verified; agents, orchestration, ingestion and maintained
application integration adapters are not implemented. Further work requires a
separate scoped owner instruction.

## Local document preparation - M1.5b.1

The owner approved local preparation of Product Brief v0.2 and Synthetic PRD v0.3
on 2026-11-05 and subsequently accepted the results: **OWNER ACCEPTED / CLOSED**.
Accepted scope: five page records,
raw/normalized text, page provenance, separate document authority, source links and
complete claim/requirement preservation checks. [Setup and verified results](docs/planning/m1.5b-document-preparation.md)
describe the locked Python 3.12 / pypdf environment and reproducible ignored
outputs. This supersedes earlier no-dependency/no-ingestion status only for local
preparation. Source artifacts and prior acceptance history remain unchanged.
Chunking, embeddings, BM25, Pinecone indexing and agents remain unimplemented;
M1.5b.2 requires explicit owner authorization. No commit or push authorized.

## Local chunking and evidence preparation - M1.5b.2

The owner explicitly authorized M1.5b.2 on 2026-11-05 after accepting document
preparation. [Chunking setup and verification](docs/planning/m1.5b-chunking-review.md)
record the **OWNER ACCEPTED / CLOSED** local result (2026-11-05): 45 chunks (15
claims, seven requirements, 23 context/reference sections), 96 authored blocks,
complete qualifiers and cross-page citations, and canonical approval metadata.
Custom Python reuses the validated block boundaries; no new dependency added.
42 tests and clean-copy regeneration PASS. Existing source/preparation artifacts
remain unchanged. Chunks are reproducible ignored local records. Embedding token
fit, retrieval quality and Pinecone upload format remain unverified; no embedding,
BM25, Pinecone indexing, agent, commit or push has been performed or authorized.
This later explicit local scope supersedes the prior checkpoint's stop boundary.

## Focused embedding projection and audit - M1.5b.3

Owner authorized local M1.5b.3 on 2026-11-05. [Plain-English review and setup](docs/planning/m1.5b3-embedding-review.md)
include a readable before/after audit for all 45 unchanged chunks. Implemented
projection separates focused embedding_text from the complete evidence_payload;
source authority, qualifications and citations remain intact. multilingual-e5-large
is the owner-accepted baseline (2026-11-05); pinned public tokenizer checks
show all inputs fit locally (largest 279/507 tokens). 65 tests and clean-copy
regeneration PASS. The co-located serialized-evidence storage contract is locally
round-trip tested; no Pinecone record exists. Runtime decoding needs no local JSONL.
A small isolated tooling lock preserves accepted root dependencies/artifact hashes.
Hosted tokenizer parity and relevance remain unverified. No vectors, model API,
Pinecone index/upload, agent, commit or push. On 2026-11-05 the owner explicitly
accepted **both M1.5b.2 and M1.5b.3: OWNER ACCEPTED / CLOSED**, including all three
embedding/model/evidence decisions. Dated canonical closure records supersede
preparation-time pending labels; original generated artifacts remain unchanged.
The owner directed recording acceptance, then stopping. No next checkpoint or
publication is authorized.

## Hosted three-record evidence sample - M1.5b.4

Owner authorized the bounded sample on 2026-11-05. [Verification and setup](docs/planning/m1.5b4-pinecone-sample-validation.md):
**technical PASS, owner review pending**. Dedicated Pinecone index
`launchlens-e5-sample-v1` contains only PROD-008, PROD-011 and REQ-007 in its sample
namespace. E5 inference reported 258 tokens. Exact-ID fetch restored every evidence
byte, digest, citation, qualification and authority unchanged; existing 65 tests
passed freshly. Earlier no-index statements describe prior checkpoint results.
The remaining 42 records, semantic retrieval and agents remain unimplemented;
no commit/push. Index/sample retained. Stop for review before further work.

## Full validation corpus - M1.5b.4

[Full-corpus storage verification](docs/planning/m1.5b4-full-corpus-validation.md):
**technical PASS / owner review pending**,2026-11-05. All45 approved records are in
isolated namespace m15b4-corpus-validation-v1 on the existing validation index.
Exact IDs/full evidence/metadata and stored1024-dimensional vectors verified;
original three-record sample unchanged. E5 usage4,275 tokens;65 existing tests PASS.
Earlier no-full-upload descriptions are checkpoint history. No semantic search
or generated GTM behavior tested; full M1.5b.4 remains incomplete. Stop for review.

[GTM-focused semantic retrieval baseline](docs/planning/m1.5b4-semantic-retrieval-validation.md),
2026-11-05: **7/8 fixed checks passed; one direct-claim coverage miss remains.**
The broad flavor/inspiration query retrieved a relevant overview but not PROD-002
in its top five; the overview links to that exact claim. All40 hit packets verified,
corpus unchanged. Ranked results and fixed expectations are in the report. No
query tuning, claim-link follow-up or agent implementation performed. Earlier
no-search statements describe prior checkpoints. Stop for owner review.

[One-hop claim-reference follow-up](docs/planning/m1.5b4-claim-link-validation.md),
2026-11-05: technical PASS. Actual overview links recovered PROD-002 with full
source support; original semantic scorecard remains7/8. Keyword/hybrid retrieval
is untested and remains an open comparison. No agent implementation or publication.

[Fixed search comparison](docs/planning/m1.5b4-search-comparison.md),2026-11-05:
semantic7/8,keyword6/8,hybrid7/8 on the same eight cases. Keyword improved some
ranks; the tested hybrid did not close the top-three flavor miss or increase
case coverage. Recommend semantic plus verified reference-following for the frozen
MVP, pending review. No runtime hybrid service/index/dependency or agent added.

## Educational and independent use

This is an independent educational certification project. It is not an official
product of, endorsed by, or affiliated with any referenced product vendor.
Public-source attribution and applicable license notices must be preserved;
synthetic launch scenarios must be labeled as independently authored examples.
