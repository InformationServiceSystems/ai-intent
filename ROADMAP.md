# Roadmap

This document lists the planned development of AI-Intent beyond the ER 2026 reference implementation. It follows the three tracks named in the paper's conclusion (modeling, ontological, empirical) and adds the concrete engineering items that the evaluation and the paper's limitations call for. Items are ordered by dependency, not by priority; an item marked *depends on* cannot start before the named item is done.

## 1. Modeling track

### 1.1 Fourth predicate template: state predicates

**Status:** done 9 October 2026. **Motivation:** the Materials Mandate's rebalancing trigger ("flag to orchestrator if allocation drifts more than ±5% from target") was the only boundary constraint without a predicate, because the Compliance Agent had no access to portfolio state (Amendment 4). The same gap prevented any constraint that compares a proposed action with the current position.

**What was done.**

- Two predicate kinds, `state_max` and `state_drift`, alongside the threshold, set and term kinds. Both read the proposed total from the agent's typed field (summed over the items, else the summed `proposed_allocation`) and compare it with a `SessionState` (current and target allocation per category, label, timestamp) that the orchestrator holds for the session and passes to the gate. The state is logged as `state.snapshot` before any sub-agent is called, and every `RuleResult` of a state predicate carries the snapshot it used, so the verdict is reproducible from the trace; the verdict and the accountability note repeat it.
- The rebalancing trigger is `O(|proposed − target| ≤ rebalance_drift_threshold ∨ flagged)`: `MANIFEST_MATERIALS_REBALANCE`, kind `drift`, satisfied by the typed field `rebalance_flag` or by a constraint flag naming the drift. The Materials Mandate has five predicates.
- A second state predicate, `MANIFEST_STOCKS_EXPOSURE` (`state_max`): the current equity allocation plus the proposed positions may not exceed `max_equity_exposure` (0.40, contained in the parent's 40 % cap). A concentration breach that only the state reveals.
- Evaluation: TC-20 (drift beyond threshold without flag) and TC-21 (concentration after the trade) carry their own state; a new dimension SP scores whether each expected state rule was evaluated against that state and the snapshot is in the trace. The finance default state is the empty portfolio, so the ER 2026 cases are unchanged.
- While deriving the schemas, one text-predicate mismatch surfaced that C1 to C4 could not see: "Maximum 15 % of total portfolio in raw materials" was checked per item. It is now the sum over the commodities (`aggregate="sum"`).

### 1.2 Structured agent outputs instead of prose extraction

**Status:** done for the two constraints that needed it, 8 October 2026. The equities agent returns `positions` (name, `market_cap_usd`, allocation) and the commodities agent returns `commodities` (name, allocation) alongside `proposed_allocation`. The large-cap rule is now a threshold constraint over `market_cap_usd` against `max_market_cap_threshold`, and the approved-commodities rule a set constraint over commodity names against `approved_commodities`; both are `ConstraintSpec` kinds (`min`, `in_set`) with the former term lists retained as a prose fallback when the field is absent. The fallback reproduces the earlier behaviour byte for byte, so the oracle test still holds. A commodity such as lithium, or a company stated to be a leading firm without a capitalisation above the floor, is now caught from the structured field.

**Completed the same evening:** every boundary constraint now reads a typed field first. Bonds return `holdings` (name, credit rating in S&P or Moody's notation, maturity years, allocation, region) and `portfolio_duration_years`; equities return `positions` with `instrument` and `esg_assessment`; materials return `commodities` with `instrument` and a top-level `inflation_rationale`; the synthesis returns `allocation_by_asset_class`. The rating floor is an ordinal comparison, the ladder cap sums allocations per maturity year, the ladder obligation needs two distinct maturities, leverage and emerging markets are value checks on `instrument` and `region`, and the disclosures are required fields. The regular expressions and synonym lists survive only as the prose fallback when a field is absent, with unchanged detail strings.

*Depends on* nothing; *enabled* 2.1's last step.

### 1.3 Defeasible norms and session-mutable Mandates

**Status:** research. The constraints have no exception structure and Mandates are immutable within a session; both are deliberate for regulated finance. Extending the model to defeasible deontic logic (a prohibition that a stronger norm can override) and to Mandates that a Principal may amend during a session, with the amendment itself logged as a governance event, widens the class of domains the model transfers to.

## 2. Ontological track

### 2.1 Constraints as a single source, by the ORM principle

**Status:** done 8 October 2026 (`agents/constraint_spec.py`). **Motivation:** the paper's most important limitation was specification-to-predicate consistency: text and predicate of a boundary constraint were authored separately, so a miscoded predicate was enforced silently. A deterministic check (`evaluation/spec_consistency.py`, C1 to C4) located the actual divergences on 8 October 2026: three bond texts had drifted between manifest and registry, and two predicates were term-list proxies of their text.

**What was done.** Each boundary constraint is now one `ConstraintSpec` (template, formal content, deontic type). From it are generated the manifest text the agent sees, the predicate the gate evaluates and the registry entry the gate cites; every number is read from the agent's risk parameters. Text and predicate therefore cannot diverge, and the two proxy predicates now say in their text which terms they forbid. This is the Object-Role Modeling principle, verbalising a constraint from its formal form, applied with a 200-line Python module instead of the ORM tooling.

**Why not full ORM here.** Fourteen constraints in four mandates, written and reviewed by developers, do not justify a modelling tool chain (NORMA requires Visual Studio on Windows) whose verbalisations nobody outside the team would read. Full ORM becomes worthwhile when mandates are authored by compliance staff who review the verbalisations, or when dozens of mandates with cross-references exist. The paper cites ORM as the source of the principle.

**Done the same day.** With structured outputs (1.2) the two proxies became a set constraint (`commodity ∈ approved_commodities`) and a threshold constraint (`market_cap ≥ max_market_cap_threshold`), as `ConstraintSpec` kinds `in_set` and `min`; the term lists remain only as prose fallback.

*Depends on* 1.2 for the last step. *Enables* 2.2.

### 2.2 Design-time consistency checks over the OntoUML model

**Status:** research. Render AI-Intent as a complete OntoUML model and investigate whether design-time reasoning (OntoUML validation, or an OWL rendering of the schema and the Mandates) catches the inconsistencies that the runtime gate cannot: conflicting constraints across Mandates, a risk parameter referenced by no predicate, a predicate whose key points to a parameter of another agent. *Depends on* 2.1 for the Mandate content.

## 3. Empirical track

### 3.1 More capable models

**Status:** first campaign done 9 October 2026. Ten runs of both domains with `llama3.3:70b` next to `llama3.1:8b` on one HPC GPU node (`paper2/generalisation-notes.md`, section 7; `evaluation/c4_summary.md`). The expectation holds: containment (BVC), gate precision (CGP) and trace completeness (ATC) are 100 % in all 40 runs for both models, while the model-dependent dimensions move: with the 70B model Mandate Enforcement rises to 100 % and the agents propose fewer violations, so fewer forced blocks are needed. CDA is now reported together with the exposure rate. Open: a model outside the Llama family, and the full ER 2026 campaign protocol on the 70B model for the paper.

### 3.2 Independent verification of specification-to-predicate consistency

**Status:** planned. The evaluation's expected rule IDs and the enforced predicates share provenance. Introduce an independent oracle, either a second encoding of the Mandates by a different author or the ORM-generated constraints of 2.1, and measure agreement between the two encodings on the 190 sessions. Disagreements are miscodings by construction.

### 3.3 Further domains

**Status:** research. Candidates must satisfy the transfer conditions stated in the paper: a sortal in-or-out-of-scope boundary, norms expressible as decidable prohibitions, session-stable Mandates, tolerance for lexicographic constraint priority. Clinical decision support fails the exception condition and is therefore a test of 1.3 rather than of the core; procurement and public tendering are closer candidates.

## 4. Platform items

- **Deterministic routing for evaluation.** Done 7 October 2026 (`runner.py --deterministic-routing`): the harness fixes the routing to the test case's expected agents; the override is logged and still passes the routing checkpoint. ME is reported without the override (campaigns one and two) and with it (campaign three).
- **Accountability note as a projection of the trace.** Done 9 October 2026 (`agents/accountability.py`). The note is generated from the log and the verdicts: session, principal, domain, every consulted agent with its complete revision history (each rejected attempt with its rule ids, Amendment 2), the number of rule evaluations, violations, blocked agents, the state snapshot and the timestamp. The synthesis model no longer writes the note; what it writes, if anything, is kept as `model_accountability_note` for comparison. Trace completeness (ATC) therefore no longer depends on instruction following.

## 5. Follow-up paper: substantive use of UFO

**Status:** in progress since 6 October 2026. Plan and paper skeleton under `paper2/`. The ER 2026 paper uses UFO for categorisation only; the follow-up uses three parts of UFO as model content.

- **5.1 Delegation as commitment and claim (UFO-C).** `agents/delegation.py` builds the chain Principal to central to sub-agents as relators constituted by a Commitment and a Claim, checks that each sub-mandate is contained in its parent, and resolves a forced block to the chain of answerable parties. Logged as `delegation.establish` and `delegation.breach.{agent}`.
- **5.2 Dispositions as model constructs (UFO-A/B).** `agents/dispositions.py` adds Disposition (bearer, degree, triggering situation, characteristic rule set) and attributes rejections to dispositions deterministically. Logged as `disposition.manifest.{agent}`.
- **5.3 Traces as gUFO graphs.** `mcp/gufo_export.py` exports a session as a gUFO-typed RDF graph from the log alone; `evaluation/sparql_checks.py` states eight integrity invariants as SPARQL queries. Run with `python evaluation/sparql_checks.py --all`.

Two full campaigns ran on 7 October 2026 (`evaluation/ufo_hpc*_results_*.json`, notes under `paper2/`). The paper draft is at `paper2/ai-intent-ufo.tex`. Next: a third campaign with deterministic routing for the evaluation (item 4) after the draft is reviewed.

*Depends on* nothing in sections 1 to 4; *relates to* 2.2, which the gUFO export makes concrete.

## 6. Generalisation to other domains

**Status:** done 9 October 2026 (steps 1 and 2 on 8 October). The kernel reads a `Domain` object (`agents/domain.py`); the finance domain is the first package (`domains/finance.py`); public procurement is the second (`domains/procurement.py`). Behaviour on the finance domain is unchanged except for the two state predicates of 1.1 and the summed materials cap.

- **6.3 Roles instead of names. Done.** No kernel module (`compliance`, `orchestrator`, `delegation`, `dispositions`, `specialist`, `accountability`, `gufo_export`, `runner`) names an agent; `tests/test_generalisation.py` greps for it. The orchestrator, the gate and the specialists are read from the Domain, `get_manifest()` resolves against the active domain, thresholds come from the risk parameters (the cap an agent's risk-seeking check measures against is its first percentage cap), and the vocabularies the disposition integrity checks used (cross-scope terms, complexity terms) are `SpecialistConfig.scope_terms` and `Domain.complexity_terms`. The disposition presets, the containment rules and the test cases moved into the domain package. The UI draws the graph, the sequence diagram and the panels from the domain and has a domain switch in the sidebar.
- **6.4 Dispositions over constraint tags. Done.** Every `ConstraintSpec` and `RegulatoryRule` carries tags (`allocation_cap`, `exposure_cap`, `leverage`, `disclosure`, `scope`, `quality_floor`, `structure`, `authority`, `specificity`, `process`, `monitoring`); `KIND_TAGS` maps the five disposition kinds to tags and `manifestation_map()` computes the characteristic rule sets. For finance the computed map equals the hand-written ER 2026 map (test), so the published attribution is unchanged.
- **6.5 Response schemas from specs. Done.** `derive_response_model()` builds a specialist's response model from the `structured_field`, `item_key`, kind, `field_enum` and `field_description` declarations of its specs; routing and synthesis models are derived from the specialist ids and the orchestrator's specs. The derived finance schemas require the same fields as the hand-written ones (test). A domain author writes specifications and prompts only.
- **6.6 Test cases in the domain package. Done.** `Domain.test_cases` with `dry_run` flags; the runner takes `--domain` and `--cases`; DC reads the orchestrator's and the routed specialists' caps from the manifests, ME reads the specialists' scope terms, BVC reads the domain's response method.
- **6.7 A second domain. Done.** Public procurement under Directive 2014/24/EU: a coordinator and three specialists (supplies, services, works); the mixed supply-and-service contract (Art. 3) is the boundary object, encoded as a cap on the services specialist's `supply_share`; thresholds (Art. 4), lots (Art. 46), framework duration (Art. 33), subcontracting (Art. 71), conflict-of-interest screening (Art. 24) and sustainability criteria (Art. 67 and 68) are the other specifications; 19 specifications over 17 rule ids, one state predicate (committed budget share), twelve test cases including a mixed-contract decline, an aggressive-preset case and a state case. C1 to C3 hold by construction (`AI_INTENT_DOMAIN=procurement python evaluation/spec_consistency.py`), containment holds, the manifestation map is derived from the tags. First runs with llama3.1:8b: `paper2/generalisation-notes.md`.

**Decline path (done 9 October 2026).** Declines are scored under ME instead of CDA and SP when they name the constraint; the gate checks the typed content of a decline against prohibitions other than scope; the actionable-output rule is vacuous over declines only; specialists with state predicates receive the state in their sub-question. See `paper2/generalisation-notes.md`, section 5.

Open after 6.7: the specialist prompts (`json_instruction`) are still hand-written per specialist; generating the JSON example from the derived schema is the next step. The `recommendation` vocabulary is a domain field (`award | shortlist | reject | not_applicable` for procurement). The semantic checker's prompt still speaks of "investment" in two sentences.

Transfer conditions, from the ER 2026 paper: a sortal in-or-out boundary per agent, norms expressible as decidable prohibitions or obligations over fields, session-stable Mandates, and lexicographic priority of compliance over usefulness. Procurement satisfies all four; the mixed contract shows that the in-or-out boundary can itself be a numeric predicate.

## Dependency summary

| Item | Depends on | Enables |
|---|---|---|
| 1.1 State predicates (done) | – | TC-20, TC-21, SP dimension |
| 1.2 Structured outputs | – | 2.1 |
| 1.3 Defeasible norms | – | 3.3 |
| 2.1 ORM Mandates | 1.2 | 2.2, 3.2 |
| 2.2 Design-time checks | 2.1 | – |
| 3.1 Capable models | – | – |
| 3.2 Independent oracle | 2.1 (optional) | – |
| 3.3 Further domains | 1.3 | – |
| 6.3 to 6.7 Generalisation (done) | 1.2, 2.1 | 3.3, third paper |
