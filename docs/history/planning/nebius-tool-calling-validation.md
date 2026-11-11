# Nebius tool-calling smoke test

Date: 2026-11-05, America/Los_Angeles. **Technical PASS; owner review pending.**
Owner approved a small model -> harmless local tool -> model test, capped at two
inference requests, stopping on failure. No application agent or integration built.

## Readable result

Model: `Qwen/Qwen3-30B-A3B-Instruct-2507`, present in refreshed authenticated catalog
(31 entries). Selected for this compatibility test, not adopted as a final
application model. Publisher documents tool use/non-thinking mode; Nebius documents
the tool-capable chat API. This test uses direct standard-library HTTP, not a new
framework or SDK.
[Publisher model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507),
[Nebius chat API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion).

| Step | Observed result |
|---|---|
| First model request | HTTP200; auto-selected get_test_launch_status; finish_reason=tool_calls |
| Argument validation | Exact approved fixture: product TEST-LAUNCH, market US, evaluation date 2026-12-14; no extra arguments |
| Local tool | Returned FIXTURE_ONLY_READY plus a newly generated verification code, absent from the initial prompt |
| Second model request | HTTP200; consumed the linked tool result; finish_reason=stop; no further tool requested |
| Final answer | Exact JSON equality with the returned fixture status/code |

The observed verification code was `8b0eff985d577f9d` in both the
local tool result and final answer. This is an ordinary test marker, not a secret
or any actual approval. All status/date/product values here are isolated test
fixtures, not records from the accepted launch datasets.

## Limits and measured usage

Execution: 2026-11-06 05:47:27-05:47:29 UTC / 2026-11-05 21:47:27-21:47:29 PST.
One read-only model-catalog GET preceded the two inference POSTs. Endpoint:
`https://api.tokenfactory.nebius.com/v1/chat/completions`.

| Request | Input tokens | Output tokens | Total | HTTP elapsed seconds |
|---|---:|---:|---:|---:|
| Tool selection | 323 | 48 | 371 | 1.121 |
| Tool-result response | 412 | 30 | 442 | 0.921 |
| Total | 735 | 78 | 813 | 2.042 |

Both responses identified the selected model. Both requests used tool_choice=auto,
temperature=0, store=false, non-streaming and max_tokens=256. The function was not
forced through a named tool choice. No automatic retries, fallback models or third
inference request. Actual dollar charges/credit balance were not checked.

Offline validation accepted a valid fixture call and rejected seven malformed or
out-of-scope calls (tool name, product, market, date, extra argument, invalid JSON,
missing call ID). Independent receipt checks verified both model IDs, HTTP codes,
finish reasons, two-request count and exact tool-result consumption. No application
suite rerun: the change is an isolated smoke-test tool, not the application.

## Canonical setup and protected artifacts

Maintained stdlib-only tool: `tools/check_nebius_tool_calling.py`.

```sh
.venv/bin/python tools/check_nebius_tool_calling.py
# Offline preflight. --execute requires a separately authorized hosted run.
```

Use existing Python3.12/.venv provisioning. Hosted execution reads only the local
NEBIUS_API_KEY from ignored private .env. It refuses an existing receipt, counts
attempts before sending, strictly dispatches only the local fixture, and stops on
unexpected responses or truncation. No model-provided code is executed. HTTPS
verification enabled; proxies/cookies/redirects disabled; internal reasoning is not
printed or retained. No project source documents or real launch records transmitted.

Receipt: ignored `data/generated/nebius-tool-smoke/receipt.json`, SHA-256
`04d8a26d1431d3dbbdccb40a6b38e7d98028125b7842a07cea729ec7abd33f02`.
Executed script SHA-256: `877e41bd32d0524d5ef1e5b25da88c79df955c7bab79f1838731319c8fb18841`.
This canonical summary is sufficient without temporary files or workspace.

No .env/model configuration, accepted datasets, original preparation artifacts,
locks, dependencies or existing application code changed. No Pinecone, Notion,
Drive, GTM generation, LangGraph agent, commit or push. MEMORY unchanged.

## Completion boundary

One hosted tool-call cycle is verified. This does not establish reliable autonomous
planning, multi-tool selection, LangGraph/SDK compatibility, GTM quality, retrieval
accuracy or Reviewer behavior. No model benchmark or final model decision is implied.
Stop for owner review. Next proposed chunk: GTM-focused retrieval validation under
separate authorization. Existing Pinecone sample/milestone acceptance is unchanged.
