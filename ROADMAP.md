# Roadmap

This document lists the planned development of AI-Intent beyond the ER 2026 reference implementation. It follows the three tracks named in the paper's conclusion (modeling, ontological, empirical) and adds the concrete engineering items that the evaluation and the paper's limitations call for. Items are ordered by dependency, not by priority; an item marked *depends on* cannot start before the named item is done.

## 1. Modeling track

### 1.1 Fourth predicate template: state predicates

**Status:** planned. **Motivation:** the Materials Mandate's rebalancing trigger ("flag to orchestrator if allocation drifts more than ±5% from target") is the only boundary constraint without a predicate. The Compliance Agent has no access to portfolio state, so the trigger is an agent obligation that the gate cannot verify (Amendment 4). The same gap prevents any constraint that compares a proposed action with the current position: drift limits, concentration after the trade, cumulative exposure across agents in one session.

**Scope:**

- Add a `Predicate` kind `state_threshold` alongside `max_threshold`, `forbidden_term` and `required_term`. It compares an extracted value of the proposed action with a value read from a **session state** object, bound through two keys: `risk_param_key` for the limit (as today) and `state_key` for the reference value (for example `current_allocation.materials` or `target_allocation.materials`).
- Introduce a minimal, explicit `PortfolioState` model (current allocation per asset class, target allocation, session timestamp) that the orchestrator holds for the session and passes to the Compliance Agent. The state is part of the Accountability Trace: every Log Entry that evaluates a state predicate references the state snapshot it used, so an auditor can reproduce the verdict.
- Encode the rebalancing trigger as `O(|proposed − target| ≤ rebalance_drift_threshold ∨ flagged)`: the obligation is satisfied if the drift is within the threshold, or if the agent's output carries the flag. This keeps the constraint an agent obligation while making it checkable.
- Extend the evaluation suite with test cases whose expected violations depend on state (drift beyond threshold without flag; concentration breach only after the proposed trade), and add the rule IDs to the scorer's expected sets.

**Acceptance:** the Materials Mandate has five predicates; the trace records the state snapshot per verdict; the new test cases score deterministically.

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

**Status:** planned. Repeat the 19-case, 10-run evaluation with models whose instruction following is not the limiting factor, to separate the structural guarantees of the gate from the model-dependent dimensions (ATC, CDA, revision quality). The expectation to be tested is that trace completeness rises and detection latency falls while containment stays at the current level.

### 3.2 Independent verification of specification-to-predicate consistency

**Status:** planned. The evaluation's expected rule IDs and the enforced predicates share provenance. Introduce an independent oracle, either a second encoding of the Mandates by a different author or the ORM-generated constraints of 2.1, and measure agreement between the two encodings on the 190 sessions. Disagreements are miscodings by construction.

### 3.3 Further domains

**Status:** research. Candidates must satisfy the transfer conditions stated in the paper: a sortal in-or-out-of-scope boundary, norms expressible as decidable prohibitions, session-stable Mandates, tolerance for lexicographic constraint priority. Clinical decision support fails the exception condition and is therefore a test of 1.3 rather than of the core; procurement and public tendering are closer candidates.

## 4. Platform items

- **Deterministic routing for evaluation.** Done 7 October 2026 (`runner.py --deterministic-routing`): the harness fixes the routing to the test case's expected agents; the override is logged and still passes the routing checkpoint. ME is reported without the override (campaigns one and two) and with it (campaign three, pending).
- **Accountability note as a projection of the trace.** Generate the human-readable accountability note from the Accountability Trace rather than asking the model to write it, so that trace completeness (ATC) no longer depends on instruction following.

## 5. Follow-up paper: substantive use of UFO

**Status:** in progress since 6 October 2026. Plan and paper skeleton under `paper2/`. The ER 2026 paper uses UFO for categorisation only; the follow-up uses three parts of UFO as model content.

- **5.1 Delegation as commitment and claim (UFO-C).** `agents/delegation.py` builds the chain Principal to central to sub-agents as relators constituted by a Commitment and a Claim, checks that each sub-mandate is contained in its parent, and resolves a forced block to the chain of answerable parties. Logged as `delegation.establish` and `delegation.breach.{agent}`.
- **5.2 Dispositions as model constructs (UFO-A/B).** `agents/dispositions.py` adds Disposition (bearer, degree, triggering situation, characteristic rule set) and attributes rejections to dispositions deterministically. Logged as `disposition.manifest.{agent}`.
- **5.3 Traces as gUFO graphs.** `mcp/gufo_export.py` exports a session as a gUFO-typed RDF graph from the log alone; `evaluation/sparql_checks.py` states eight integrity invariants as SPARQL queries. Run with `python evaluation/sparql_checks.py --all`.

Two full campaigns ran on 7 October 2026 (`evaluation/ufo_hpc*_results_*.json`, notes under `paper2/`). The paper draft is at `paper2/ai-intent-ufo.tex`. Next: a third campaign with deterministic routing for the evaluation (item 4) after the draft is reviewed.

*Depends on* nothing in sections 1 to 4; *relates to* 2.2, which the gUFO export makes concrete.

## 6. Generalisation to other domains

**Status:** steps 1 and 2 done 8 October 2026. The kernel reads a `Domain` object (`agents/domain.py`); the finance domain is the first package (`domains/finance.py`); the three specialist modules are bindings of one generic specialist (`agents/specialist.py`). Behaviour on the finance domain is unchanged (test suite and dry run).

Remaining steps, in order:

- **6.3 Roles instead of names.** The gate and the orchestrator still refer to `central`, `stocks`, `bonds`, `materials` in the routing check, the synthesis check, the disposition-integrity checks and the runner's DC scorer. Replace by roles read from the manifests (`composite` for the synthesis role, `decision_right` for specialists) and by thresholds read from the risk parameters.
- **6.4 Dispositions over constraint tags.** `MANIFESTATION_MAP` names finance rule ids. Give each `ConstraintSpec` tags (`cap`, `leverage`, `disclosure`, `scope`, `quality_floor`) and map disposition kinds to tags, so attribution is valid in any domain.
- **6.5 Response schemas from specs.** Derive each specialist's response model from the `structured_field` and `item_key` declarations of its specs, so a domain author writes specifications only.
- **6.6 Test cases in the domain package**, with scorers reading thresholds from manifests.
- **6.7 A second domain** as the proof: public procurement (CPV categories, thresholds, lot rules, a boundary object such as mixed supply-and-service contracts), roughly ten specifications, run through the same suite and invariants. This is the empirical core of a third paper (3.3).

Transfer conditions, from the ER 2026 paper: a sortal in-or-out boundary per agent, norms expressible as decidable prohibitions or obligations over fields, session-stable Mandates, and lexicographic priority of compliance over usefulness.

## Dependency summary

| Item | Depends on | Enables |
|---|---|---|
| 1.1 State predicates | – | state-dependent test cases |
| 1.2 Structured outputs | – | 2.1 |
| 1.3 Defeasible norms | – | 3.3 |
| 2.1 ORM Mandates | 1.2 | 2.2, 3.2 |
| 2.2 Design-time checks | 2.1 | – |
| 3.1 Capable models | – | – |
| 3.2 Independent oracle | 2.1 (optional) | – |
| 3.3 Further domains | 1.3 | – |
