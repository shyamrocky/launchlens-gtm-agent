# Nebius Writer candidates — qualification without inference

Date: **2026-11-07 (America/Los_Angeles)**. Owner authorized qualification only.
**Review complete with blockers. No candidate is execution-ready or adopted.**

## Recommendation in plain English

Do not add Qwen 235B to this MVP: its serverless retirement falls before our
submission deadline. Keep Hermes 405B as the candidate to qualify further; price
and public availability are established, but its hosted reasoning behavior and
request token bound are not. The preserved Qwen 30B result remains the comparison
baseline. No replacement candidate, dedicated endpoint or additional test is selected.

## Verified candidate information

| Item | Qwen 235B Instruct | Hermes 4 405B |
|---|---|---|
| Exact Nebius ID | `Qwen/Qwen3-235B-A22B-Instruct-2507` | `NousResearch/Hermes-4-405B` |
| Public catalog | Active parent; flavor explicitly deprecated | Active parent; no deprecated flag on flavor |
| Published input / output USD per million tokens | $0.20 / $0.60 | $1.00 / $3.00 |
| Published context limit | 262,144 tokens | 131,072 tokens |
| Serving region / quantization | Finland, eu-north1 / FP8 | Finland, eu-north1 / FP8 |
| Lifecycle decision | Exclude from new MVP adoption | Conditional candidate; no removal listed in the checked November notice |

