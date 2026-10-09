# Independent oracle for specification-to-predicate consistency (ROADMAP 3.2)

Date: 9 October 2026. `python evaluation/oracle_agreement.py` (logged gate verdicts) and `--regate` (current gate re-evaluated on the logged payloads); tests in `tests/test_oracle.py`.

## Design

The evaluation's expected rule ids and the gate's predicates share one source, the ConstraintSpec. The oracle is a second encoding of the same Mandates:

- **Source:** the natural-language Mandate texts and risk parameters, plus the response schema as the interface; not `agents/constraint_spec.py` or the gate.
- **Formalism:** SHACL-SPARQL shapes (`evaluation/oracle/shapes_finance.ttl`, `shapes_procurement.ttl`), one or two per rule, each naming the rule id it encodes; applied to the oracle's own RDF rendering of an agent response with its own number and rating parsing.
- **Reading of the text:** where the text fixes a boundary, the shape follows the text ("must exceed $10 billion": exactly 10 billion violates; "remain below 10 years": exactly 10 violates); an unrecognised rating cannot establish investment grade; an empty CPV code cannot establish membership of division 45.
- **Comparison:** for every logged response and every rule the gate evaluated on a typed field the response carries, the gate's verdict on that rule against the oracle's. 6819 pairs from 2310 responses in 1023 sessions (the six ten-run campaigns, the full suites and the dry runs of 9 October 2026; the earlier campaigns predate the typed fields).
- **Limitation:** independence is in source and formalism, not in authorship; the same author wrote both encodings. The SHACL engine (`pyshacl`) is used to establish that running each shape's SELECT once over the whole graph gives the same violations as per-focus-node validation (test); the full comparison uses the fast path (seconds instead of hours).

## Results

| Comparison | Agreement |
|---|---|
| first run, logged gate verdicts | 6246 of 6819 (91.6 %) |
| after fixing three oracle defects, logged gate verdicts | 6764 of 6819 (99.19 %) |
| current gate re-evaluated on the logged payloads | 6819 of 6819 (100 %) |

**Oracle defects (fixed in the oracle):** floats converted exactly to `xsd:decimal` (0.4 became 0.40000000000000002, 527 of the first 573 disagreements); "N/A" read as rating A; "BBB+/Baa1" read as BBB.

**Gate defects (fixed in the gate):**

1. *Unrated holdings passed the rating floor.* A holding whose rating the gate could not parse ("N/A", an equity fund or gold listed among bond holdings) was skipped, so the floor passed. 24 logged responses. An unrecognised rating now ranks below every rating.
2. *Combined notations were not parsed.* "AAA+/Aaa" was read as one unknown token; ratings are now found token by token.
3. *Placeholder filtering hid real content.* The gate dropped every item whose name contained "example", and later every item that carried the prompt's sentinel market cap. The model names real proposals "Example 5-year bond" and copied the sentinel into real positions; the gate then evaluated prose or an empty list. Effects in the logs: false rejections (ladder, ESG, sustainability) and false passes (a 15 % leveraged ETF position, a 45 % maturity bucket). A copied example is now evaluated like any proposal, and only a copied sentinel value is treated as unknown.
4. *Empty values passed a set constraint.* A works lot without a CPV code ("Bicycle supply contract") passed "CPV division 45 only". An empty value now cannot establish membership.

**Text-predicate inconsistencies (fixed in the text):** the stocks leverage prohibition also forbade futures, options, swaps and CFDs, the materials one also margin, short, options, swaps and CFDs, and the emerging-market prohibition also frontier and developing markets, none of which the texts named. C2 did not check the forbidden values of set-exclusion predicates; it does now, and the texts name every forbidden value. The texts were widened to the predicates rather than the predicates narrowed to the texts; this is a decision for the author.

## What this means for the evaluation

In the campaigns, 29 responses passed the gate although their typed content breached a rule as the Mandate text states it (24 unrated bond holdings, two hidden leveraged or over-cap positions, one oversized bucket, one leverage reference, one lot without CPV code). BVC was 100 % in every run because BVC measures whether a rejected message is delivered, not whether the gate's verdict is right. The oracle measures the second, and found the gate's verdict wrong in 0.4 % of the evaluated pairs, always through input normalisation (placeholders, rating notation, missing values), never through a wrong bound. A paper claim of "no non-compliant message delivered" therefore needs the qualifier "as judged by the gate", together with the oracle agreement as the evidence that the gate's judgement matches the Mandate texts.
