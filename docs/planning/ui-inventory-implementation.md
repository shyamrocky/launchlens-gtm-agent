## M2-D050 — Home product-evidence status and header

**Owner-approved scope, November 10, 2026:** Home source card, shared header and
routing to the unchanged planned-Rebuild explanation only. Implemented; owner UI
review pending. No model call, evidence/source/index change or Git sync.

Source documents always shows a product-evidence line below Last checked and a
muted **Rebuild evidence (planned) ›** link. Index date reads `finished_utc` from the
existing successful `data/generated/m15b4-full-corpus/receipt.json`, checked against
the current index, namespace, embedding model and45-record count. Actual receipt:
2026-11-06T06:04:00.563850+00:00 → **Nov5,2026 Pacific**. It does not use file mtime,
current time or a fabricated configuration date. Missing/invalid/different-corpus
metadata displays index date unavailable / Not verified; it is optional display
metadata, not a new runtime provisioning requirement.

**✓ Up to date** requires both successful Drive PDF reads with actual digests equal
to the frozen indexed source digests, and a valid receipt. It is a source checksum
comparison, not a new Pinecone health test or launch permission. A changed Drive
checksum renders amber **Product brief changed · evidence not re-indexed**. Missing
reads and fixture simulation never claim current verified access. No network call
was added to obtain the index date; the existing source-check behavior is retained.

Restored the prior explanation body exactly from its accepted implementation;
byte-for-byte comparison PASS. It remains non-executable, outside the top nav.
Clicking its Home link and returning does not refresh sources or mutate runs.
The apparent header divider was the main scroll container's focus outline.
Removed that outline only; interactive link/button focus indicators remain.

**Verification:**105 offline UI tests PASS, including6 new tests for timestamp/
timezone provenance, malformed/missing/wrong-corpus metadata, matched versus changed
checksums, unverified/fixture states, explanation navigation with zero fetches and
scoped focus styling. Prior archive/Refresh/run UI regressions pass. Python syntax
and `git diff --check` PASS. All900 protected baseline files unchanged: sources,
indexed artifacts, prompts/configs, archives, runs, ledgers, .env and MEMORY.

Main8520 restarted; actual Chrome Home shows the date/status and muted link, clean
header and unchanged two-link nav. Opened the explanation and returned to the same
Home snapshot. Standard read-only Home source checks succeeded; no external writes
or model/Pinecone calls. Shared demo budget remains USD1.00, no current run started.
[Verified Home screenshot](screenshots/d050/home.jpg). No installs, Git staging,
commit/push or MEMORY append. Stop for owner review.

---

## M2-D049 publication checkpoint — November 10, 2026

