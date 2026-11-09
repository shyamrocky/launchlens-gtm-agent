# Launch inventory homepage

Decision ID: UI-D001. Date: 2026-11-08 (America/Los_Angeles).
Authority: owner reviewed the supplied inventory screenshot and explicitly asked
to implement this homepage. Status: design direction approved; interactive preview
implemented locally and awaiting owner inspection. Live Streamlit integration is
not implemented or authorized by this preview checkpoint.

## Decision and rationale

Start with a launch inventory: a PM/PMM should understand upcoming product/market
work before opening a brief or reviewing generated content. This supersedes the
earlier action-first homepage concept. Alternatives considered: start directly in
the draft workspace, or show only a supported-case selector without launch dates.
Both obscure the upcoming launch portfolio.

One product card shows product name, company, a source-supported short description,
markets, planned launch window and planned deliverables. Expand/collapse reveals
market rows with planned dates and the campaign objective. Every market, including
restricted ones, can open its prefilled brief. Opening a brief must not dispatch
generation. Use Current workspace rather than a Runs/history navigation item.

The current preview has one Cherry Float case, flavor discovery, US 2026-12-14,
UK 2027-01-04 and India 2027-01-18. Planned deliverables are campaign brief,
LinkedIn, email, blog and ads; current preview scope remains LinkedIn only.
These fictional plans are not actual Coca-Cola launch schedules.

## Authority and implementation boundary

- Product description derives from approved Product Brief PROD-002/PROD-003:
  cherry with vanilla notes and classic soda-float inspiration, not ingredients.
- Future product/task discovery uses the existing harness registry. Dates come
  from the Launch Calendar, not duplicated authoritative registry scheduling.
- Readiness comes from the separate Readiness Tracker and deterministic launch
  checks. A planned date or inventory selection cannot grant drafting permission.
- Preview labels are explicitly scenario snapshots at each market's launch date:
  Drafting permitted / Availability confirmation missing / Marketing approval
  pending. These are not fresh Notion checks or publishing approval. The prefilled
  brief says readiness has not been checked and requires explicit preparation.
- Retain the independent educational disclaimer. Publishing remains disabled.
- The temporary interactive draft is workspace/ui-concepts/launchlens-ui-concept.html.
  It contains local fixtures only, no network calls or backend integration. This
  document owns the durable design direction; workspace cannot override it.
  No application, build or required check depends on the temporary draft. Promote
  the accepted interface into canonical application files in a later authorized
  integration increment rather than making workspace a runtime dependency.

## Verification of this preview

Local Node syntax/fixture checks PASS: product/company/description/window/package,
source disclosure, collapse/expand, supported market/date prefill, rejection of an
unknown market, and zero dispatch on market selection. Existing concept checks
also PASS for US/UK/India, invalid dates, single revision, version-specific review
and export, current workspace, reset/regenerate and both layout variants. These
use a minimal DOM simulation, not a real backend or browser automation suite.

Chrome desktop inspection confirmed the rendered inventory, expanded source
details and UK brief prefilled with 2027-01-04 and readiness not checked. Responsive
CSS is included; no device/browser matrix is claimed. Preview server refreshed
at http://127.0.0.1:8765/ for owner inspection. No live model/source calls, source
dataset edits, dependencies, default-model changes, MEMORY append or Git publication.
Reviewer and full Streamlit delivery remain on the existing LinkedIn-first roadmap.


## Owner-directed presentation refinement — 2026-11-08

Owner approved subtle dark-background contrast, a larger LaunchLens product name,
GTM Launches as the page title, and product/brand hierarchy. Product name remains
Coca-Cola Cherry Float without a redundant Product prefix; the secondary line now
reads Brand: Coca-Cola. The homepage uses a charcoal-blue canvas, lighter neutral
card, subtle border and restrained blue links/brand accent. Status colors retain
readiness meaning. Light appearance remains supported through paired color tokens.
This is a cosmetic preview refinement, not an integration or milestone expansion.

Fresh checks: existing Node concept interactions PASS after updating expected text;
primary, secondary and accent foregrounds against page/card backgrounds exceed
4.5:1 in both palette definitions (minimum 5.20:1 light, 7.72:1 dark). These are
palette calculations, not a full accessibility audit. Chrome desktop dark preview
visually confirmed enlarged LaunchLens, GTM Launches, Brand: Coca-Cola and card
separation. Existing fixtures, dates and interactions remain unchanged. No live
calls, runtime/source changes, MEMORY append or Git publication. Preview remains
at http://127.0.0.1:8765/ for owner review; live Streamlit integration remains pending.


