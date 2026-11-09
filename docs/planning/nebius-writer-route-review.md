# Nebius-only Writer routing — removal review

Date: 2026-11-07 (America/Los_Angeles). **OFFLINE TECHNICAL PASS; no inference.**
Owner first clarified that the direct GPT/Sonnet route must be inactive with no
approval transfer, then explicitly requested removing it from the code repository
because this build should use Nebius Token Factory. This later direction supersedes
merely waiting for direct-provider credentials. M2.3b generation remains open.

## Removed from executable code and configuration

- Direct OpenAI, Anthropic and Groq endpoint/profile branches, credential loading
  and provider-specific payload/response translations.
- GPT-5.4, Claude Sonnet and Groq Llama entries from the operational model registry.
- Their command-line selections. The previous GPT/Sonnet command now fails at
  argument validation, before source inputs, credentials or transports are touched.

Historical reports, catalog captures and generated responses remain preserved.
Their original model IDs, old example commands and verification results are audit
history, not executable configuration or current authorization. No Git history
rewrite, staging, commit or push occurred.

## What remains

The existing Qwen application/controller path is unchanged. The adjacent comparison
utility now accepts **Nebius only**, reading only NEBIUS_API_KEY and targeting the
same pinned Nebius endpoint as the accepted baseline. It reuses the same prompt,
projected context and original-authority validator. The small generic selection,
one-attempt ledger, cost reservation, raw capture and independent result reporting
remain; no replacement framework or pipeline was built.

Version2.0 [registry](../../data/templates/gtm/writer_models.json) contains only
`qwen30` → `Qwen/Qwen3-30B-A3B-Instruct-2507`, the existing baseline. Candidate
Qwen235B and GPT-OSS remain in the [informational inventory](nebius-model-inventory.md),
not the runtime registry. No replacement model was adopted, enabled or tested.
Future models require separately approved profiles and model-specific qualification.

The new registry/configuration hash and selected model IDs invalidate old run
bindings. **Earlier direct-provider approval and its0.40USD ceiling are inactive;
they do not authorize any Nebius test, including another baseline run.** Enabling a
profile remains eligibility only. Current prices in the new registry are deliberately
unresolved, so live execution also fails the spending gate. Its0.20USD safety ceiling
is a proposed configuration bound, not a new spending approval.

The current Nebius comparison output guard is
`data/generated/m23b-nebius-writer-comparison-v1`, presently absent. The earlier
multi-provider output path and all historical experiment guards remain unmodified;
no authorization file or execution directory was created.

## Verification

- **268 offline tests PASS:**97root,23preparation,148agent/adapter.
  The25 comparison tests retain existing concurrency/attempt/cost/authority/raw-
  capture checks using explicitly fake Nebius profiles and prices. Three added
  checks prove production registration is baseline-only, old authorizations cannot
  be reused, and removed CLI routes fail before inputs/keys/transport.
- **Clean canonical copy148PASS** without .env, workspace, private snapshots,
  generated artifacts, source PDFs or inherited credentials.
- Actual frozen-input offline preflight: single/qwen30/nebius, zero provider calls.
  Config SHA256:
  `78ca820d097496156ffb52e5809cb18c8cbedc80a4f83687055ae568a123aa7f`.
- Exact projected baseline request identity unchanged:
  `fa6c1d36f4b19f7fba5e2a48977a2e5397bdbe8f699e8380def87930eb8dfc05`.
  The comparison envelope exactly equals the existing Writer request constructor;
  no prompt/settings/schema/context changes were made to obtain this result.
- Static scan found no removed provider endpoint URLs, credential names or exact
  direct-provider model IDs in maintained src/tools/template configuration. Removed
  slot names survive only in negative tests asserting rejection, and in historical
  documentation. Source evidence may retain ordinary publisher references.

No API/authentication/source call, live model response, package change or quality
result was produced. Existing Writer failures remain known, not fixed by this
routing cleanup. No independent Reviewer findings or milestone closure claimed.

## Current operating boundary

Default offline preflight remains:

```sh
PYTHONDONTWRITEBYTECODE=1 tools/agent_foundation/.venv/bin/python tools/compare_writers.py \
  --input data/generated/m23b-us-linkedin-v3/writer-input.json \
  --source-state data/generated/m23b-us-linkedin-v3/state.json \
  --select qwen30
```

The historical snapshots are optional experiment inputs, explicitly checksum-
verified. They are not required by the application/tests/build/deployment. Tests
use canonical safe fixtures; there is no dependency on workspace.

Stop for owner review. The next model-choice/qualification/test checkpoint requires
its own authorization; no previous spending permission transfers automatically.
Do not reactivate direct providers, swap models, execute another Writer call,
change the prompt/validator, add Reviewer/UI/dependencies or publish Git changes
without the corresponding explicit owner instruction.