Source: Nebius's [authoritative public model JSON](https://tokenfactory.nebius.com/api/public/models_info),
with its [readable catalog](https://tokenfactory.nebius.com/model-catalog.md).
Both exact IDs also occur in our preserved same-day authenticated account listing;
no new authenticated request was made. A listed model does not prove quota,
billing eligibility, successful inference or writing quality. The two sources have
different scope: the earlier account listing omits deprecation/pricing information.

**Lifecycle blocker:** Nebius's [November notice](https://docs.tokenfactory.nebius.com/november-2026-deprecation-notice.md)
says Qwen 235B serverless requests stop working on **November 9, 2026**. This is
before the handout's November 11 deadline. Its suggested replacement is our existing
Qwen 30B model, not a newly selected alternative. The notice does not list Hermes
or our current Qwen 30B baseline. Absence from this notice is not a long-term
availability guarantee. Do not introduce dedicated infrastructure to retain Qwen 235B.

## API compatibility and unresolved reasoning behavior

The [Nebius Chat Completions reference](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion)
and [OpenAPI schema](https://api.tokenfactory.nebius.com/openapi.json) document the
same API family as the current transport. Our proposed unchanged envelope is:
`temperature=0`, `max_tokens=2048`, `stream=false`, `store=false`, one system and
one user message. No response_format/structured-output constraint, tools, retries,
repair or fallback would be added. These are documented general API fields,
**not model-specific execution results**. We did not POST either request.

- **Qwen:** its [publisher card](https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507)
  identifies this exact Instruct model as non-thinking-only. It does not need an
  enable_thinking flag. This favorable compatibility fact does not remove retirement.
- **Hermes:** its [publisher card](https://huggingface.co/NousResearch/Hermes-4-405B)
  identifies a Llama 3.1-derived hybrid model and describes creative-writing/schema
  training. These are screening reasons, not proof it will obey our citation contract.
  Publisher examples activate reasoning with a template flag or a different system
  prompt. They do **not** establish the default/control mapping on Nebius.
- Nebius's general schema includes reasoning_effort and arbitrary extra_body, but
  does not establish that reasoning_effort=none or a particular template flag disables
  Hermes reasoning. Do not invent that mapping or change our prompt to force it.
  The inspected pinned Hermes tokenizer config has no chat_template entry; this
  does not establish what the hosted provider uses.
- The general API defines max_completion_tokens as including visible and reasoning
  tokens. Our existing request uses max_tokens. Equivalence of these limits for
  hosted Hermes, and the treatment of any hidden reasoning for billing, remain
  unqualified. A new parameter would require an explicit reviewed settings change.
- Existing comparison admission allows only absent/zero reported reasoning tokens.
  An absent counter is not proof reasoning was disabled. Preserve raw provider
  fields and do not silently strip thinking text to make JSON pass.
- Existing timeout is 45 seconds, unchanged. Catalog throughput figures are not
  measured latency for our request. Hermes timing and completion within that
  timeout remain untested; an ambiguous timeout must not trigger an automatic retry.

No model-specific hard maximum output length was established from the catalog.
The API's omitted max_tokens default is not a verified per-model output limit.

## Token-fit and proposed spending bounds

The preserved complete projected provider-body SHA-256 remains
`fa6c1d36f4b19f7fba5e2a48977a2e5397bdbe8f699e8380def87930eb8dfc05`.
It contains 35,665 serialized bytes and **33,909 UTF-8 message-content bytes**.
The previous 7,052 provider input tokens are a Qwen 30B observation; they cannot be
reused as a Hermes token count. No tokenizer packages, weights or executable
publisher code were installed/downloaded. The existing tokenizer library is
available, but full tokenizer assets and hosted template matching were not qualified.
No input-token counting API was found in the inspected Nebius OpenAPI paths.

The current comparison profile input ceiling is 32,768. Even a one-token-per-byte
estimate for message text exceeds that ceiling before chat-wrapper overhead; it
cannot serve as a passing input bound. **A defensible candidate-specific count or
upper bound is still required.** Do not cut context, inflate the ceiling or treat
character counts as exact tokens to pass the gate.

For planning only, if qualification proves input <=32,768 and total billable
output <=2,048, using uncached published rates gives:

| Candidate | Conditional maximum token charge | Proposed per-call ceiling |
|---|---:|---:|
| Qwen 235B (not recommended) | $0.0077824 | $0.01 |
| Hermes 405B | $0.038912 | $0.05 |
| Hypothetical pair | $0.0466944 | $0.06 aggregate |

Formula: `(input_bound × input_rate + output_bound × output_rate) / 1,000,000`.
These are conditional token-charge estimates and proposed safety ceilings, not
expected bills or spending permission. They do not resolve Hermes hidden-output
accounting. Ignore cache discounts for reservation; final invoice/account terms
may differ. If only Hermes is pursued, propose $0.05 aggregate for that one request.
Previous direct GPT/Sonnet approval and its $0.40 bound remain inactive/nontransferable.

## What remains before any live experiment

1. Owner reviews the lifecycle finding and agrees whether to pursue Hermes only.
2. Qualify its hosted reasoning controls/output accounting and obtain a defensible
   token bound for the exact unchanged Writer request. Provider confirmation or
   pinned local tokenization plus documented hosted wrapping could supply evidence;
   no provider support message has been sent. If documentation remains insufficient,
   present that limitation rather than claiming complete qualification. A diagnostic
   probe would need its own explicit authorization and acknowledged settings.
3. Separately approve minimal offline candidate-profile/allowlist work. Currently
   only qwen30 is registered, so both candidates remain intentionally rejected by
   the operational registry. Do not alter the global controller/Writer model.
4. Reconfirm request identities, current prices, source permissions, account access
   and per-model/aggregate reservations, then obtain a new single-attempt live
   authorization. Preserve prompt, projected context, output contract and original-
   authority backend validation. No automatic repairs, retries or substituted model.
5. Assess citation structure separately from factual grounding, voice and writing.
   An offline check cannot establish either live compatibility or content quality.

## Verification, preservation and evidence

- Public metadata/docs only; no credential loading, authenticated API call,
  inference, Notion/Pinecone read, dependency installation or Git publication.
- Inspected exact IDs/prices/lifecycle against primary sources and independently
  recalculated the conditional Decimal cost bounds. Reused the original protected
  provider request for byte/hash inspection without sending it anywhere.
- Original application, model registry, prompts, context policy, validators,
  datasets, historical responses and Git HEAD/index remain unchanged.
- This is a documentation-only checkpoint: application tests were not rerun.
  Previous 268 offline passing tests belong to the routing-removal checkpoint,
  not new candidate compatibility tests. No milestone or model adoption accepted.
- Canonical findings are all here. Optional protected public-source captures and
  HTTP receipts are in `data/generated/m23b-nebius-candidate-qualification-v1/`.
  Nothing requires that directory or workspace for runtime/build/tests/deployment.
  Publisher tokenizer configs were pinned by revision; no model weights acquired.

Public capture identities (SHA-256; all captured HTTP 200 on 2026-11-07):

| Source | SHA-256 |
|---|---|
| Nebius public model JSON | `0f3c08ebef5a341541096adec8ac77252a6959aebf924f7fc0934f5feaecbae8` |
| Nebius readable catalog | `6d43397e88154d06e5a7560b95460bd97a1c6978f676b92a9535523679dca198` |
| Nebius OpenAPI | `94c0c01e54a54bfca2f0d3e5ac88ca7568c19f9a898e5f3d5ffbf1dbb8f187fe` |
| Nebius Chat API Markdown | `f2dbc6f9babb12a1331cb988438f04fed337e6507c47affca3462df3fac0fc2b` |
| November retirement notice | `764739c6c94fe36ff541819f238e3dee1c792833203474e5da73b23c26b59084` |
| Hermes tokenizer config, revision 88e3dce03c4a5535e2f4a2bcc08e939a2b302f82 | `beb2e35eeb32be25c3bc8c7c9ad765ebe2a1a48cfffc3e06cf6e6d5525309fca` |
| Qwen tokenizer config, revision ac9c66cc9b46af7306746a9250f23d47083d689e | `a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3` |

Stop for owner review. M2.3b generation remains open. No live comparison,
Reviewer, other format, UI, new model profile or Git operation is authorized here.
