# Design-time consistency checks (ROADMAP 2.2)

Date: 9 October 2026. `python evaluation/design_checks.py --all`; tests in `tests/test_design_checks.py`.

## Method

`mcp/mandate_export.py` renders a domain's specification (Principal, Mandates and their decomposition, boundary constraints with the keys their predicates read, risk parameters with values, registry rules, containment rules) as RDF in the vocabulary of the OntoUML model (`ontology/ontouml/ai-intent.gufo.ttl`). Seven checks run on that rendering, D1 to D6 as SPARQL queries and D7 against the model's cardinality restrictions. They read the graph under the closed-world assumption: an OWL-RL closure of the same graph (tried first) reports nothing, because OWL's open world rarely makes a cardinality or a missing reference inconsistent and OWL RL does not evaluate cardinalities on anonymous inverse properties.

| Check | Defect it finds | The runtime gate cannot see it because |
|---|---|---|
| D1 unused parameter | a risk parameter no predicate, containment rule or kernel step reads | changing it changes nothing at runtime, silently |
| D2 foreign or missing key | a predicate reads a parameter its own Mandate does not define | the evaluation would fail or read the wrong agent's value |
| D3 contradictory bounds | a floor above a ceiling on the same field | no output can satisfy both; every message would be rejected |
| D4 set conflict | an approved value that a prohibition on the same field forbids | approval and rejection of the same value |
| D5 cap above parent | a sub-mandate's allocation cap above its parent's | the containment check covers only declared pairs |
| D6 rule registry | a constraint whose rule is unregistered or does not apply to its Mandate | a verdict would cite a rule outside the agent's commitment |
| D7 model cardinality | the content violates a cardinality of the conceptual model | the model is not consulted at runtime |

Each check has a mutation test that injects its defect and expects the finding.

## Findings on the shipped specifications (before the fixes)

| Domain | Finding | Consequence | Fix |
|---|---|---|---|
| procurement | D1: `services.max_lot_value_eur` unread | the EU services threshold (Art. 4) was not enforced for services at all | new specification `MANIFEST_SERVICES_LOT_VALUE` |
| finance | D1: `stocks.leverage_permitted`, `materials.leverage_permitted` unread | setting them to true would not have permitted leverage | the leverage prohibitions apply only while the parameter is false (`condition_param`) |
| finance | D1: `bonds.warn_duration_years` unread; the duration warning had no predicate (the last C4 finding) | the obligation to flag durations above 7 years was not checked | flag obligation `O(duration ≤ 7 ∨ flagged)`, kind `flag_above`; warn severity |
| procurement | D1: `direct_award_permitted`, `performance_guarantee_required` unread | as for leverage | conditions on the procedure prohibitions and on the guarantee obligation |
| both | D1: `timeout_seconds`, `deterministic_checks_first` of the gate unread | declared policies with no effect | the semantic checker's LLM call uses the timeout; a gate with `deterministic_checks_first = false` refuses to run |
| model | D7: a Mandate bears exactly one boundary constraint (all specialist Mandates have five to seven) | the conceptual model contradicts every Mandate | `build_model.js`: constraint end 1..*; the same default also made claims, verdicts and dispositions exactly one per bearer, corrected to 1..* and 0..* |

Two consequences beyond the findings themselves. First, warn severity is now honoured: a failed warn-severity rule is recorded on the verdict (`warnings`) but does not block, as the CLAUDE.md rule registry always specified ("only block prevents delivery") and the gate did not implement. Second, the procurement domain I wrote on the same day had the unread services threshold: the check found a gap in a specification written with the check's own author in the loop, which is the argument for running it before every campaign.

After the fixes: 0 findings on both domains, C1 to C4 clean on both, OntoUML model schema-valid with 0 verification issues.
