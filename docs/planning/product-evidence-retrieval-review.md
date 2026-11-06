# Product-evidence retrieval tool - implementation and review

Status: **OWNER ACCEPTED — 2026-11-06**. Full M1.5b.4 acceptance remains separate.
The closure record below supersedes historical review-pending descriptions. Authority: owner approved the
proposed bounded work and one live eight-case run while on break. This checkpoint
advances the north star's evidence access, not autonomous generation or launch decisions.

## Plain-English result

The application can now search the frozen product corpus and open its declared
supporting references through one callable tool. The formerly missing flavor claim
is recovered automatically from a returned summary, with the complete evidence.
All eight fixed cases have their expected evidence in the combined results.
Direct semantic top-three coverage remains **7/8**: this is evidence enrichment,
not an improved ranking or a new statistical accuracy claim.

One query correctly reports **incomplete**: the lower-ranked positioning summary
references more records than the five-additional-record limit. PROD-014 and
PROD-015 remain unresolved for that summary. Its `usable_as_complete_evidence`
flag is false. The overview, flavor PROD-002 and inspiration PROD-003 support
are resolved. We did not enlarge the limit, drop qualifications, change the
queries or hide this warning. The combined 8/8 coverage must not be described as
8/8 wholly complete tool responses; seven responses have no issues, one is partial.

## What was built

- src/launchlens/retrieval.py: standard-library callable tool and restricted HTTP transport.
- tests/test_retrieval.py: 16 offline safeguard tests with safe authored fixtures.
- tools/validate_product_retrieval.py: offline preflight and one-shot live evaluator.
- This report: durable setup, actual results and readable examples. Original datasets,
  45 prepared packets, historical scripts/reports and frozen expectations stay unchanged.

The model will eventually select the research question/category. The harness fixes
product CC-CHERRY-FLOAT, E5 multilingual-e5-large, 1024 dimensions and the existing
validation namespace m15b4-corpus-validation-v1 in launchlens-e5-sample-v1.
This is not an application-index migration or a new agent framework.

Input: query plus public_product_facts or synthetic_product_intent. Query input is
bounded to 1-2000 characters; hosted token overflow is rejected via truncate=NONE,
not silently truncated. The runtime needs no local tokenizer. Root search is filtered
by product and requested authority. Each returned record is decoded/checked against
approved source document/version/SHA bindings and its canonical evidence digest.
The digest detects corruption, not coordinated malicious rewriting of evidence and
digest; existing Pinecone access control and the frozen corpus remain trust boundaries.

Top five search hits keep their original ranks/scores (not confidence probabilities).
Follow declared links in ranked-parent order, then declared link order; deduplicate,
skip already-returned IDs, fetch at most five more in one batch, and never recurse.
PRD links to public claims retain public authority; public-to-synthetic links are
rejected. Full evidence_payload is returned unchanged with authority, citations,
qualification/source roles, page provenance and acceptance snapshot. Historical
pending labels do not override canonical source acceptance. There is no local JSONL lookup.

Result statuses are evidence_found, incomplete or error. evidence_found means valid
retrieval without reported transport/reference problems, not exhaustive research,
launch permission or factual entailment. Missing/corrupt evidence is unusable and
explicit; unresolved summaries are flagged. No matches do not establish product
unavailability. All results carry the operational calendar/readiness boundary notice.

## Verification results

Fresh tests: **81 PASS** = 42 prior preparation + 16 new retrieval + 23 prior
projection/codec. Safe fixtures cover unchanged full packets, genuine reference
recovery/deduplication, authority separation, source/version/product rejection,
missing/corrupt/unexpected records, five-target limit, one-hop bound, invalid inputs,
bad vectors, no matches and transport failures. Timeout/HTTP failures do not retry
or expose credentials. A successful fixture-backed retrieval ran in an empty cwd
with site packages disabled and no .env, workspace, generated files or tokenizer.

Offline replay of the original eight response snapshots reproduced expected
combined coverage and the explicit reference-budget warning before the live run.
This replay was not a second hosted query run.

