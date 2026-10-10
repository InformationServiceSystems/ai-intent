# Specification-predicate consistency (8 October 2026)

The ER 2026 paper names as its most important limitation that the text and the predicate of a boundary constraint are authored separately, so a miscoded predicate is enforced silently and the trace records the mismatch as intended. The question whether this is still possible has a short answer: yes, in two of fourteen constraints, and the mechanism that would exclude it by construction is not yet in place. What is in place since today is a deterministic check that makes every such divergence visible, and a test that fails on any new one.

## The check (`evaluation/spec_consistency.py`)

| Id | Question | Result on 8 October 2026 |
|---|---|---|
| C1 | Does the text of a threshold constraint state the number the predicate enforces (via the manifest's risk parameter)? | 0 findings in 7 threshold constraints |
| C2 | Does the text of a term-based constraint name the terms the predicate looks for? | 2 findings: `MANIFEST_STOCKS_LARGECAP` (text: market cap above $10 billion; predicate: forbids mid-cap, small-cap, penny stock, OTC) and `MANIFEST_MATERIALS_APPROVED` (text: gold and silver only; predicate: forbids oil, copper, platinum, palladium and others) |
| C3 | Is the text the gate cites identical to the text in the agent's manifest? | 3 findings before the fix (bond constraints had been shortened or split in the registry); 0 after aligning the registry to the manifest wording |
| C4 | Does every manifest constraint that states a number or a prohibition have a predicate? | 2 findings, both known: the duration warning (an obligation to flag) and the rebalancing trigger (needs portfolio state, ROADMAP 1.1) |

`tests/test_spec_consistency.py` requires C1 and C3 to be empty and C2 and C4 to equal the documented sets.

## What the two C2 findings mean

Both predicates are proxies: a closed list of forbidden terms stands in for a positive rule over a set or a threshold the gate cannot evaluate from prose. An equity in a company the model calls "a leading firm" without a capitalisation passes the large-cap rule; a recommendation of lithium passes the approved-commodities rule. The ER 2026 paper's limitation is thus not hypothetical; the check locates it precisely.

## Is Object-Role Modeling the answer?

Partly. ORM would remove C1 and C3 by construction, because the verbalisation of a constraint and its formal form come from one model, and it would replace the two C2 proxies by set and value constraints with formal semantics (`commodity ∈ {Gold, Silver}`, `market_cap > 10e9`, `rating ≥ BBB+`). ORM 2 also carries deontic modality, which matches the deontic type of the triple. Two things it does not do. It presupposes structured agent outputs: an ORM constraint needs a population to check, and prose is not one, so ROADMAP item 1.2 (typed output fields) must come first. And it does not verify the interpreter that evaluates predicates; that remains the job of the oracle test. The tooling is a practical constraint as well: NORMA requires Visual Studio on Windows; a lightweight verbaliser that generates the registry text from the predicate and the risk parameter would give the single-source property for C1 and C3 without ORM's formal apparatus.

## Recommended order

1. Structured output fields in the specialists' responses (ROADMAP 1.2), evaluated before prose extraction.
2. Replace the two proxy predicates by a set constraint and a threshold constraint over those fields; C2 then becomes empty.
3. Generate constraint texts from predicates (verbaliser or ORM); C1 and C3 become true by construction rather than by test.

## Update, 8 October 2026, later the same day: single source implemented

`agents/constraint_spec.py` now holds one `ConstraintSpec` per boundary constraint. The manifest text, the predicate and the registry entry are generated from it, and every number is read from the agent's risk parameters (`STOCKS_RISK`, `BONDS_RISK`, `MATERIALS_RISK`, `CENTRAL_RISK` in `agents/manifests.py`). Consequences:

- C1 and C3 hold by construction; the check remains as a regression guard.
- C2 is empty: the two former proxies state in their text which terms they forbid ("mid-cap, small-cap, micro-cap, penny stock or OTC equities are outside the universe"; "oil, crude, natural gas, ... are not permitted"). They remain term lists over prose until structured outputs allow set and threshold constraints.
- C4 is unchanged: the duration warning and the rebalancing trigger have no predicate.
- The Compliance Agent's interpreter is untouched; the oracle test still reproduces it byte for byte with the generated texts.

Roadmap item 2.1 was rewritten accordingly: the ORM principle is applied, the ORM tooling is not, and the conditions under which full ORM would pay off are stated.

## Update, 8 October 2026, evening: structured outputs (ROADMAP 1.2)

The equities agent now returns `positions` with `market_cap_usd`, the commodities agent `commodities` with names. The large-cap rule is a threshold constraint (`min`) over the capitalisation against `max_market_cap_threshold`, the approved-commodities rule a set constraint (`in_set`) over the names against `approved_commodities`. The term lists remain as prose fallback when a field is absent, reproducing the earlier behaviour exactly. Lithium now fails the set constraint and a $4 billion company fails the threshold, whatever the prose says. Credit ratings, durations and ESG remain prose-evaluated; the mechanism to retire them is in place.

## Update, 8 October 2026, night: all constraints structured-first

Every boundary constraint now has a typed field: holdings with rating, maturity, allocation and region plus a portfolio duration for bonds; instrument and ESG assessment on positions; instrument on commodities and a top-level inflation rationale; allocation per asset class in the synthesis. Predicate kinds: `max_threshold` (also summed per group, e.g. per maturity year), `min_threshold` (numbers and an ordinal credit-rating scale), `in_set`, `not_in_set`, `required_field`. The prose mechanisms are retained only as fallback and reproduce the earlier detail strings; 45 tests cover both paths.

### Dry run with typed fields (8 October 2026, llama3.1:8b, four test cases)

| Agent | Field | Emitted |
|---|---|---|
| bonds | `holdings` | 5 of 5 responses |
| bonds | `portfolio_duration_years` | 5 of 5 |
| materials | `commodities` | 4 of 5 |
| materials | `inflation_rationale` | 5 of 5 |
| stocks | `positions` | 0 of 2 (key present, list empty) |

Of 55 evaluations of manifest constraints, 36 ran on the structured path and 19 on the prose fallback. The fallback is therefore still needed with this model, mostly for the equities agent, whose positions list it leaves empty. All nine integrity checks held on every session. A more capable model, or a response schema enforced by the serving layer, would move the remaining evaluations to the structured path; the gate's behaviour does not depend on which path was taken.

### Schema-enforced responses (8 October 2026)

With a JSON schema passed as `response_format` (Pydantic models in `agents/schemas.py`; Ollama enforces it by constrained decoding), the equities agent filled `positions` in 3 of 3 probes with named companies, instruments and ESG assessments, where it had left the list empty in 2 of 3 probes without the schema. The commodities agent filled its fields; the bond agent returned an empty `holdings` list in one probe, so the prose fallback remains in place. Two observations matter for the paper. First, the model copies example values from the prompt (a $250 billion example became Microsoft's capitalisation); the examples are now recognisable placeholders and a copied placeholder item is ignored by the gate. Second, the typed values are self-declarations: a model that states a $12 trillion capitalisation for Johnson & Johnson passes the large-cap floor on a false number. The gate verifies the declaration against the Mandate, not the declaration against the world; that is the division of labour the ER 2026 paper describes for the Compliance Agent, and a data source for market data would be the remedy.

Dry run with schemas on every call (four test cases): all four completed, all nine integrity checks held, the routing and synthesis schemas were honoured in every call, `allocation_by_asset_class` was present in 10 of 10 synthesis attempts, `positions` in 1 of 1, `holdings` and `portfolio_duration_years` in 2 of 2, `commodities` and `inflation_rationale` in 4 of 5. Of 42 manifest-constraint evaluations, 19 ran on the structured path and 23 on the prose fallback, the latter mostly where a list was returned empty; the fallback therefore stays.

## Update, 10 October 2026: whether the bound itself is admitted (C5)

The oracle disagreed with the gate on two responses of the final campaign in which the 8B model proposed positions with a market capitalisation of exactly $10 billion. The Mandate says "must exceed $10 billion"; the gate's `min` predicate admitted the bound. The same reading applied to "Portfolio duration must remain below 10 years", where the gate admitted exactly 10 years. C1 could not see this: it compares the number in the text with the number in the predicate, not whether the text includes or excludes that number.

- `ConstraintSpec` and `Predicate` carry `strict: bool`; the gate evaluates `v <= bound` (minimum) and `v >= bound` (maximum) when it is set. The large-cap floor and the duration cap are strict; every other bound ("maximum", "at most", "no more than", "not exceed", "longer than") admits its value, as before.
- C5 reads the wording of every threshold text and reports a text that excludes the bound with a non-strict predicate, a text that admits it with a strict predicate, and a text that does not say either. The last finding appeared for "must lie between" and "may carry more than", which are inclusive readings and are now in the check's vocabulary. All three domains report no finding.
- The oracle had encoded both bounds as strict from the texts. After the change the current gate agrees with the oracle on every pair of the final campaign.