Owner requested Git sync. A clean canonical copy passed422 harness,99 UI and112
root tests (633 total), without credentials, saved runs or workspace. Publication
review found one pre-existing test relying on the local standing ledger; it now
provisions its own private temporary fixture ledger. Runtime code and production
budget rules are unchanged by that test correction. Prior failed clean-copy checks
also used the minimal environment without jsonschema / omitted PYTHONPATH; corrected
commands reuse the existing UI environment with PYTHONPATH=src, without installs.
[Publication record](repository-sync-2026-11-09.md#archive-and-demo-reset-sync--m2-d049).
Earlier no-publication labels describe the implementation handoff, not this sync.

## M2-D049 — Archive, fresh demo allocation and navigation

**Date:** November 10, 2026. **Decision/status:** owner-authorized design implemented;
engineering verification complete, owner UI review pending. Archive moves active
run descriptors/pointers into a read-only archive and leaves protected originals in
place. Rationale: PMMs can start clean without losing drafts, approvals or accounting.
Alternatives rejected: deleting receipts, copying generated stores, resetting the
old budget or rebuilding evidence as part of a fresh run. No restore in this MVP.

**Delivered:** right-panel **Archive & start fresh**, Home per-market **Start fresh ›**
when a saved run exists, confirmation with Download first/Cancel, active-run block,
and **Archived packages (N) ›** with individual downloads. Confirmation opens that
market's Prepare screen; the agent starts only on Start agent. Nav now contains only
GTM launches and Current run. Refresh is in Source documents with Last checked and
the existing change summary. Rebuild is a checksum-mismatch notice only, remains
unimplemented and never runs from Refresh or archive.

**Actual reset:** ten existing US run records archived: six contained drafts and
four stopped before a draft. Both V2 records remain, including the earlier owner's
approved V2. There were no saved UK/India package runs; no placeholder archives were
created. No active records remain. All ten ZIP downloads passed integrity checks.
Home shows US drafting permitted, UK availability missing and India approval pending.
Current run is empty. A fresh US Prepare screen has an enabled Start agent; it was
not clicked. Main app restarted on port8520. Browser source reads succeeded for all
five documents; they made no model calls and changed no external records.

**Budget:** the owner explicitly authorized a new, shared USD1.00 allocation for
registered Cherry Float demo dry run and recording. It is provisioned in a separate
private ledger: USD0 accounted, USD1.00 remaining. The prior ledger remains exactly
USD0.3404722 accounted / USD0.6595278 remaining and is not reused or reset. Each
archive records its prior ledger reference/hash and totals. All future demo runs,
required reviews, retries and revisions share the new allocation; unknown-usage
reservations and existing per-call/run limits still apply. Archive, Refresh, app
rerender and Start never refill it. Standing spending approval does not trigger a
call. Existing model/profile qualification and expiry checks still apply; this
checkpoint did not requalify providers or alter the frozen profile.

**Private storage/provisioning contract:**

- `data/private/runs/active/<run-id>.json` owns the active descriptor. Archive uses
  a catalog lock and renames it to `runs/archive/<run-id>/record.json`. Matching
  current-live-run/current-review pointers also move into that archive directory.
- Protected `data/generated/` bytes stay in place. Archive records bind all original
  version checkpoints, decisions, reviews, approval/export receipts and captured
  accounting by relative path and SHA-256. ZIPs are built in memory on demand,
  including per-version Markdown and the simulation label. Nothing is copied into
  archive storage; missing/tampered originals fail download explicitly. Keep both
  ignored private catalog and original generated stores in a local backup.
- The shared ledger can continue accumulating spending after archive, so its hash
  is a historical reference, not a requirement that the mutable ledger never change.
  Original per-run captures and recorded prior totals remain frozen. Archived IDs
  cannot append checkpoints, reserve another call or become active through stale UI.
- Explicit one-time operator reset uses `discover_legacy_runs()` / `archive_run()`;
  normal Home reads do not scan experimental stores. Budget provisioning is
  `launchlens.run_archive.provision_demo_budget()` and refuses an existing session.
  Never invoke it merely to bypass an exhausted allocation. It creates0600 private
  `demo-session.json` and a unique demo-budget ledger, bound to current profile and
  package hashes. New run grants use this ledger; historical grants keep their own.
- A clean checkout without these local artifacts shows an empty catalog and no
  provisioned live demo allocation. Offline tests use safe temporary fixtures;
  application/build/tests have no new dependency on `workspace/`.

**Verification:** **633 offline tests PASS**:422 harness,99 UI,112 root. Includes
actual descriptor moves, unchanged original bytes, active-run refusal, Download
first, per-market preservation, approved-receipt binding, all-version ZIPs,
mutable-ledger independence, stale-run rejection, fresh scoped grants and shared
budget exhaustion before a provider call. UI tests cover confirmation/Cancel,
archive list, empty Current run, two-link nav, Refresh relocation and mismatch-only
rebuild notice. Existing single-run and source/approval preservation regressions
pass. No packages installed. `git diff --check` PASS.

Preservation audit:887 baseline protected files verified;885 unchanged in place,
exactly two current-pointer files moved with identical hashes, zero unexpected
changes. All generated receipts, source datasets, templates/configs/prompts,
credentials, MEMORY and prior accounting unchanged. New local catalog/ledger
files remain ignored. No model calls, Pinecone writes, source edits, Git staging,
commit or push. Browser visual/interaction check completed in Chrome; Safari's
local-page memory reload problem was bypassed without changing the application.

Screenshots: [Home](screenshots/d049/home.jpg),
[empty Current run](screenshots/d049/empty-current.jpg),
[archive list](screenshots/d049/archives.jpg),
[confirmation before reset](screenshots/d049/confirmation.jpg).
Stop for owner review. Next user journey: GTM launches → market Open brief →
Prepare → Start agent, within the same shared USD1.00 demo allocation.

---

## M2-D046 — Read-only format tones

Prepare now shows the core Tone row and expandable five-format tone lines from
voice_policy_v2.json. Package labels each deliverable with its configured tone;
computed length/exclamation warnings are advisory and never block approval.
Notes remains creative steering; editable tone presets are future scope.
[Canonical policy/wiring/results](writer-run-experience-review.md#m2-d046--shared-per-format-tone-policy-and-measurable-checks).
93UItestsPASS; native fixture-only screenshots: [Prepare](screenshots/d046/prepare-tones.jpg),
[Package](screenshots/d046/package-tones.jpg). No live calls or main8520 restart.
Temporary8524 preview has external connections blocked. Stop for owner review.

---

## M2-D045 — Refresh completion summary

**Owner direction, November 10, 2026:** show what changed after Refresh, or No
changes; show Last checked in Source documents. Optional action relocation was
not taken: Refresh data remains in the existing header alongside Rebuild evidence.

The existing refresh handler compares the preceding Home snapshot with the newly
read one. Lists per-market planned launch date and four readiness-status changes,
including `India · Marketing authorization: Pending → Approved`. Changes to blockers,
supporting references and status dates are also identified without repeating source
prose. Source-access changes and changed PDF digests are reported. Timestamp-only
changes and row ordering do not count. Successful unchanged comparison displays
**Updated · No changes**; incomplete/missing reads or missing comparison baselines
show an explicit incomplete notice instead. First load has no invented comparison.
Demo results are labeled Simulation updated and never claim live source reads.
The source card now shows **Last checked <time>** with date/timezone; per-file checks
retain their existing precise timestamp tooltips. Latest result stays associated
with that Home snapshot; navigation does not fetch again. Mode replacement clears
its prior result. Current run, captured evidence, decisions, approval and accounting
stay unchanged; active-run Refresh guards still apply. No rebuild or model call.

**Verification:**91 UI tests PASS (four new plus existing regressions). Mocked India
approval/date/blocker changes, unchanged data, shuffled records, incomplete reads,
source changes, completion rendering, timestamps and no-refetch navigation checked.
Actual saved USVersion2 AppTest: zero network and same run/state/capture/decisions/
approval/accounting after mocked refresh. Native Safari on8520 performed a real
read-only Refresh: **Updated · No changes**, all5 sources accessible and Last checked
10:34 AM displayed. No actual Notion value was changed for testing: the India change
case is fixture verification, not a claim of live India approval. 745 protected file
hashes unchanged, including saved runs/approval, source data, credentials, budget and
MEMORY. Syntax/whitespace PASS. No dependency, Git staging/publication or next milestone.
Broader harness/root suites not repeated for this UI-only change; D043 records
prior full-suite results. [Verified page](screenshots/d045/refresh-no-changes.jpg).

The Home summary describes refreshed source data, not a retroactive permission
change to a saved run. Existing runs keep their original captured snapshot. Rebuild
evidence remains an explicitly unimplemented placeholder. App restarted on8520;
stop for owner review.

---

## M2-D044 — Rebuild evidence in top navigation

**Owner correction, November 10, 2026:** Rebuild evidence belongs beside GTM
launches, Current run and Refresh data; selecting it shows the placeholder card.
Moved the same non-executable card out of Home's Source documents column into a
single selected Rebuild evidence view. No duplicate card, confirmation or rebuild
handler. Widened the header navigation for four readable options; narrow CSS wraps
it to two rows. Current run/evidence/approval and Refresh guards are untouched.

**87 UI tests PASS**, including a navigation regression verifying the four choices,
exactly one disabled placeholder, Home-card removal, no source fetch on navigation
and unchanged current run/capture. Updated mismatch test opens the new view.
Native Safari verified the full header, Home without the duplicate card and the
selected placeholder view. Read-only source checks on app reload passed; no model
calls, embeddings, Pinecone operations, owner decisions, approval or revision.
745 protected file hashes unchanged, including saved USVersion2 and its approval,
credentials/budget/sources/generated artifacts/MEMORY. Whitespace check PASS.
Broader harness/root suites were not rerun for this navigation-only follow-up;
D043's585-test result remains the prior full verification. No installs or Git sync.

Screenshots: [navigation](screenshots/d044/navigation.jpg),
[Rebuild evidence view](screenshots/d044/rebuild-view.jpg).
App8520 restarted; click the fourth header option. Stop for owner review.
This supersedes D043's placement below Sources only; all its refresh behavior stays.

---

## M2-D043 — Run-preserving Refresh and Rebuild evidence placeholder

**Owner authorization, November 10, 2026:** fix Refresh only; add a disabled,
clearly labeled Rebuild evidence information card. No rebuild implementation,
model calls, ingestion, Pinecone writes or Git publication.

Refresh now replaces only the homepage/source snapshot, preserving the current
run object, captured evidence, decisions, approval, notes, selected task, counters
and current page. Source failures replace homepage permissions without altering
run evidence. Previously documented refresh-clears-run behavior is superseded.
An active run means created/queued, executing, paused for clarification, a queued
command or pending revision. Both button and handler block refresh, displaying
“Finish or stop the run to refresh” as disabled-button help (and a warning if the
handler is called directly). A held/stopped/failed run or a completed package
awaiting human review may refresh safely. Execution modes cannot be switched
while active; an explicit idle mode switch retains its existing reset behavior,
separate from Refresh. Missing-cache initialization cannot bypass the run guard.

Drive checks use the same fixed source SHA-256 identities as retrieval's verified
indexed corpus (retrieval.SOURCES), rather than a duplicate hash list. Refresh
makes no Pinecone query: this is the frozen registered corpus identity, not a
new remote index inventory. A valid PDF with a differing hash reports changed,
retains observed/indexed digests and shows an amber “Product brief changed —
evidence not re-indexed” warning (document-specific wording for Synthetic PRD).
HTML/login responses, oversize files and access failures remain unavailable.
No changed bytes are retained, accepted or indexed. Authority separation stays.

The Home right column now includes **Rebuild evidence / Not implemented** with a
permanently disabled “Coming later” action and no execution/confirmation handler.
It describes future document acceptance and claim mapping; separate build,
verification and activation; export before removal of affected product runs and
protected audit-history preservation. These are future requirements, not active
capabilities. Actual rebuild/embedding spending and run invalidation remain deferred.

**Fresh verification: 585 tests PASS** (387 harness,86 UI,112 root), including
six new tests and updated obsolete refresh-reset expectations. Socket-blocked
AppTest verified completed-run/decision/approval preservation, notes/date retention,
active/queued/locked/clarification guards, failed refresh isolation, mismatch badges
and the non-executable placeholder. Actual saved US Version2 was also loaded in
AppTest with zero network: mocked refresh updated Home only; the same run/evidence,
approval/decisions and full capture/accounting remained identical.

Native Safari on8520 verified the card and performed one explicit real Refresh
while viewing the saved approved V2. Home timestamp advanced from10:01:46 to
10:02:48 AM PST; all five source access checks passed. The current run stayed on
V2 with3 kept choices, approval,1/3 revisions and$0.71 unchanged. Source reads only;
no model calls, embeddings or Pinecone operations. No owner wording choices,
revision, new approval or export was executed. All745 protected file hashes match
before/after, including source datasets, private receipts/approval, budget,
credentials, generated artifacts and MEMORY. Syntax and whitespace checks PASS.
No installs or required workspace dependency. Checksum mismatch was simulated
only; no actual source was modified to test it. No mobile-device test claimed.

Screenshots: [Home](screenshots/d043/home.jpg),
[disabled rebuild card](screenshots/d043/rebuild-placeholder.jpg),
[approved V2 after Refresh](screenshots/d043/approved-after-refresh.jpg).

App8520 restarted to load this change. Stop for owner review; no Git sync or
Rebuild execution authorized. Historical implementation receipts below remain.

---

## UI-D009 — Existing harness connected in explicit offline mode, 2026-11-09

Owner approved checkpoint 2. [M2-D020](ui-agent-integration-review.md) is the
canonical integration record and supersedes UI-D008's disabled-Start statement
only for the explicit offline simulation. Real inventory remains read-only and
live Start disabled. Same app/preparation route; fixture data is separately labeled,
with no live-source fallback or green access badges. Existing dark presentation,
real source-read behavior and accepted UI-D007 scope remain preserved. New run view
shows the actual harness ledger, draft/evidence, mock findings, explicit feedback,
one revision/re-review and current-run lifecycle. Technical PASS320offline tests;
owner review pending. No inference, source writes, export, tracing or Git sync.

# Market preparation — replaces the existing brief screen

Decision ID: UI-D008. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner approved the reviewed preparation-screen refinement and explicitly
requested replacing the existing screen rather than stacking pages.
Status: implemented locally; technical verification PASS; owner review pending.

## Behavior and source ownership

The existing `brief_page` function / `screen="brief"` route is replaced in place.
Dark theme retained, centered max-width720px, one column. Back returns to the same
fully expanded inventory. Header's Current brief becomes Current setup. Product,
registry objective and source-derived planned launch date appear once. Two-row
summary shows objective and the current LinkedIn scope; UK is paused and India
shows Promotional package blocked. No new standalone page or source dataset.

Gate display comes only from the existing `evaluate_launch`, recomputed against
cached authoritative Notion records for the selected evaluation date. US: Drafting
permitted; UK: Availability not confirmed; India: Promotional drafts blocked.
Other date/conflict conditions get Readiness needs clarification. Missing/incomplete
sources get Unable to verify readiness. Known blocking policy remains dominant.
No permission is accepted from UI text, notes or a model. Details defaults collapsed:
four checks, only actual blockers (no literal None), unresolved conditions, material
pre-launch restrictions and source/evaluation-date explanation. Optional date editor
recalculates in place; never changes the calendar or triggers a source/model read.

Notes are bounded1000characters, kept separately per market in session state and
preserved through navigation. They are guidance only: no registry/request/policy
changes and no fabricated run initial state. Explicit Refresh clears notes/date
widgets and the old selection/snapshot before the existing read process. All Start
agent buttons are visibly disabled with an honest not-connected caption. No fake
toast run, thread ID, generation, Reviewer promise or new India research-only path.
The source panel remains on the homepage only; Save brief, Launch brief, Launch
decision, duplicate objective, old banners and raw record dump are removed from
this screen. The development-stage explanation is documented in README instead.

Rationale: a PMM should understand what is being prepared, why drafting is permitted
or paused, and how to start once integrated. Alternatives: retain the ambiguous
brief editor, add a second screen, adopt light theme, or wire unapproved agent/
research-only behavior. Those alternatives were not adopted. Current policy,
source readers, prompts, evidence, models, dependencies and historical receipts
remain unchanged. Earlier UI-D007 acceptance/publication remains historical; it
does not automatically accept this additional refinement or close M2.3b content.

## Actual verification

- **122 offline tests PASS:111existing root +11Streamlit UI.** Network is blocked
  in UI tests. US/UK/India state copy, disabled start, collapsed details, no source
  panel/old controls/literal None, date recalculation, missing source/check/calendar,
  pre-launch available-now restriction, back/current navigation and explicit refresh
  are verified. Instruction-like notes cannot alter the admitted request or Hold;
  notes do not become executable HTML, and no run is created. Existing root tests
  cover source/launch-policy regressions. Initial new assertions looked for caption
  blocker text in markdown-only results; corrected the test to inspect both.
- Actual Chrome desktop screenshots inspected for US, UK and India with the real
  existing source reader. US Details shows four approvals.390px responsive India
  view inspected from title through footer: summary stacks cleanly, gate explanation,
  Details, notes and disabled button remain readable. Device mode/DevTools restored
  to normal desktop; US preparation left open. Not cross-browser/device certification.
- The normal UI first load checked existing read-only sources. Navigation reused
  the same snapshot timestamp (Nov08,2026,11:56:29PM PST); all five access badges
  were accessible on the homepage. No separate source validation campaign, paid
  inference, external write, corpus change, dependency install or Git publication.
- Scope/hash, syntax, whitespace, privacy and workspace-boundary review completed.
  No application/build/test/deployment requirement added inside workspace. MEMORY
  and unrelated Writer experiments/history remain unchanged.

Review at http://127.0.0.1:8520/ → Open brief. Next agent/Reviewer integration and
any live call require a separately approved checkpoint. Stop for owner review.

---

# UI milestone acceptance

Decision ID: UI-D007. Date: 2026-11-08 (America/Los_Angeles).
Status: owner accepted; scoped publication authorized.

## Owner acceptance and scoped Git sync — 2026-11-08

Owner described the completed UI as a good milestone and explicitly requested Git
sync. The real inventory/brief UI and its source-access/presentation refinements
(UI-D002 through UI-D006) are **OWNER ACCEPTED / CLOSED** for this bounded slice.
UI-D001 is preserved as design history. This accepts registry-driven discovery,
read-only source checks, launch-aware brief selection and the reviewed layout;
it does not accept M2.3b content or authorize agent/Writer/Reviewer integration.

Publish only the canonical UI code/configuration, isolated locked Streamlit profile,
UI/source tests and supporting design/setup/acceptance records after exact-diff,
confidentiality, reproducibility and private-visibility review. Unfinished Writer
experiments, credentials, workspace, generated receipts and environments remain
local. No source writes, inference or next milestone is authorized. This latest
owner instruction supersedes earlier UI-only pending-review/no-publication text;
previous verification and audit history remain intact.

## UI-only publication verification

The publication candidate is the existing committed baseline plus exactly18 UI
code/config/test/documentation files. Shared README/instructions/milestone/plan
files include only their UI additions; unrelated unpublished Writer work stays in
the working tree. The existing committed registry/source/policy implementation is
used unchanged. No incomplete Writer or Reviewer implementation is included.

Fresh clean-candidate verification: **109 tests PASS (103root +6Streamlit)**;
UI lock consistency PASS offline (35resolved packages, Python3.12.15). The initial
full root run stopped because its documented parsed-page inputs were absent.
Running the existing local prepare_documents.py in the scratch checkout regenerated
those ignored inputs, then all103root tests passed. The actual project outputs
were not touched. UI clean-copy startup separately PASS without workspace,
generated data, .env, inherited keys, local PDFs or network: unavailable states,
disabled date-dependent actions, no repeat reads and no model modules loaded.

Exact candidate review: credential-value scan, Python/JSON parsing,84relative
links, scoped file paths and ignore boundaries PASS. Remote GitHub API confirmed
private=true,visibility=private and main matching the local pre-sync baseline.
Staged contents and final remote commit will be checked before handoff; no fresh
live source/model call is part of publication verification.

---

# Compact header and grouped navigation — current refinement

Decision ID: UI-D006. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner requested closing the tagline/source-check gap, moving the page
up and placing GTM launches / Current brief / Refresh data inside one rectangle.
Status: implemented locally and verified; owner visual review pending.

Grouped the existing header and source-check caption in one compact container,
removed surplus brand/tagline margins, reduced top padding by8px and used6px
container spacing. The existing three native navigation buttons now share one
subtle bordered rectangular container. Active, disabled and accent states remain.
At narrow width, the group sits beneath the branding with all three actions in
one readable row. No source/check timestamp, button action, task or policy changed.

Rationale: bring the title, tagline and source status into one coherent header and
reduce wasted vertical space. Alternatives: preserve the large gap, or add three
separate button boxes. Chosen: one navigation rectangle and closely attached status.
This supersedes earlier unboxed-header presentation only; product/source layout stays.

Fresh verification: **six Streamlit UI tests PASS** for existing rendering, status/
timestamp details, market navigation, refresh behavior, failed-source permission
clearing and date-policy controls. Chrome desktop inspection confirms the reduced
gap, navigation rectangle and raised content;390px viewport inspection confirms all
three labels fit inside the box without observed clipping. Desktop restored and
DevTools/emulation closed. This is viewport simulation, not a physical-device audit.
Navigation/viewport tests retained the same source snapshot timestamp. Normal initial
read-only checks ran after the presentation-server restart; no new dedicated source
audit or full299-test rerun claimed. No inference, source write or new dependency.

Canonical change is inventory_ui.py/css plus this report and existing current
continuity/instructions. Source readers, launch policy, registry, datasets, prompts,
credentials, locks, historical receipts, MEMORY and Git state remain untouched.
Local app: http://127.0.0.1:8520/. Stop for owner review; no Git publication or
agent/Reviewer implementation. Main milestone scope/acceptance remains unchanged.

---

# Balanced inventory layout — current refinement

Decision ID: UI-D005. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner approved reducing the gap, improving product-card positioning and
checking actual sizes/alignment before handoff. Status: implemented and verified
locally; owner visual review pending. This supersedes UI-D004's outer-column ratio.

The page uses more available width (1440px maximum, with responsive padding). The
product occupies approximately two-thirds of the desktop card grid; Sources uses
one-third. The two cards align at their top edges with a **24px gap**. Product
heading/brand/description/metadata spacing is tighter. Campaign objective is now a
small label and a separate19px value, subordinate to the25px product name. All
three markets remain open. Source group layout, genuine badges and focusable
checked-time details remain; link wrapping is balanced. No forced equal heights.

At1100px and below, the main cards stack vertically before their contents become
cramped. Source groups respond to actual card width through a container query;
metadata and market controls retain their native narrow-width stacking. Content
stays in normal page flow without a clipped square or internal card scrollbar.

Rationale: preserve the product/market inventory as the primary PMM task while
keeping supporting documents close and legible. Alternatives: squeeze the product
to maintain a square sidebar, or retain the wide separation. Chosen: wider overall
layout, approximately2:1 columns, compact content hierarchy and responsive stacking.

## Actual verification

**Six Streamlit UI tests PASS**, including all five documents and their genuine
status distinctions, tooltip references/keyboard-focus markup, the revised objective
hierarchy, all three market-to-brief paths, failed refresh, no repeat reads on
navigation/rerender and policy-preserving evaluation-date edits. This is a focused
UI rerun; the earlier299-test result below is historical, not rerun here.

Chrome responsive viewport checks used the real running app and the Elements /
Computed panels; no page script was required for the measurements. Inspection found
Streamlit's intervening stLayoutWrapper element; selectors were corrected and the
**rendered computed styles** rechecked, rather than relying on stylesheet intent.

| Viewport width | Actual grid width | Actual direction | Computed gap |
|---|---|---|---|
|1440px|1376px|row|24px|
|1280px|1216px|row|24px|
|1024px|960px|column|24px|
|768px|704px|column|24px|
|390px|358px|column|24px|

Computed alignment is flex-start. Desktop screenshots show both cards sharing a
top edge, the wider product card, readable date/metadata/status rows and all five
source links. At390px, scrolling confirms readable market actions and all five
sources stacked within the viewport, without observed text clipping. These are
Chrome viewport simulations, not a physical-device or cross-browser certification.
Normal desktop view was restored and DevTools/device emulation closed before
handoff. The unchanged browser snapshot retained the same source-check timestamp
through navigation and viewport changes. Existing first-load read-only checks ran
normally after the server restart; no new dedicated source audit is claimed.

Canonical changes: inventory_ui.py/css, existing UI tests, this report and current
continuity/instructions. No source reader, launch policy, registry, dataset,
credential, dependency, prompt, model, response history or workspace runtime
requirement changed. No inference, source writes, MEMORY update or Git publication.
Local app remains http://127.0.0.1:8520/; stop for owner review. Overall M2.3b and
Reviewer/main delivery scope remain open.

---

# Compact Sources card — current refinement

Decision ID: UI-D004. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner approved the proposed compact, roughly square Sources card.
Status: implemented locally, awaiting owner visual review.

The wider right-hand card groups Google Drive and Notion side by side, tightens
heading/document spacing and keeps all five links and role descriptions visible.
Compact per-document status labels replace repeated visible timestamps. Hovering
or keyboard-focusing a status reveals its original checked date/time; each focus
point has a document-specific accessible label and linked tooltip. The timestamp
and source result are unchanged. No fixed height, clipped contents or inner scroll.
Narrow layouts stack the groups as needed; normal page scrolling remains available.

Rationale: reduce the sidebar's excessive vertical height while retaining readable
source identity and genuine access evidence. Alternatives: rigid square with clipped
or internally scrolling contents; retained narrow vertical list. Chosen: natural,
responsive proportions with compact details. All launch and source-check behavior
remains unchanged; no provider, dataset, prompt, registry or dependency change.

Fresh offline verification: **six Streamlit tests PASS**, covering rendering of all
five links, correct status distinctions, timestamps, five keyboard-focusable status
labels linked to five tooltip IDs, both source groups, market/brief navigation,
refresh/no-repeat-call behavior and existing launch restrictions. Prior299-test and
live-access results below remain historical; no new full-suite execution is claimed.
Chrome desktop inspection confirmed the roughly square card, side-by-side groups,
all five visible links/statuses and readable descriptions. Focusing the Product
Brief status revealed its timestamp; two Tab presses moved to the Synthetic PRD
status and revealed its own timestamp. No external document link was opened.
Desktop verification only; no mobile-device matrix claimed.

The local server was restarted only to load presentation changes; browser startup
uses the existing read-only source checks. No model calls or source writes.

Runtime/setup remains http://127.0.0.1:8520/. Canonical changes are inventory_ui.py,
inventory_ui.css and the existing UI tests, with this review and current continuity
notes. No workspace runtime dependency. Stop for owner review; no Git publication,
MEMORY update, generation/Reviewer work or milestone advancement.

---

# Homepage polish and source-access checks — current checkpoint

Decision ID: UI-D003. Date: 2026-11-08 (America/Los_Angeles).
Authority: explicit owner approval of the six homepage refinements and genuine
source-access checks. Status: implemented locally, technical PASS; result awaits
owner review. No M2.3b content acceptance or agent/Reviewer/Git authorization.

## Delivered refinement

- Tagline: **Your launch-aware GTM agent.**
- Campaign objective: **Introduce Cherry Float’s flavor**, retaining the existing
  flavor_discovery ID and meaning, not consumer research or taste testing.
- Concise source roles; five direct document text links. Native tertiary navigation
  and **Open brief ›** actions, with keyboard/focus behavior preserved. Periwinkle
  links/actions; active navigation white; two primary card borders retained.
- Status dots green #30D158, amber #FF9F0A, red #FF453A, with text labels. Opaque,
  brighter secondary text; no horizontal divider behind the header/navigation.
- Each source shows **✓ Accessible · checked [local date/time]**, **Not checked**,
  or **Access unavailable · checked [local date/time]**, using actual recorded results.

## Access semantics and bounded execution

First session load and explicit Refresh data check sources. Navigation, brief edits
and ordinary rerenders reuse the same snapshot and timestamps; no periodic checks
or retries. Refresh removes the preceding snapshot and brief before reading again.
A new browser session performs fresh reads. The completed timestamp includes failed
checks; individual badges say whether their read passed. It is not continuous monitoring.

The two Drive PDFs each receive one anonymous HTTPS GET to the existing Google
usercontent download endpoint: no browser session, cookies, OAuth, redirects,
proxies or retries. Twenty-second timeout, one-megabyte bound. HTTP200 viewer/login
HTML is rejected. A green check requires PDF header/EOF and the **exact frozen
approved SHA-256** from the accepted originals (listed in the historical
[M1.5a report](m1.5-connectivity-validation.md)). This verifies byte identity to the
previously integrity-tested PDFs without adding another parser or dependency.
Downloaded bytes remain transient; no PDFs are saved or ingested. Changed content
is unavailable to this check, even if its sharing link still opens.

Notion reuses the existing scoped reader and read-only credential. Calendar and
readiness badges require all three scoped contexts to be completely read. This is
conservative: an incomplete joint read marks both operational sources unavailable
rather than guessing which partial data is usable. PMM requires the existing full
nested/paginated read to succeed with nonempty content. Notion's existing sixty-call,
response-size/depth/pagination limits remain unchanged. PMM text is not retained in
this inventory snapshot; only its result/block count and safe read events remain.

Access is established for this application's anonymous Drive reader or configured
Notion connection at the displayed time; it does not establish the viewer's personal
Notion permissions, launch approval, content acceptance or semantic consistency.
Operational permission continues to come solely from the unchanged launch policy.
Sources are checked independently of marketing outcomes: India can have accessible
files while promotional drafting remains on Hold. Source-check results cannot grant
permission or override missing launch data. A failed PDF/PMM check affects its badge;
this checkpoint has no generation action to enable.

Maintained new helper: src/launchlens/source_access.py. Presentation/configuration
and focused tests extend the existing inventory files and UI profile. The inventory
helper's default lightweight mode does not check PDFs/PMM; the real UI explicitly
sets verify_documents=True. No dependency or credentials changed. No workspace,
generated snapshot or local PDF is required by the runtime checks. Only the existing
approved Markdown display binding remains a normal canonical startup dependency.

## Actual verification

**299 offline tests PASS:**111root (six new source-access tests),159agent,
23embedding and six Streamlit tests (one new badge/rendering test). Tests cover
exact approved bytes, HTTP200 HTML, changed/oversized PDFs, denied/failed reads,
no credentials/retries/redirects, unapproved IDs never requested, independent source
failures, Not checked fallback, timestamps, tertiary controls, five text links,
registry/date/policy preservation and navigation/refresh behavior. Existing checks
still exercise clearing old permissions and unsupported scope. Mocks establish
behavior only, not hosted access. Commands are the same four unittest commands
recorded below. Expected negative-fixture messages and bare-AppTest warnings remain.

Fresh clean-copy startup PASS without workspace, generated files, .env, inherited
keys, local PDFs or network. Missing access displays unavailable, dependent market
actions disable, rerender makes no additional requests, no Writer/model module loads.

Dedicated live validation completed **2026-11-08 17:15:46 PST**:

| Source | Verified result |
|---|---|
| Product Brief PDF | HTTP200;9,460bytes; approved SHA-256 match |
| Synthetic PRD PDF | HTTP200;7,790bytes; approved SHA-256 match |
| PMM / GTM Brief | Complete read;102blocks |
| Calendar | 9records /126values match accepted CSV |
| Readiness | 12records /108values match accepted CSV |

**26 Notion requests, all HTTP200; two Drive GETs, both HTTP200.** Zero retries,
model calls or source writes. Protected optional snapshot/receipt:
data/generated/ui-source-access-validation-v1/ (directory0700/files0600). These
receipts are audit evidence, never runtime/test prerequisites. A separate live
browser session also read sources; its requests are not counted in this receipt.

Chrome inspection confirmed the tagline, borderless navigation, source text links,
stronger status dots, all five timestamped checks and no crossing header divider.
UK Open brief retains Jan4,2027 and actual missing-availability Clarify; returning
home retains the same source-check timestamps. US Proceed / UK Clarify / India Hold
remain derived from unchanged records at their respective planned dates.

Rendered contrast was checked from actual Chrome screenshots, converted using the
embedded color profile to sRGB. Sampled solid glyph interiors in source descriptions
and the small product note measured approximately **8.36:1 or greater** against
rendered card backgrounds; footer **9.59:1 or greater** against rendered page
background. This includes the rendered composition, not palette values alone.
Capture compression/antialiasing means these are sampled estimates, not a complete
accessibility certification. Explicit secondary-text opacity is1; nominal contrast
is8.86:1 on cards /10.18:1 on the page. Desktop Chrome checked; no mobile matrix.

## Boundary

Keep the local real app on **http://127.0.0.1:8520/** for owner review. No inference,
agent/Reviewer integration, generation, source writes, dataset/prompt/policy changes,
new dependency, Git staging/commit/push or MEMORY update. Earlier UI-D002 below is
preserved as historical evidence; its unverified-source wording is superseded by
this checkpoint. Existing roadmap and M2.3b content acceptance remain open.

Implementation references: [native tertiary buttons](https://docs.streamlit.io/develop/api-reference/widgets/st.button)
and [HTML/CSS rendering](https://docs.streamlit.io/develop/api-reference/text/st.html).

---

# Real launch inventory UI — bounded checkpoint

Decision ID: UI-D002. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner explicitly approved the proposed Real Launch Inventory UI after
reviewing the mockup. Status: implemented locally, technical PASS; owner acceptance
pending. This does not close M2.3b or authorize Writer/Reviewer execution or Git sync.

## Delivered behavior

Streamlit inventory → select a market → prefilled brief. All market rows remain
visible; source documents occupy a right-hand card. The approved dark/system-font
design is adapted to native Streamlit controls. The interface is functional, not
the historical HTML simulation. No agent, model or generation call is registered
in this UI checkpoint. Save brief stores the supported request in session memory.

| Displayed information | Authority |
|---|---|
| Available use case, markets, objective, planned outputs | Existing harness registry |
| Name, brand and short description | Owner-approved display metadata; description bound to accepted Product Brief SHA-256 and PROD-002/PROD-003 |
| Market dates and overall launch window | Fresh normalized Notion Calendar records, no configured dates or CSV fallback |
| Drafting permitted / clarification / hold | Existing evaluate_launch policy using Notion readiness at the stated evaluation date |
| Google Drive PDFs / Notion resource links | Existing approved document IDs and scoped Notion resource constants |

Readiness on the homepage is explicitly evaluated at each **planned launch date**,
not the current day. The selected brief allows an explicit evaluation date and
recomputes policy using that same fetched snapshot. Future readiness cannot grant
retrospective permission. The launch window requires all market dates. Missing,
ambiguous or contradictory calendar data displays unavailable; no date is invented.

The first session load reads Notion once. Navigation, form edits and rerenders reuse
the snapshot. Refresh data explicitly replaces it and clears the selected brief;
a failed refresh cannot retain an earlier green label. A new browser session starts
a new read. Snapshots are not continuously refreshed or automatically expired.
The existing transport retains scoped endpoints, bounded pagination, TLS, request
budget and no automatic retries. There are no Notion/source writes.

Product facts, fictional product intent/PMM direction and fictional operational
readiness retain distinct roles. This real application still uses an independent
fictional educational launch scenario. Publishing remains disabled. Planned output
names describe future scope, not completed multi-format generation.

## Reproducible setup and access

Python 3.12.15, uv 0.13.0; isolated UI environment. Only direct UI dependency is
Streamlit 1.67.0, pinned in tools/ui/pyproject.toml and uv.lock. Existing root,
embedding and agent dependency profiles remain unchanged.

From the repository root:

```sh
uv sync --project tools/ui --locked --no-python-downloads
uv run --project tools/ui --locked --no-python-downloads streamlit run streamlit_app.py
```

Open **http://127.0.0.1:8520/**. This is the real application. Port8765 remains the
optional historical mockup. Bind127.0.0.1 only; Streamlit usage telemetry and file
watching are disabled in the canonical .streamlit/config.toml. CORS/XSRF defaults
are preserved. No deployment or public hosting added.

Supply NOTION_API_KEY as a process environment variable or the existing local
ignored .env with owner-only permissions (0600). Duplicate/missing/malformed keys
or loose file permissions fail safely; do not paste credentials in the UI or docs.
The existing read-only connection must retain access to the approved Calendar and
Readiness data sources. No other provider credential is required for this UI.
Drive links use existing shared files; Notion links require the viewer's own access.
Link destinations are rendered, but this page does not download PDFs or fetch the
full PMM brief and does not claim fresh authorization checks for every file.

Maintained implementation: streamlit_app.py; src/launchlens/inventory.py,
inventory_ui.py and inventory_ui.css; data/templates/gtm/launch_inventory.json;
tools/ui locked profile; tests/test_inventory.py and tools/ui/tests/.
No application, setup, test or safety gate requires workspace or generated receipts.
The old mockup remains a design reference, superseded for runnable inventory.

## Actual verification

Offline total **292 PASS**:105root tests (8new inventory),159agent,23embedding and
5new Streamlit AppTests. Checks cover real registry scope, source-driven date/status
changes, ambiguity/unavailable sources, private credential handling, no fixture/CSV
fallback, unsupported scope, no inference/source reread on navigation/rerender,
one explicit refresh, failed refresh removing old permissions, and editing the brief
date without overriding launch policy. Mocked providers prove application behavior,
not live source compatibility. Existing negative-fixture messages are expected.

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python -m unittest discover -s tools/agent_foundation/tests -q
PYTHONDONTWRITEBYTECODE=1 tools/embedding_preparation/.venv/bin/python -m unittest discover -s tools/embedding_preparation/tests -q
PYTHONDONTWRITEBYTECODE=1 tools/ui/.venv/bin/python -m unittest discover -s tools/ui/tests -q
uv lock --project tools/ui --check --offline --no-python-downloads
```

Clean-copy startup PASS without workspace, generated records, .env, inherited keys
or network: displays unavailable and disables date-dependent Open actions.

Read-only live validation at2026-11-08T23:30:54Z: **14Notion requests, allHTTP200**.
All9calendar records/126field values and12readiness records/108field values match
the approved local CSVs and their pinned hashes. These are comparisons, not fallback
inputs. Date/window/policy results:

| Market | Planned date = evaluation date | Observed decision | UI label |
|---|---|---|---|
| US | 2026-12-14 | Proceed | Drafting permitted |
| UK | 2027-01-04 | Clarify | Availability confirmation missing |
| IN | 2027-01-18 | Hold | Marketing approval pending |

AppTest navigation using this live snapshot PASS for all three markets without
additional source reads. Protected optional audit receipt/snapshot at
data/generated/ui-inventory-validation-v1/ (directory0700/files0600); not required
to run or test the application. No model calls, retries, repairs or source writes.

Chrome inspection confirmed the real inventory, live fetch timestamp, all three
market rows, real document URLs and UK brief with Jan4,2027 and the actual missing
availability condition. Returning home preserves the fetch timestamp. Browser
session source reads are separate from the14-request validation receipt; no global
browser request count is claimed. Desktop inspection only, no mobile browser matrix.

## Completion boundary and next step

Stop for owner review of the real inventory/brief. Full autonomous research/drafting,
Reviewer, revision, remaining formats and export integration remain on the existing
LinkedIn-first roadmap; no milestone acceptance or model adoption is inferred.
No Git staging, commit or push. Historical reports, datasets, responses, credentials,
MEMORY, accepted dependency profiles and original harness/source/prompt behavior
are preserved. This scoped UI delivery advances a discovery slice of integration,
not the entire previously proposed Streamlit/agent milestone.

Primary implementation references:
[Streamlit 1.67.0 release](https://pypi.org/project/streamlit/1.67.0/),
[native containers](https://docs.streamlit.io/develop/api-reference/layout/st.container),
[AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest),
[configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml).


## M2-D051 — Browser disconnect recovery and saved US Version 1

November 10, 2026. Owner authorized offline tests for both disconnect cases and
recovery of the current US checkpoint without new generation. Implemented locally;
owner end-to-end retest pending. No Git publication.

- Execution ownership now uses a per-run OS file lock, independent of browser
  session state. A reopening browser attaches read-only to a still-active worker;
  it cannot duplicate execution or archive that worker. Check progress reloads
  its latest persisted checkpoint.
- If execution ended, reopening validates the hash-bound saved receipts. A complete
  package/review returns to human review. An incomplete or unsafe-to-resume run
  becomes interrupted, retains its artifacts, releases its execution lock and can
  be downloaded/archived before starting fresh. No paid action is replayed.
- Worker exit/disconnect persists the latest state. Start controls explain the
  existing run and offer navigation. Interrupted draft-only views do not assume a
  review exists. Archive retains protected artifacts and accounting.

### Actual verification

428 harness tests PASS, including six focused disconnect/recovery cases. 105 UI
regressions PASS; seven focused live-UI tests then PASS including one additional
interrupted-draft test: 106 unique UI tests / 534 unique tests total. Network is
blocked in the recovery tests. Both active-worker and ended-worker paths are
covered; completed, incomplete, abandoned-refinement and unknown-accounting
checkpoints are included. Archive download ZIP and preserved originals checked.

Initial UI regressions exposed two outdated assumptions: explicit-only resume and
an unisolated Home test seeing the real saved pointer. Updated tests to expect
automatic attachment and isolate Home rendering. During that network-blocked
AppTest, the authorized real checkpoint was recovered; the subsequent explicit
recovery check confirmed the same result with zero network calls.

US run c9d4db36-d900-4057-948c-ec9573619a77 is now awaiting_human_review, Version 1,
with its complete saved review and all five formats. Package and review exactly
match original state-10. No new Writer, Reviewer, research, approval or revision;
revision attempts remain zero. The interrupted scheduled automatic refinement was
not replayed. Historical state/capture files remain unchanged; recovery appends new
receipts and updates only the active descriptor/current pointer.

All 954 baseline protected files checked: only those two expected pointer/descriptor
files changed. Sources, prompts, configs, credentials, historical receipts, archives,
budget ledgers and MEMORY unchanged. Budget remains USD0.7997323 available
(display USD0.80), including retained uncertain reservations; no refund/reset and
zero new inference cost. Whitespace check PASS.

Actual saved-run Streamlit AppTest: Current run automatically opens, Version 1
and complete review render, Review package / Archive controls available, zero
exceptions and zero network calls. Local app started on 127.0.0.1:8520; health HTTP
200. Native browser automation was unavailable (no enabled browser surfaces), so
no native visual screenshot or real browser-disconnect end-to-end pass is claimed.
Owner retest: reopen app → Current run → Review/Package; test disconnect/reopen or
archive and start fresh as desired. Reopening alone does not generate content.