| Fixed GTM case | Expected evidence | Direct top-three coverage | Combined returned evidence | Tool status |
|---|---|---|---|---|
| GTM-01: Supported flavor and inspiration for campaign messaging | PROD-002, PROD-003 | MISS | Present | incomplete |
| GTM-02: Variant distinction in the campaign brief | PROD-004 | PASS | Present | evidence_found |
| GTM-03: Market-specific packaging claims for US copy | PROD-005 | PASS | Present | evidence_found |
| GTM-04: Audience hypotheses for the fictional campaign | audience | PASS | Present | evidence_found |
| GTM-05: Competitive context for proposed differentiation | competitive-context | PASS | Present | evidence_found |
| GTM-06: Qualified Canadian announcement context for regional messaging | PROD-012 | PASS | Present | evidence_found |
| GTM-07: Synthetic requirement for availability claims | REQ-007 | PASS | Present | evidence_found |
| GTM-08: Surface the evidence gap before India availability copy | unknowns | PASS | Present | evidence_found |

One live run: 2026-11-05 23:58:51 to 23:59:04 PST,
12.822 seconds for this validation only. All 22 HTTP responses
were 200: eight query-embedding requests, eight similarity searches and six reference
fetches. E5 reported 248 query tokens total. Read/inference usage can incur charges;
actual dollar billing was not inspected. No record writes, embeddings of documents,
new index, retries, model-generated copy or Notion/Nebius/Tavily calls occurred.
All eight top-five ID sequences match the historical semantic baseline. All 57
returned packet occurrences (34 distinct IDs) matched the approved projection
byte-for-byte after canonical serialization, including citations/qualifications.
This checks retrieved evidence, not a fresh full45 vector-storage audit.

## Readable views of actual returned evidence

These show selected fields/passages from real tool responses, not generated marketing
copy or a claim that an LLM has already consumed the tool. The full JSON result retains
all fields/context unchanged. The expanded blocks below display the exact full packet
text for each selected record; structured source mappings/provenance also remain in
responses.jsonl. Thus shortened views are display-only, not evidence removal.

### 1. Flavor claim recovered through a reference

Origin: reference; search rank: not a direct search hit; authority: public_product_facts; PDF pages: 1, 2, 3.

Exact primary passage:

> PROD-002 | SOURCE_SUPPORTED | S2, S3. The documented flavor combines cherry with vanilla notes.

Claim-specific citations and limitations (shared context is separately labeled in the payload):

