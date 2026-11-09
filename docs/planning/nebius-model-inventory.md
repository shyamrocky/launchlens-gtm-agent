# Nebius model inventory — LaunchLens

Latest qualification — 2026-11-07: [Qwen 235B / Hermes review](nebius-writer-candidate-qualification.md).
Qwen 235B serverless retirement is November 9; do not adopt it for this MVP.
Hermes pricing is verified, but reasoning/output accounting and token bounds remain
unqualified. No inference, profile changes or new spending authorization. Earlier
shortlist and unknown-pricing descriptions below are historical inventory findings.

Current routing update —2026-11-07: owner requested removing direct-provider paths.
Executable configuration is now Nebius-only, containing the existing Qwen baseline.
Direct GPT/Sonnet approval is inactive and does not transfer to these inventory
candidates. [Current removal record](nebius-writer-route-review.md). The catalog
snapshot below is preserved; inventory candidates remain unregistered/untested.

Date: **2026-11-07, America/Los_Angeles**. Read-only inventory and proposed screening shortlist.
**31 unique catalog entries; no new inference, model adoption or spending authorization.**

## What this inventory establishes

This is the set returned by one authenticated `GET https://api.tokenfactory.nebius.com/v1/models`
for the existing LaunchLens Nebius credential earlier in this session: HTTP200,
31records,2,911response bytes,0.582seconds. This document reuses that same-day
capture; no second catalog request or generation call was needed. It is a snapshot
of this account-visible listing, not a guarantee covering every Nebius account,
region or dedicated deployment. Catalog visibility does not prove inference
entitlement, available quota, endpoint compatibility or suitability for GTM writing.

The response supplies only `id`, `object`, `created`, `owned_by`. It does **not**
supply input/output prices, context/output limits, tokenizer identity, reasoning
controls, tool-call/JSON guarantees or generation quality. Those remain unverified
unless a separate source/experiment is explicitly cited below. `created` is catalog
metadata, not a verified model release date or immutable weights/version pin.
Every returned `owned_by` is `system`; namespace grouping below is taken from the
ID prefix and is not inferred from that ownership field.

## Suggested small Writer shortlist — proposal, not ranking

| Candidate | Why consider it | What remains before a test |
|---|---|---|
|`Qwen/Qwen3-30B-A3B-Instruct-2507`|Keep the preserved baseline; no rerun needed simply to establish comparison history|The latest projected-context Writer still emitted empty citation entries; generation acceptance remains open|
|`Qwen/Qwen3-235B-A22B-Instruct-2507`|Investigate first: same family/release suffix and publisher-confirmed non-thinking instruct behavior reduce an obvious comparison difference|Current Nebius price/access, model-specific token budget, supported request settings/response shape, bounded adapter/config approval and new paid-test authorization|
|`openai/gpt-oss-120b`|Optional different-family candidate on the existing provider; distinct from proprietary GPT-5.4|Current Nebius price/access, reasoning controls/output accounting and response formatting; do not assume reasoning can be disabled|

