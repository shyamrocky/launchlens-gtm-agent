# LaunchLens — recording walkthrough

Demonstrate the same controller/Writer/Reviewer flow across three launch decisions. Public product evidence and synthetic launch/readiness records have different authority. Nothing is published.

## Before recording

1. Restart the local Streamlit app: stop its terminal process with Ctrl+C, then use the [README run command](../README.md#setup). Open http://127.0.0.1:8520/ and choose **Live agent** mode.
2. Check **Demo budget left** on GTM Launches. It is shared across runs, retries and recording; restarting or archiving does not refill it. Do not assume the earlier reported balance is current.
3. Open a market's **Open brief ›** preparation screen. The model catalog auto-qualifies when its cached check expires; wait for readiness. If authorization, source access or spending qualification blocks Start agent, resolve that preflight condition before recording.
4. Keep the provisioned private launch catalog, evidence bindings and existing spending authorization available. A new checkout with credentials alone does not reproduce those private artifacts; provisioning must follow the approved setup, without copying receipts into Git.
5. Open the **launchlens-demo** project in LangSmith in the correct workspace/US region (or the configured project), and the Pinecone index **launchlens-e5-sample-v1** in another tab. Tracing must already be enabled; see the [tracing guide](langsmith-tracing.md).
6. Check whether each market already has a saved package. Use **View run** to inspect it. If a fresh recording requires archiving it, download first and deliberately use **Start fresh** → **Archive & start fresh**; existing history and budget accounting remain. Do not reset the ledger.

## US — Proceed

1. On **GTM launches**, choose the US **Open brief ›**. Point out the evidence/source status and launch readiness, then click **Start agent**.
2. In **Activity**, show the controller choosing research steps, its short reasons, evidence retrieval and the launch gate's **Proceed** decision.
3. Wait for Version 1 and the independent review. Show the five formats: campaign brief, LinkedIn, email, blog and three ad variations. A bounded agent self-fix may produce Version 2 when required; do not promise a particular version or card count.
4. In **Review**, inspect each required card. Choose **Use “…”** for an exact suggestion, **Let the Writer rephrase** for a targeted rewrite, or **Keep wording** after checking the context. A suggestion click records a choice; it does not create a version immediately.
5. At **Review choices**, finish required decisions and press **Create Version N** (the next-version action). Exact suggestions apply in code; rephrases go to the Writer with only targeted fields and guidance. Show changed/unresolved counts and the fresh review. Unchanged requests stay unresolved.
6. Open the package, inspect the current version and any remaining flags, check the human acceptance box, then click **Approve package** and **Download Markdown**. Approval is for internal use; no publication occurs.

Point out the separation: the agent chooses actions, the Writer drafts, the Reviewer assesses, the harness enforces boundaries, and the human approves.

## UK — Clarify

1. Return through **GTM launches**, open the UK brief and click **Start agent**. An approved US package permits moving to another market; an active unapproved run must be resolved first.
2. Show the **Clarify** decision and the human question. Choose **Draft without availability wording**, then **Continue**.
3. In **Activity**, point out the human answer and required evidence retrieval for **PROD-002** and **PROD-003**, followed by drafting and independent review. The answer permits drafting without availability wording; it does not prove availability.
4. Inspect the draft to confirm that availability wording is absent. Demonstrate any agent fix and a targeted human rewrite using the same review choices → **Create Version N** flow. Review outcomes and version counts vary.
5. Review the new version and any Factual support cards against the evidence; use **Keep wording** only after human inspection. Approve the current package and download it as in the US flow.

Point out the real pause and continuation in the same run, the bounded revision scope and the human approval boundary.

## India — Hold

1. Return to **GTM launches**, open the India brief and click **Start agent**.
2. Show the **Hold** decision, its blocking reason and supporting readiness evidence. Promotional drafting must stop; a held run is a successful gate outcome, with no promotional package to approve or download.
3. Show that the controller/gate/tool activity is still traceable. There should be no Writer or Reviewer drafting spans for a run held before drafting.

Point out that launch permission is enforced independently of a model's ability to produce copy.

## If a first draft fails citations

The one automatic repair returns missing references for the saved candidate without rewriting it. If **Draft needs attention** remains, use **Try again** to explicitly re-run the failed drafting stage when offered. If only **Continue run** is shown, continue that saved run first. Wait for whole-package validation and the fresh review. Retry spending still counts; do not reset the run, budget or revision ledger to hide the failure.

## Show the LangSmith trace

1. In the project, find the root named **use case · scope · run ID**. Match the scope and run ID with the app; use that ID to distinguish repeated recordings of a market. Background delivery can take a moment.
2. Expand the trace tree and select **controller_action**. Inspect its selected action and short **why** in inputs/outputs. This is the controller's stated business reason, not private reasoning.
3. In the UK trace, select **human_interrupt**, then **human_resume** and the later nodes. They should share the same root/run ID. Tracing reattachment does not fix browser reload recovery.
4. Select **Writer**, **Reviewer**, **revision Writer**, or **citation repair** when that operation occurred. Show model/provider metadata, start/end or latency, input/output/total tokens and estimated cost. Costs use configured profile rates and returned usage; they are not the protected spending ledger.
5. Expand **risky-phrase scan** and its **scan <format>** children, then **launch gate check** to show the gate result. Latest grouping/latency polish needs live confirmation; if the dashboard still shows pre-pause root latency, use completed child spans and describe the known limitation honestly.

For configuration, failure isolation, privacy and exact span names, use the unchanged [tracing guide](langsmith-tracing.md). Do not display credentials, email or protected receipts while recording.

## Show the Pinecone evidence

Open **launchlens-e5-sample-v1**, select namespace **m15b4-corpus-validation-v1**, and use the record browser/fetch view to inspect product-claim metadata for **PROD-002** and **PROD-003**. These are claim IDs; if direct record-ID lookup needs a different key, find the record whose **unit_id** matches the claim and use its full stored record ID. Show the claim text, provenance and qualifications, then connect those IDs to the UK required evidence step and package citations. Do not edit/upsert records or present an arbitrary new search as the saved run's retrieval.

[Current status and limitations](STATUS.md) · [Project README](../README.md)