- [S2 — Coca-Cola Soda Flavors: Vanilla, Cherry, and More](https://www.coca-cola.com/us/en/brands/coca-cola/products/coca-cola-flavors); scope: United States and Great Britain descriptions. Flavor description, not proof of vanilla ingredient content or a measured taste preference. Publication date not displayed; live U.S. product page accessed on research date.

- [S3 — Coca-Cola Introduces Cherry Float Flavour](https://www.coca-cola.com/gb/en/media-center/coca-cola-introduces-cherry-float-flavour); scope: United States and Great Britain descriptions. Flavor description, not proof of vanilla ingredient content or a measured taste preference. Body explicitly states 9 February 2026.

<details>
<summary>Exact full evidence-packet text retained by the tool</summary>


```text
PROD-002 | SOURCE_SUPPORTED | S2, S3. The documented flavor combines cherry with vanilla notes.

Source classification: Publicly verified product information (source-supported; not independent product testing).

Evidence domain: PRODUCT_TRUTH. No simulation dates, readiness decisions or launch approvals are supplied.

Temporal boundary: this is retrospective research using live and dated public sources. The fictional exercise is set
before the February 2026 rollout; its precise simulation date is unspecified. This brief does not certify what was
knowable at that earlier date. A 2025 public notice already names the product (PROD-014).

SOURCE_SUPPORTED means the cited official source supports the scoped statement.
QUALIFIED_SOURCE_STATEMENT records a dated or regional publisher statement with limitations; it does not
verify actual rollout or current availability. All claims are PRODUCT_TRUTH evidence; owner acceptance is pending.
The CSV provides per-source locators and limitations.

Mandatory qualification: S1 gives broader portfolio timing; S4 separately specifies March 2026 for Cherry Float and
February 2026 for Diet Coke Cherry in Canada. This difference in specificity does not establish a direct conflict or
actual shelf arrival. Permanent Great Britain and limited-time Canada wording are regional. No fictional readiness or
approval is established. Preserve the CSV limitations when using a claim.

Commercial gaps: no Cherry Float price by market/pack, sales forecast, market share, conversion claim or
comparative performance claim is verified by this brief.

Regional gaps: actual store inventory and first shelf-arrival dates are unverified. No India source is included; absence
of evidence does not establish unavailability or a legal restriction. No global availability duration is established.

Product limits: no cross-market ingredient equivalence, allergen certification, health benefit or regulatory approval is
verified. Nutritional values beyond the two identified U.S. label statements are outside this claim set.

Simulation boundary: the later PMM Brief, Launch Calendar and Readiness Tracker must identify fictional
assumptions separately. This brief supplies no market readiness state, launch authorization or invented schedule.

All five sources are official Coca-Cola pages accessed on 2026-11-04. Publication dates below are publisher dates,
not inferred access dates. Numeric dates with unresolved ordering are preserved verbatim. No original articles,
images or logos are reproduced.

This document was independently prepared for an educational Agentic AI demonstration. It uses publicly available
product information in a fictional pre-launch scenario. It is not affiliated with or endorsed by The Coca-Cola Company
and does not represent the company's internal product plans or GTM operations.

S1. Coca-Cola Expands Its Cherry Portfolio with the Launch of Coca-Cola Cherry Float and the Nationwide Release of Diet Coke
Cherry

https://www.coca-colacompany.com/media-center/coca-cola-cherry-float-and-diet-coke-cherry-launch-nationwide.html

Publication: 2026-02-02. Page displays 02-02-2026; unambiguous date.

S2. Coca-Cola Soda Flavors: Vanilla, Cherry, and More

https://www.coca-cola.com/us/en/brands/coca-cola/products/coca-cola-flavors

Publication: not displayed. Publication date not displayed; live U.S. product page accessed on research date.

S3. Coca-Cola Introduces Cherry Float Flavour

https://www.coca-cola.com/gb/en/media-center/coca-cola-introduces-cherry-float-flavour

Publication: 2026-02-09. Body explicitly states 9 February 2026.

S4. Coca-Cola Expands Its Cherry Portfolio with Coca-Cola Cherry Float and the Nationwide Release of Diet Coke Cherry

https://www.coca-cola.com/ca/en/media-centre/news/coca-cola-cherry-float-diet-coke-cherry-canada

Publication: 02/05/2026. Date preserved as displayed; numeric month/day ordering not independently resolved.

Source-specific CSV evidence (separate from PDF text):
claim_id: PROD-002
source_id: S2
verification_status: SOURCE_SUPPORTED
market_scope: United States and Great Britain descriptions
temporal_scope: Retrospective evidence snapshot; not certified available at fictional pre-launch date
source_locator: Products > Coca-Cola Cherry Float
notes_or_limitations: Flavor description, not proof of vanilla ingredient content or a measured taste preference. Publication date not displayed; live U.S. product page accessed on research date.

claim_id: PROD-002
source_id: S3
verification_status: SOURCE_SUPPORTED
market_scope: United States and Great Britain descriptions
temporal_scope: Retrospective evidence snapshot; not certified available at fictional pre-launch date
source_locator: Opening and flavor-description paragraphs
notes_or_limitations: Flavor description, not proof of vanilla ingredient content or a measured taste preference. Body explicitly states 9 February 2026.
```

</details>

### 2. Canada announcement with its limitation

Origin: search; search rank: 2; authority: public_product_facts; PDF pages: 1, 2, 3.

Exact primary passage:

> PROD-012 | QUALIFIED_SOURCE_STATEMENT | S4. The Canada release separately specifies March 2026 for Cherry
> Float and February 2026 for Diet Coke Cherry.

Claim-specific citations and limitations (shared context is separately labeled in the payload):

- [S4 — Coca-Cola Expands Its Cherry Portfolio with Coca-Cola Cherry Float and the Nationwide Release of Diet Coke Cherry](https://www.coca-cola.com/ca/en/media-centre/news/coca-cola-cherry-float-diet-coke-cherry-canada); scope: Canada; product-specific announcement. S1 describes broader portfolio timing across two countries; S4 provides the product-specific Canadian dates. Do not represent the difference as a confirmed direct conflict. Actual shelf arrival and simulation readiness remain unverified. Date preserved as displayed; numeric month/day ordering not independently resolved.

<details>
<summary>Exact full evidence-packet text retained by the tool</summary>


```text
PROD-012 | QUALIFIED_SOURCE_STATEMENT | S4. The Canada release separately specifies March 2026 for Cherry
Float and February 2026 for Diet Coke Cherry.

Source classification: Publicly verified product information (source-supported; not independent product testing).

Evidence domain: PRODUCT_TRUTH. No simulation dates, readiness decisions or launch approvals are supplied.

Temporal boundary: this is retrospective research using live and dated public sources. The fictional exercise is set
before the February 2026 rollout; its precise simulation date is unspecified. This brief does not certify what was
knowable at that earlier date. A 2025 public notice already names the product (PROD-014).

SOURCE_SUPPORTED means the cited official source supports the scoped statement.
QUALIFIED_SOURCE_STATEMENT records a dated or regional publisher statement with limitations; it does not
verify actual rollout or current availability. All claims are PRODUCT_TRUTH evidence; owner acceptance is pending.
The CSV provides per-source locators and limitations.

Mandatory qualification: S1 gives broader portfolio timing; S4 separately specifies March 2026 for Cherry Float and
February 2026 for Diet Coke Cherry in Canada. This difference in specificity does not establish a direct conflict or
actual shelf arrival. Permanent Great Britain and limited-time Canada wording are regional. No fictional readiness or
approval is established. Preserve the CSV limitations when using a claim.

Commercial gaps: no Cherry Float price by market/pack, sales forecast, market share, conversion claim or
comparative performance claim is verified by this brief.

Regional gaps: actual store inventory and first shelf-arrival dates are unverified. No India source is included; absence
of evidence does not establish unavailability or a legal restriction. No global availability duration is established.

Product limits: no cross-market ingredient equivalence, allergen certification, health benefit or regulatory approval is
verified. Nutritional values beyond the two identified U.S. label statements are outside this claim set.

Simulation boundary: the later PMM Brief, Launch Calendar and Readiness Tracker must identify fictional
assumptions separately. This brief supplies no market readiness state, launch authorization or invented schedule.

All five sources are official Coca-Cola pages accessed on 2026-11-04. Publication dates below are publisher dates,
not inferred access dates. Numeric dates with unresolved ordering are preserved verbatim. No original articles,
images or logos are reproduced.

This document was independently prepared for an educational Agentic AI demonstration. It uses publicly available
product information in a fictional pre-launch scenario. It is not affiliated with or endorsed by The Coca-Cola Company
and does not represent the company's internal product plans or GTM operations.

S1. Coca-Cola Expands Its Cherry Portfolio with the Launch of Coca-Cola Cherry Float and the Nationwide Release of Diet Coke
Cherry

https://www.coca-colacompany.com/media-center/coca-cola-cherry-float-and-diet-coke-cherry-launch-nationwide.html

Publication: 2026-02-02. Page displays 02-02-2026; unambiguous date.

S4. Coca-Cola Expands Its Cherry Portfolio with Coca-Cola Cherry Float and the Nationwide Release of Diet Coke Cherry

https://www.coca-cola.com/ca/en/media-centre/news/coca-cola-cherry-float-diet-coke-cherry-canada

Publication: 02/05/2026. Date preserved as displayed; numeric month/day ordering not independently resolved.

Source-specific CSV evidence (separate from PDF text):
claim_id: PROD-012
source_id: S4
verification_status: QUALIFIED_SOURCE_STATEMENT
market_scope: Canada; product-specific announcement
temporal_scope: Retrospective evidence snapshot; not certified available at fictional pre-launch date
source_locator: Opening paragraph; Cherry Float versus Diet Coke Cherry timing
notes_or_limitations: S1 describes broader portfolio timing across two countries; S4 provides the product-specific Canadian dates. Do not represent the difference as a confirmed direct conflict. Actual shelf arrival and simulation readiness remain unverified. Date preserved as displayed; numeric month/day ordering not independently resolved.
```

</details>

### 3. India evidence gap, without a launch decision

Origin: search; search rank: 2; authority: public_product_facts; PDF pages: 1, 2, 3.

Exact primary passage:

> G. Unknown or unverified information
>
> Commercial gaps: no Cherry Float price by market/pack, sales forecast, market share, conversion claim or
> comparative performance claim is verified by this brief.
>
> Regional gaps: actual store inventory and first shelf-arrival dates are unverified. No India source is included; absence
> of evidence does not establish unavailability or a legal restriction. No global availability duration is established.
>
> Product limits: no cross-market ingredient equivalence, allergen certification, health benefit or regulatory approval is
> verified. Nutritional values beyond the two identified U.S. label statements are outside this claim set.
>
> Simulation boundary: the later PMM Brief, Launch Calendar and Readiness Tracker must identify fictional
> assumptions separately. This brief supplies no market readiness state, launch authorization or invented schedule.

This is a recorded evidence gap, not a supported India availability claim. Shared-qualification citations remain context references, not India launch authorization.

<details>
<summary>Exact full evidence-packet text retained by the tool</summary>


```text
G. Unknown or unverified information

Commercial gaps: no Cherry Float price by market/pack, sales forecast, market share, conversion claim or
comparative performance claim is verified by this brief.

Regional gaps: actual store inventory and first shelf-arrival dates are unverified. No India source is included; absence
of evidence does not establish unavailability or a legal restriction. No global availability duration is established.

Product limits: no cross-market ingredient equivalence, allergen certification, health benefit or regulatory approval is
verified. Nutritional values beyond the two identified U.S. label statements are outside this claim set.

Simulation boundary: the later PMM Brief, Launch Calendar and Readiness Tracker must identify fictional
assumptions separately. This brief supplies no market readiness state, launch authorization or invented schedule.

Source classification: Publicly verified product information (source-supported; not independent product testing).

Evidence domain: PRODUCT_TRUTH. No simulation dates, readiness decisions or launch approvals are supplied.

Temporal boundary: this is retrospective research using live and dated public sources. The fictional exercise is set
before the February 2026 rollout; its precise simulation date is unspecified. This brief does not certify what was
knowable at that earlier date. A 2025 public notice already names the product (PROD-014).

SOURCE_SUPPORTED means the cited official source supports the scoped statement.
QUALIFIED_SOURCE_STATEMENT records a dated or regional publisher statement with limitations; it does not
verify actual rollout or current availability. All claims are PRODUCT_TRUTH evidence; owner acceptance is pending.
The CSV provides per-source locators and limitations.

Mandatory qualification: S1 gives broader portfolio timing; S4 separately specifies March 2026 for Cherry Float and
February 2026 for Diet Coke Cherry in Canada. This difference in specificity does not establish a direct conflict or
actual shelf arrival. Permanent Great Britain and limited-time Canada wording are regional. No fictional readiness or
approval is established. Preserve the CSV limitations when using a claim.

All five sources are official Coca-Cola pages accessed on 2026-11-04. Publication dates below are publisher dates,
not inferred access dates. Numeric dates with unresolved ordering are preserved verbatim. No original articles,
images or logos are reproduced.

This document was independently prepared for an educational Agentic AI demonstration. It uses publicly available
product information in a fictional pre-launch scenario. It is not affiliated with or endorsed by The Coca-Cola Company
and does not represent the company's internal product plans or GTM operations.

S1. Coca-Cola Expands Its Cherry Portfolio with the Launch of Coca-Cola Cherry Float and the Nationwide Release of Diet Coke
Cherry

https://www.coca-colacompany.com/media-center/coca-cola-cherry-float-and-diet-coke-cherry-launch-nationwide.html

Publication: 2026-02-02. Page displays 02-02-2026; unambiguous date.

S4. Coca-Cola Expands Its Cherry Portfolio with Coca-Cola Cherry Float and the Nationwide Release of Diet Coke Cherry

https://www.coca-cola.com/ca/en/media-centre/news/coca-cola-cherry-float-diet-coke-cherry-canada

Publication: 02/05/2026. Date preserved as displayed; numeric month/day ordering not independently resolved.
```

</details>

## Runtime setup and reproduction

Use the existing Python 3.12 environment; no additional dependencies installed.
The runtime reads no files and performs no automatic downloads. Provision the
Pinecone key explicitly through the caller's environment or secret mechanism; it
is never logged or embedded in docs. The local audit harness alone reads the ignored
private .env file, requiring mode0600. The two source bindings/host/namespace are
pinned in maintained code for this frozen MVP; their changes need owner review.

```python
import os
from launchlens.retrieval import PineconeHTTP, retrieve_product_evidence

transport = PineconeHTTP(os.environ["PINECONE_API_KEY"])
# This call performs provider inference/reads; run only within authorized scope.
result = retrieve_product_evidence(
    "What flavor and inspiration can support our Cherry Float campaign?",
    "public_product_facts",
    transport=transport,
)
```

Run with src on PYTHONPATH (or the eventual approved app entrypoint). The complete
packets can be large; selective LLM prompt assembly remains later agent work, with
no evidence silently lost. This checkpoint returns evidence and does not build prompts.

Offline checks:

```sh
.venv/bin/python -m unittest discover -s tests -q
tools/embedding_preparation/.venv/bin/python -m unittest discover -s tools/embedding_preparation/tests -q
.venv/bin/python tools/validate_product_retrieval.py
```

The evaluator's approved-original comparison uses the explicitly provisioned B3
projection in ignored data/generated/m15b-embedding-projection/; regenerate it using
[m1.5b3-embedding-review.md](m1.5b3-embedding-review.md) and its B1/B2 setup references
if missing. This is an audit dependency, not a runtime-tool dependency. The frozen
case manifest is maintained in tools/gtm_retrieval_cases.json. No workspace input.

`--execute` already ran once and refuses its existing receipt directory; rerunning
hosted work or replacing historical results requires new authorization. Do not delete
receipts to bypass that boundary. Generated receipt/responses remain ignored in
data/generated/product-evidence-retrieval/. This canonical report preserves the
concise verification independently of those large execution outputs.

## Evidence hashes

| File | SHA-256 |
|---|---|
| src/launchlens/retrieval.py | `4da62831a0311d0d180219d474cec7320bc494988835885f03b5f317992c19fc` |
| tests/test_retrieval.py | `ee7cc381f281be21527035c28bf8edd565b9eb53816ac0205ec597a6a59a6bb5` |
| tools/validate_product_retrieval.py | `e27a2b0defcd56a84866b72f2fabea73d032768e2ff1e80d41047c86729ba6f8` |
| tools/gtm_retrieval_cases.json | `87fc5d94341f2f6c491bf6240f62b265639fdbde7d6f0d8dc9e0fec350d9105d` |
| data/generated/product-evidence-retrieval/receipt.json | `8ba06bfadfa1d7e5b6217cbede7423a358bf2469844d2c428a8d37bea139a631` |
| data/generated/product-evidence-retrieval/responses.jsonl | `69f6a32c1d4b7df549147106e8c141b36d8bdcd459a5bbec104d75badba728d7` |

## Review boundary and next step

Recommendation: review the bounded tool with its disclosed partial-reference case;
keep the fixed five-target budget for now. Do not present the partial positioning
summary as complete or require arbitrary exhaustive reference expansion. No tuning,
framework or separate evidence store is justified by this run. Original ranking
miss remains recorded. This is a small fixed-case validation, not general retrieval
accuracy, answer-grounding, prompt-injection resistance or launch-guardrail proof.

Owner action: accept or request corrections to this tool checkpoint, including the
explicit incomplete result for lower-ranked positioning references. Full M1.5b.4
acceptance is a separate decision, not inferred here. After review, separately
scope the Notion read adapter/launch harness and autonomous-agent connection.
No agent/Reviewer/UI, Tavily, model adoption, corpus/schema change, staging, commit,
push or subsequent milestone was performed or authorized by this checkpoint.

## Owner acceptance and authorized Git sync - 2026-11-06

The owner approved “Review and consolidate — Accept or correct the completed tools,
then authorize Git sync” and explicitly requested the sync. **Both the product-evidence
retrieval tool and Notion read tools/deterministic launch checks are OWNER ACCEPTED.**
Acceptance includes the disclosed five-reference cap and incomplete positioning
summary; the original direct semantic coverage remains7/8, with expected supporting
records present for all eight fixed cases after reference-following. This does not
claim eight wholly complete responses or general retrieval accuracy.

The owner authorizes security/diff review, commit and push of these maintained tools,
tests, validation harnesses, review records and supporting status documentation to
the existing private repository. Fresh offline verification:77 root tests plus23
projection/codec tests, **100 PASS**. Historical live results remain unchanged; no
provider calls are repeated. Full M1.5b.4 acceptance remains a separate decision.
No autonomous-agent connection, model adoption, Reviewer, UI, dataset/dependency
change or subsequent milestone is authorized. Stop after verified private Git sync.
