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
