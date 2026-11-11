# Compact shared Streamlit header — November 11, 2026

**Publication checkpoint — November 11, 2026:** owner approved Git sync after the
production restart and successful local health check. Latest display is the short,
muted `Budget left: $X.XX` beside Mode. Fresh isolated verification before sync:
**122 offline UI tests PASS**, with sockets blocked and private runtime excluded.
Widget/state/budget invariants, exact publication scope, credentials/ignore rules,
syntax, whitespace and screenshot links passed review. Earlier screenshots show
the preceding long caption, as explained in the follow-up below. No new restart,
run execution, model/source/LangSmith calls, budget write or MEMORY append is
initiated by publication. No additional restart is needed. Earlier pending/no-sync
statements retain their original dated scope.

Owner authorized a small layout/CSS exception to the frozen demo build, with diagnosis
and a proposal shown before editing. No controller, harness, gate, Writer/Reviewer,
LangSmith, budget, prompt, model, configuration or protected run changes.

## Diagnosis and delivered layout

`inventory_ui.main()` previously split brand/navigation from a home-only page title
and mode selector. `ui-mode` is both the existing widget key and session-state value;
its existing preservation assignment and `_data_mode` lifecycle remain unchanged.
The same selectbox now appears in the shared three-column header on both views,
with unchanged options, formatter and `refresh_blocked()` disabled guard. Home and
Current run buttons retain keys `home`/`current` and identical handlers.

The existing `budget_caption()` is invoked once under the shared header. Its reader,
rounding, label and simulation suppression are unchanged. Large duplicate home/empty
run titles are removed; run/review market context uses compact captions. Existing CSS
reduces top padding and caption margins and lets the header wrap on narrow screens.

Runtime changes: `inventory_ui.py`, `agent_run_ui.py`, `inventory_ui.css` only.
Five existing UI test files adjust presentation expectations; five new regressions
in `tools/ui/tests/test_compact_header.py` cover the actual widgets and continuation.
No extra state, callbacks, keys, session fields or execution pipeline were added.

## Verification

- **122 offline UI tests PASS**, using the existing UI environment, `PYTHONPATH=src`
  and an isolated canonical copy. The initial invocation omitted PYTHONPATH and had
  an import error; the corrected full suite passes. No live inference or spending.
- AST comparisons prove every widget call (keys/options/callbacks/disabled guards)
  and all session-state assignments/mutations are identical. Budget/source-refresh
  helpers are unchanged; other canonical runtime/configuration/data bytes preserved.
- Both mode values survive repeated home/current navigation and reruns. During a
  UK clarification pause, mode switching remains disabled by the existing guard.
  The same run object, ID, state and captured calls survive navigation; the actual
  Continue form resumes it to reviewed Version 1 in offline simulation.
- A single live-mode caption tracks updated helper values on both views (tested
  USD0.9775988 -> USD0.98 and USD0.734 -> USD0.73). Simulation still suppresses it.
- Separate local before/candidate preview servers start without application warnings
  or errors. Test-runner bare-mode ScriptRunContext warnings are separate from app
  startup. Browser checks use fixture reads and the read-only budget display snapshot;
  no production run or ledger was copied or executed.
- Safari visual verification at approximately1340px wide and at200% zoom (roughly
 670 CSS px): readable wrapping, no clipping/overlap. Both tab screenshots below use
  the same laptop-width window. Browser UK pause -> home -> current -> Continue also
  reached Package ready for your review / Version1 with the selected mode retained.

The live budget display snapshot was USD0.98; it is not a promise of the balance at
recording time. The production app remains active; no original run/budget write,
restart, MEMORY append or Git sync was initiated. Source installation requires an
owner-ready restart because file watching is disabled.

## Before / after

Screenshots are native captures of isolated UI copies with fixture data, not new live
quality results. Original images are unedited.

| View | Before | After |
|---|---|---|
| GTM launches | [Before](../images/header-2026-11-11/before-home.jpg) | [After](../images/header-2026-11-11/after-home.jpg) |
| Current run (empty) | [Before](../images/header-2026-11-11/before-current.jpg) | [After](../images/header-2026-11-11/after-current.jpg) |

[Narrow header](../images/header-2026-11-11/narrow.jpg) ·
[Paused UK run after navigation](../images/header-2026-11-11/paused-run.jpg)

## Owner follow-up — short budget caption beside Mode

The owner requested the display-only label `Budget left: $X.XX` next to the Mode
selector. The existing right-hand header column now contains adjacent Mode/caption
columns; the caption uses small muted text. The same budget reader, remaining_usd
value, Decimal two-place formatting and simulation suppression are retained. No cap,
ledger, enforcement, widget key, callback or session-state change.

Five focused header regressions pass again, including exact caption values on both
views, mode persistence and UK pause/navigation/resume. Earlier screenshots above
show the preceding long-caption layout; this follow-up supersedes that caption's
wording and placement. No production restart, live call, budget write or Git sync.
