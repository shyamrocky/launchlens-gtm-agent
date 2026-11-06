# LaunchLens north star

Owner-designated project direction, 2026-11-05. This is the authoritative goal,
MVP scope and completion target. It does not assert implemented functionality or
authorize a new execution milestone. The [milestone plan](milestones.md) records
actual acceptance and authorized work; latest explicit owner instructions govern.

## Goal

**LaunchLens helps a Product Marketing Manager turn a GTM request into an
evidence-grounded, launch-aware content package through an autonomous AI agent
that researches, drafts, delegates review and revises, while a deterministic
harness enforces launch restrictions and preserves human control.**

For this MVP, the product is Coca-Cola Cherry Float, using verified public product
facts alongside independently authored fictional launch scenarios. The experience
ends with reviewed drafts, human feedback and export; it does not publish content
or grant real-world business approval.

## Autonomous behavior and boundaries

The user provides a market, evaluation date and campaign objective. The agent
determines what information it needs, chooses tools, gathers evidence, identifies
audience hypotheses and tone, and decides whether to research further, request
clarification, generate content, delegate critique, revise or stop.

**The model controls task execution. The harness controls what is permitted.**
Use a bounded autonomous agent loop with state and tools. A fixed sequence of
LLM calls alone does not meet the owner's objective. Required evidence checks,
source authority, launch restrictions, tool permissions, execution limits and
Reviewer participation remain enforced regardless of the model's proposed action.

Product Brief facts, synthetic PRD intent, proposed PMM positioning, planned dates
and readiness permissions have distinct authority. Read calendar/readiness records
by exact product/market identifiers. Missing evidence or a failed tool never
becomes permission. Calendar dates govern scenario timing; a planned date or public
announcement alone does not establish inventory or marketing authorization.

## User deliverable

When permitted, produce:

- A campaign brief.
- A LinkedIn post.
- A promotional email.
- A short blog draft.
- Multiple ad variations.
- Supporting evidence, unresolved conditions and Reviewer findings.

The Reviewer checks every content format for factual grounding, tone, consistency
and completeness, with bounded revision to address findings. Streamlit presents
the reviewed package, a concise record of actual agent actions and tool outcomes,
and controls for human feedback, revision and export. Keep the request, evidence,
launch decision, drafts, review and feedback in explicit state for the active task;
cross-session memory is outside this MVP.

## Completion criteria

The MVP is complete when all five scenarios demonstrably work. These are targets,
not results already achieved.

| Scenario | Required outcome |
|---|---|
| US, at its scenario evaluation date | Complete, reviewed content package using supported claims |
| UK | Missing availability confirmation surfaced; unsupported availability wording withheld |
| India | Pending authorization respected; restricted promotional output withheld |
| Tool failure | Bounded recovery or explicit handoff; missing evidence never becomes permission |
| Human feedback | Existing content revised while preserving evidence and launch restrictions |

Verify end-to-end task completion and actual agent/tool behavior. Retrieval fit,
storage integrity and good isolated drafts do not establish workflow success.
For permitted output, all four formats must be present, each reviewed, with its
material factual claims traceable to appropriately scoped evidence. Record actual
scenario outcomes and elapsed time; do not claim unmeasured accuracy or speed.

## Scope and sprint discipline

Retain Streamlit, LangGraph, Nebius, Pinecone, Notion and LangSmith. Reuse the
accepted preparation work and keep the corpus frozen. Approved PDFs supply product
evidence; Notion supplies PMM and structured operational context. Google Drive
remains the verified source-distribution channel; an extra Sheets integration or
public-research tool is not required for this sprint.

General Q&A, generic ingestion, multiple products, public web research, publishing,
production approval lifecycle and corpus-update infrastructure remain outside the
MVP. Reference solutions provide hints only; no copied code, prompts or datasets.

The 3-5-hour sprint target covers the working experience, focused verification and
submission preparation. It is a planning target, not a guarantee or an end-user
runtime target. Verify Nebius model/tool-calling compatibility early. Add complexity
only for a demonstrated blocker to these completion criteria, with owner approval
for scope changes. Reserve time for failure handling and human feedback.

## Week 3 submission

The owner-provided Week 3 Project Handout (Oct 2026), especially Project 3D and the
agent/submission guidance, governs course alignment. Its detailed framework is
optional; its tool-use, state, error-handling and human-intervention expectations
remain central. The solution kit and reference repository do not replace it.

Prepare:

- A Google Doc covering overview, datasets, AI coding prompts, iterations and learnings.
- A live demonstration of five minutes or less showing the result and explaining AI-assisted development.
- A GitHub code link accessible to reviewers while preserving private visibility.

Keep credentials, restricted inputs and development workspace material out of
submission assets. Include one complete reviewed sample suite for the product.

## Use this north star during development

Before substantial work, read this file and the current authorized milestone. Each
proposed task should identify which goal or completion criterion it advances. At
handoff, report what is verified, what remains unresolved and whether scope changed.
Changes to this goal or scope require explicit owner direction. Keep one canonical
version here; workspace context and discussion memory link to it without replacing it.

**Our measure of success is a completed, reviewable GTM task, with observable
autonomy, enforced restrictions and a working human feedback loop.**

Current implementation/verification remains recorded separately in the
[milestone plan](milestones.md) and the
[three-record hosted sample review](m1.5b4-pinecone-sample-validation.md).
