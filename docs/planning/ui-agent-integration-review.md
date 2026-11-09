# Checkpoint 2 — Offline UI to existing agent harness

Decision: **M2-D020**, 2026-11-09 (America/Los_Angeles).
Status: **OFFLINE TECHNICAL PASS / OWNER REVIEW PENDING**.
Authority: owner explicitly approved checkpoint 2 following the offline Reviewer
and one-revision implementation. Reuse the existing harness; no new pipeline,
live inference, default-model change, hosted tracing or Git publication.

## What you can inspect

Open http://127.0.0.1:8520/. Select **Offline simulation**, open US, optionally add
notes, then **Start simulation**. The existing FoundationSession/LangGraph executes
scripted controller choices and fixture tools. The UI renders its actual action
ledger, LinkedIn draft, supporting claims/citations/qualifications and authored
mock Reviewer findings. It does not invent a progress log or show model reasoning.
Activity updates are displayed after the bounded synchronous run completes; live
streaming and background execution are not implemented.

The preserved Hermes candidate is shown as a safe fixture. Mock review flags
“We’re bringing” and “a hint of vanilla.” Submit explicit feedback with **Request
one revision**: the existing owner-only command binds permission to the current
run/version/hash; the scripted controller chooses revision, and fresh review binds
to version 2. Both versions/reviews remain inspectable inside the current run.
The revision is authored test copy; it does not creatively respond to arbitrary
notes or feedback. Structural validation and mock review do not establish live
factual accuracy, writing quality or autonomy. Human acceptance and publishing
remain false. No Approve/Publish control or export is added here.

| Scenario | Observed offline result |
|---|---|
| US at December 14, 2026 | Five completed actions through draft/review; changes requested. Explicit feedback then revision/re-review; 2 versions, 2 reviews, 11/12 simulated shared calls |
| UK at January 4, 2027 | Clarification required, missing regional availability, no draft/review. Free-text approval cannot resolve the fixture record |
| India at January 18, 2027 | Hold on pending marketing authorization, no promotional draft or research-only brief |
| Simulated launch-tool failure | Failed safely; action result remains inspectable; no permission inferred and no automatic retry |
| Invalid Writer / Reviewer response | Exact safe diagnostic and complete available mock candidate/response retained; rejected review cannot enable revision |

**Generate again · simulation** explicitly replaces the current run with a fresh
ID, ledger, budget and review state. **Reset demo**, Refresh data and mode switches
clear the current simulation; they never purge sources or historical receipts.
Opening another market cannot replace a run or dispatch another model. Navigation,
widget changes, rejected empty feedback and rerenders make no inference requests.
Lifecycle widgets and feedback forms carry run/version identity; backend locking,
replay protection and exact-version admission remain authoritative. This is
session memory, not crash-durable execution or an archive.

## Reuse and data boundaries

- Same StateGraph, source/evidence checks, launch policy, action registry, turn
  limits, Writer contract and Reviewer/revision admission. No second orchestrator.
- `user_notes` is a bounded, copied initial-state field supplied by the application,
  separate from the registry request/launch authority. Existing calls default to
  empty notes. Live prompts and accepted Writer projection are unchanged; no claim
  that these fixtures demonstrate live interpretation of notes.
- New thin adapters/rendering: [offline_ui_run.py](../../src/launchlens/offline_ui_run.py)
  and [agent_run_ui.py](../../src/launchlens/agent_run_ui.py). Existing preparation
  route remains; current-run rendering is inside the same Streamlit entry point.
- Existing safe tools fixtures are promoted into canonical
  [offline_fixtures.py](../../src/launchlens/offline_fixtures.py); original tools
  paths remain compatibility imports for demos/tests. The same canonical
  [review cases](../../tests/fixtures/gtm_review_cases.json) are unchanged. This is
  explicit fixture provisioning, not a runtime dependency on workspace or private
  experiment receipts. Product and operational source datasets are not replaced.