## Owner-approved layout refinement — 2026-11-08

After reviewing the rendered homepage, owner authorized a final density/alignment
pass: tighten vertical spacing above the title and inside the card; align header,
preview notice, page heading and inventory to the same centered content width;
label the disclosure View 3 market launches / Hide 3 market launches; show market
rows expanded initially for the one-product demo. Palette, fonts, source roles,
dates, readiness restrictions and draft/review permissions remain unchanged.

An older saved collapsed preference migrates to expanded once without discarding
its existing task/draft/review state. Subsequent explicit collapse choices persist.
Fresh Node concept checks PASS, including the two saved-preference migration cases
and existing market/date/revision/export/reset scenarios. These are offline minimal-
DOM checks. Chrome dark desktop inspection confirmed shared alignment, tighter
spacing, three visible market rows and their unchanged scenario-snapshot labels.
Preview server refreshed at127.0.0.1:8765; no runtime/backend/source/API/MEMORY/Git
changes. Live integration and main implementation acceptance remain separate.


Typography adjustment (owner-directed, 2026-11-08): increase Brand from13to14px,
product description15to16px, metadata labels12to13px and values13to14px; inline
Source link12to13px for consistency. Product heading remains25px (23px mobile).
Chrome desktop inspection confirmed readable layout without overlap. JavaScript
is byte-identical to the preceding preview; no interaction-test rerun required or
claimed for this CSS-only change. No backend/source/policy changes. Preview server
refreshed on127.0.0.1:8765 for review; all prior implementation boundaries retained.

Follow-up owner request, 2026-11-08: increase the same card fonts another1px:
Brand15px, description17px, metadata labels14px/values15px, Source14px. Heading,
palette and behavior unchanged. Desktop Chrome verified no overlap; JavaScript
unchanged. Preview refreshed at127.0.0.1:8765; no tests/live calls/Git publication.


## Product-specific source documents sidebar — 2026-11-08

Owner explicitly agreed this remains a mockup and approved a vertical right-hand
Source documents card. This supersedes the earlier top-navigation Sources link
and inline description Source link; both are removed. Product-specific context is
shown on the source card. Google Drive lists Product Brief PDF (public facts) and
Synthetic PRD PDF (fictional intent). Notion lists PMM / GTM Brief (direction),
Launch Calendar (planned dates) and Readiness Tracker (approvals/blockers).

Each filename/title expands local explanatory details; it does not open or query
an external service. Preserve claim-level citations in draft review. No connected,
synced or fresh verification badges are fabricated. The desktop content width
accommodates a wider launch column and narrower270px source card; below860px the
source card stacks beneath the launch card. Card typography/palette remain as
approved. Visible scope and footer explicitly identify the preview and fictional
scenario. Readiness and generation permissions remain separate from this list.

Fresh checks: Node syntax/concept fixtures PASS for grouped sidebar, absent duplicate
links, existing market/date/draft/revision/export/reset paths and zero network code.
Generated homepage HTML nesting PASS. Desktop Chrome confirmed right placement,
all five titles grouped under the correct app, and local Product Brief details
with PROD-002/PROD-003 and material caveats. Responsive CSS included; no mobile
browser matrix claimed. No datasets, live integrations, runtime agents, credentials,
dependencies, MEMORY or Git publication changed. This is not Streamlit integration.
Preview server refreshed at127.0.0.1:8765 for owner review.


Owner simplification, 2026-11-08: remove View/Hide3 market launches entirely;
market rows are always visible on the homepage. This supersedes prior collapse/
preference instructions. Removed toggle, handler and collapsed-state fields;
legacy saved collapse values cannot hide the section. Source sidebar and market
row actions remain unchanged. Fresh concept checks PASS for visible rows, absent
toggle and existing brief/draft/revision/reset paths; Chrome confirmed all three
rows visible with no toggle. No live integrations, datasets, MEMORY or Git changes.


Real inventory implementation authorized and delivered locally, 2026-11-08:
[UI-D002](ui-inventory-implementation.md) now owns runnable setup/data/verification.
The earlier workspace HTML is a superseded design reference for the inventory,
not the maintained application. Canonical Streamlit implementation uses real registry
and Notion data; main agent integration and owner acceptance remain separate.
