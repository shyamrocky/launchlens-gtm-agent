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
