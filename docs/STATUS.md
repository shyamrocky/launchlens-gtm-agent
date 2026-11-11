# LaunchLens — current status

As of November 11, 2026. Live results below are owner-reported from November 10–11; documentation cleanup does not rerun the application.

## What works today

- **US / UK / India:** end-to-end Proceed / Clarify / Hold paths, including human clarification and approval/download for drafted packages.
- **Agent self-fix:** the independent review can trigger a bounded automatic revision and a fresh review.
- **Targeted human revisions:** requested fields are revised; unchanged requests remain unresolved rather than being reported as fixes.
- **Exact suggestions in code:** choices are collected first, then applied on Create Version; suggestion-only changes need no Writer call and still receive validation and fresh review.
- **Citation repair:** a single automatic, reference-only repair preserves candidate text, sends all detected citation gaps, and revalidates the whole package before fresh review. Covered offline; the reported UK retest drafted first try, so that run did not exercise repair.
- **LangSmith tracing:** roots and child spans are visible in the demo project; controller actions, tools, human pauses/resumes and LLM usage are instrumented. Latest timing/grouping polish has offline coverage; live confirmation is pending.
- **Offline baseline:**730 tests passed before the submission cleanup (499 harness,117 UI,114 root). These are engineering regressions, not a content-quality evaluation.

## Known limitations

- First drafts can omit citations; one automatic repair is available, followed by an explicit re-run if needed.
- Rewritten lines can lose citations and produce Factual support cards; inspect the evidence before choosing Keep wording, which does not restore citations.
- Reviewer findings vary between versions; the code phrase scan backs up configured wording checks, not factual entailment.
- Reloading mid-run does not fully resume reliably; stay in the same browser session while recording.
- Some status labels remain stale, such as Waiting on you after an answer.
- Reported live root latency covers only the pre-pause segment; an offline-tested fix is merged, with live confirmation still pending.
- Archived approved packages can show Awaiting review; inspect the package's approval rather than relying on that label.
- Drafts can be short and ads long; length checks are advisory.

## Next steps

- Generalize the gate from market to any launch scope.
- Move runs to a background worker so browser reloads do not own execution.
- Add evaluations in LangSmith.

These are proposed next steps, not authorization or completed work.

Historical checkpoints and per-round fix logs are preserved in [history](history/README.md).

[Demo walkthrough](DEMO.md) · [Tracing guide](langsmith-tracing.md) · [Project README](../README.md)