- **Real inventory** remains the normal default and source-read behavior is
  unchanged; live Start stays disabled. **Offline simulation** has a separate
  explicitly labeled snapshot, no network transport/credential reader and no
  automatic fallback from failed live reads. Source-access badges stay Not checked.
  Changing modes discards the previous snapshot/setup/run before loading another.
- Full mock outputs/diagnostics/evidence remain in the current local session,
  behind readable disclosure controls. No new DB, on-disk archive or external trace.

## Reproduce

The existing isolated UI profile adds an **optional** `offline-agent` dependency
group with the already approved `langgraph==1.2.20` and `langsmith==0.14.17` pins.
No new framework/service is selected; root and agent locks are unchanged. UI lock
now resolves 64 packages; local combined environment has 61 compatible packages.
The normal inventory-only setup still works without this optional group; selecting
simulation without it gives a provisioning instruction instead of a fabricated run.

```sh
uv sync --project tools/ui --locked --group offline-agent --no-python-downloads
LAUNCHLENS_UI_MODE=offline uv run --project tools/ui --locked --group offline-agent --no-python-downloads streamlit run streamlit_app.py
```

`LAUNCHLENS_UI_MODE=offline` only sets the initial UI selection. No API keys are
needed for simulation. Leave it unset for normal real-inventory startup.

## Actual verification

**320 offline tests PASS:** 185 agent, 111 root, 24 Streamlit UI (13 new integration
checks). The new integration tests block socket connections and assert **zero
attempts**, even with inherited `LANGSMITH_TRACING=true`. Coverage includes actual
UI submission through the same backend, request/notes binding, US review/revision,
UK/India, tool and malformed-output failures, original evidence/launch restrictions,
version identity, replay/rerenders, current-run replacement/reset, empty/stale
feedback, mode isolation and preserved real-inventory controls. Existing 185 agent
regressions include semantic-review counterexamples and authority safeguards.

Clean canonical copy: 24 UI tests PASS without workspace, private/generated data,
credentials or PDF originals, using the same explicitly provisioned combined UI
Python environment. Lock consistency and `uv pip check` PASS. No packages updated
in the separate root/agent environments. Initial offline lock resolution lacked
cross-platform registry metadata; normal PyPI metadata resolution succeeded. The
UI optional group installed the existing harness stack (28 additional packages,
including transitive dependencies); no inference or product-source calls occurred.

Two initial new test assertions were corrected: the form test must submit feedback
and its submit button together, and Not checked appears in both badge and tooltip.
No runtime validation or policy was loosened to pass those tests.

Chrome desktop checks verified US version 1 → explicit feedback → version 2/fresh
review, UK clarification and India Hold. All output remains explicitly simulated.
At 390px, Chrome checks confirmed readable wrapped draft/review text, usable
feedback controls and stacked lifecycle actions without observed content clipping.
Desktop and closed DevTools were restored. The new primary controls use dark text
on the existing periwinkle accent; verified visually. No cross-browser/physical-
device or full accessibility certification is claimed.

Syntax, relative documentation links, `git diff --check` and exact local credential-
value exclusion checks PASS. **321 of 336 baselined files remain unchanged**,
including MEMORY, accepted datasets, original prompts/projection, separate locks,
credentials and protected Writer history. Fifteen pre-existing files changed in
this checkpoint (including two development-state notes); five canonical files added.
No removed artifacts. The former tool fixture modules remain compatibility imports.
Source API and paid-model requests: **zero**; package-registry metadata reads and
optional local environment provisioning are the only new external setup activity.
Local server remains on port8520 in offline mode; current US version1/mock review
is ready for owner inspection. No Git staging, commit or push.

## Stop boundary

This connects a usable **offline** LinkedIn review journey, not a live autonomous
end-to-end demonstration. M2.3b content acceptance and prior checkpoint acceptance
remain separate. Next proposed: owner reviews this UI, then select explicit live
controller/Writer/Reviewer profiles and whole-run budgets for a separately approved
end-to-end test. Remaining formats, human acceptance/export, LangSmith and final
submission evidence remain later work. No ongoing paid-call or Git permission.