Qwen describes the 235B Instruct release as non-thinking-only; this is a publisher
claim about the model, not a live Nebius compatibility or quality result.
[Qwen publisher model card](https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507).
GPT-OSS is a reasoning-oriented open-weight model; the publisher documents low,
medium and high effort. Its provider behavior must be qualified independently.
[OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-oss-120b),
[publisher model card](https://huggingface.co/openai/gpt-oss-120b).

Neither alternative is assumed to fix citations or grounding. Keep the same prompt,
projected evidence and original-authority validation in any later approved comparison,
with unavoidable setting differences disclosed. Contract compliance and prose
grounding/brand voice remain separate assessments. No need to benchmark all31.

## Complete account-visible inventory

Every row below is **catalog-listed**. All newly proposed Writer candidates remain
**inference/quality untested** in LaunchLens. Notes marked name-labelled are triage
hints only; they are not verified endpoint capabilities.

| ID namespace | Exact returned model ID | Writer-screening note |
|---|---|---|
| `MiniMaxAI` | `MiniMaxAI/MiniMax-M3` | Untriaged; no Writer result or capability claim established |
| `MiniMaxAI` | `MiniMaxAI/MiniMax-M3.1-Flash` | Untriaged; no Writer result or capability claim established |
| `NousResearch` | `NousResearch/Hermes-4-405B` | Untriaged; no Writer result or capability claim established |
| `Qwen` | `Qwen/Qwen3-235B-A22B-Instruct-2507` | First candidate to investigate; publisher-confirmed non-thinking instruct model; Writer untested |
| `Qwen` | `Qwen/Qwen3-30B-A3B-Instruct-2507` | Current baseline; existing research/Writer observations, not an accepted fresh draft |
| `Qwen` | `Qwen/Qwen3-Embedding-8B` | Embedding model per publisher; exclude from Writer selection |
| `Qwen` | `Qwen/Qwen3.5-397B-A17B` | Untriaged; no Writer result or capability claim established |
| `Qwen` | `Qwen/Qwen3.8-27B` | Untriaged; no Writer result or capability claim established |
| `deepseek-ai` | `deepseek-ai/DeepSeek-V4-Flash-0731` | Untriaged; no Writer result or capability claim established |
| `deepseek-ai` | `deepseek-ai/DeepSeek-V4-Pro` | Untriaged; no Writer result or capability claim established |
| `deepseek-ai` | `deepseek-ai/DeepSeek-V4-Pro-0813` | Untriaged; no Writer result or capability claim established |
| `deepseek-ai` | `deepseek-ai/DeepSeek-V4.1-Flash` | Untriaged; no Writer result or capability claim established |
| `deepseek-ai` | `deepseek-ai/DeepSeek-V4.1-Flash-1017` | Untriaged; no Writer result or capability claim established |
| `google` | `google/gemma-3-27b-it` | Untriaged; no Writer result or capability claim established |
| `meta-models` | `meta-models/muse-spark-open` | Untriaged; no Writer result or capability claim established |
| `moonshotai` | `moonshotai/Kimi-K2.6` | Untriaged; no Writer result or capability claim established |
| `moonshotai` | `moonshotai/Kimi-K2.7-Code` | Code-labelled name; not prioritized for the first text-marketing test |
| `moonshotai` | `moonshotai/Kimi-K3` | Untriaged; no Writer result or capability claim established |
| `moonshotai` | `moonshotai/Kimi-K3.1-Pro` | Untriaged; no Writer result or capability claim established |
| `nvidia` | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Untriaged; no Writer result or capability claim established |
| `nvidia` | `nvidia/Nemotron-3-Ultra-550b-a55b` | Untriaged; no Writer result or capability claim established |
| `nvidia` | `nvidia/Nemotron-3.5-Super-VL` | Vision-labelled name; role inferred from name only; not prioritized |
| `nvidia` | `nvidia/Nemotron-3_5-Lightning` | Untriaged; no Writer result or capability claim established |
| `nvidia` | `nvidia/nemotron-3-super-120b-a12b` | Untriaged; no Writer result or capability claim established |
| `openai` | `openai/gpt-oss-120b` | Different-family candidate; reasoning behavior/settings require qualification; Writer untested |
| `openbmb` | `openbmb/MiniCPM-V-4_5` | Vision-labelled name; role inferred from name only; not prioritized |
| `reflection` | `reflection/beam` | Untriaged; no Writer result or capability claim established |
| `zai-org` | `zai-org/GLM-5.1` | Untriaged; no Writer result or capability claim established |
| `zai-org` | `zai-org/GLM-5.2` | Untriaged; no Writer result or capability claim established |
| `zai-org` | `zai-org/GLM-5.3` | Untriaged; no Writer result or capability claim established |
| `zai-org` | `zai-org/GLM-5.3-Flash` | Untriaged; no Writer result or capability claim established |

The embedding exclusion is supported by the publisher’s embedding/feature-extraction
documentation, rather than the name alone:
[Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B).
It does not replace LaunchLens’s already accepted E5 embeddings.

## Namespace counts

| Namespace | Count |
|---|---:|
|`MiniMaxAI`|2|
|`NousResearch`|1|
|`Qwen`|5|
|`deepseek-ai`|5|
|`google`|1|
|`meta-models`|1|
|`moonshotai`|4|
|`nvidia`|5|
|`openai`|1|
|`openbmb`|1|
|`reflection`|1|
|`zai-org`|4|
|**Total**|**31**|

No `claude` or `llama` model ID appears in this returned snapshot. Neither
`gpt-5.4-2026-03-05` nor `claude-sonnet-4-6` is present. GPT-OSS is present but
cannot be silently substituted for GPT-5.4. The namespace `meta-models` alone
does not establish that a model is Llama.

## Pricing and selection boundary

**Current Nebius token prices remain unresolved in this inventory.** The model-list
API has no pricing fields. The public pricing URL redirected to a page with no
readable price data; historical third-party rates were not used as current prices.
[Nebius pricing](https://nebius.com/token-factory/prices). Check the authorized
console’s current selected-model rates or another attributable current Nebius
price record before preparing spending reservations. Catalog discovery does not
consume or authorize a generation budget.

[Nebius inference overview](https://docs.tokenfactory.nebius.com/ai-models-inference/overview)
distinguishes text, embedding and vision model types. General API compatibility
is not proof that every listed model accepts the same optional settings.

The inventory itself did not change the operational comparison registry. The later
owner-directed cleanup now makes `data/templates/gtm/writer_models.json` Nebius-only.
This inventory remains informational documentation, not executable routing configuration. Existing provider adapters are pinned to reviewed exact models;
new Nebius candidates need a separately approved small profile/adapter change.
Do not edit their IDs to bypass that boundary. Normal Qwen drafting is unchanged.

The direct GPT/Sonnet comparison is **inactive following the owner’s provider
clarification**, rather than waiting for credentials. Its earlier paid authorization
and0.40USD ceiling do not transfer to any Nebius model. A replacement profile/test
requires new explicit owner approval. See
[comparison status and controls](m2.3b-writer-comparison-review.md).

## Provenance, preservation and verification

Protected optional source capture (directory0700/files0600, ignored):
`data/generated/m23b-provider-preflight-v1/nebius-models-response.json` and
`nebius-access-check.json`. No authorization header or credential retained.

Full response SHA256:
`a630a8bca4f0b8dedab2e04fe40bc53d24e808040b6d7924c56c8f273c3f93fe`.

Sanitized check receipt SHA256:
`49029621824b46f424c4d0ea0764dc1b3ac89cf7fe6d982cb964c62c738ef997`.

Verification:31source records,31unique IDs,31inventory rows; exact set equality
and deterministic namespace counts checked against the preserved response. No
model requests, downloads, new packages or runtime changes. Documentation/link/
credential-exclusion/Git-preservation checks are appropriate; no application tests
were rerun for this documentation-only inventory. Earlier test results remain
historical. No Git staging/commit/push or MEMORY append.

The maintained inventory lives here in canonical docs and is understandable without
workspace or the private raw capture. The capture is optional audit evidence, not
an application/build/test/deployment dependency. Refresh by making a newly authorized
read-only catalog query and recording date, exact IDs and source checksum; preserve
old captures rather than overwrite them.
