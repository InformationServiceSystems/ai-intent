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

**Status:** planned. **Motivation:** the two term-based templates check prose with regular expressions and synonym lists. They produce the false positives of Limitation 4 and miss anything outside their vocabulary (a commodity such as lithium passes "Gold and Silver only"). The percent template already prefers the structured `proposed_allocation` field and falls back to prose only when it is absent.

**Scope:** require typed fields in every sub-agent response (`proposed_allocation`, `instrument_type`, `commodity`, `credit_rating`, `duration_years`, `esg_assessment`, `inflation_rationale`) and evaluate predicates on those fields first. Prose extraction remains as a logged fallback with a `source: prose` marker in the verdict, so the trace shows which path produced each verdict. *Depends on* nothing; *enables* 2.1.

### 1.3 Defeasible norms and session-mutable Mandates

**Status:** research. The constraints have no exception structure and Mandates are immutable within a session; both are deliberate for regulated finance. Extending the model to defeasible deontic logic (a prohibition that a stronger norm can override) and to Mandates that a Principal may amend during a session, with the amendment itself logged as a governance event, widens the class of domains the model transfers to.

## 2. Ontological track

### 2.1 Mandate modeling with Object-Role Modeling (ORM)

**Status:** planned. **Motivation:** the paper's most important limitation is specification-to-predicate consistency. Each boundary constraint is a triple of text, predicate and deontic type, but text and predicate are authored separately and nothing checks that they agree. A cap written as "15%" in the text and coded as `> 0.20` in the predicate is enforced silently, and the containment metric cannot detect it because no rule fires.

ORM addresses this at design time, with three properties the current encoding lacks:

- **Single source for text and predicate.** ORM tools verbalize every constraint in controlled natural language from the formal constraint. The sentence that goes into the agent's system prompt is then derived from the constraint the gate evaluates, not written beside it.
- **Deontic modality is built in.** ORM 2 distinguishes alethic constraints, which a population cannot violate, from deontic constraints, which it can and which are verbalized as "It is forbidden that" or "It is obligatory that". This is the deontic type τ ∈ {F, O} of the triple, with the same semantics the Compliance Agent applies: a deontic constraint is checkable but violable, and a violation is recorded.
- **Value, subset and exclusion constraints with formal semantics.** "allocation ≤ 0.15", "commodity ∈ {Gold, Silver}", "rating ≥ BBB+" become first-class constraints on fact types, replacing regular expressions over prose.

**Scope:**

- Model the content of each Mandate as an ORM schema: fact types over the structured output fields of 1.2 (Proposed Action recommends allocation of Value to AssetClass; Proposed Action names Commodity; …) with value constraints bound to the Mandate's risk parameters and deontic modality per constraint.
- Treat each Proposed Action as a candidate population of that schema. The predicate φᵢ is the violation check of constraint i against that population; the Compliance Agent becomes an ORM constraint checker over a single-action population.
- Generate `text`ᵢ by ORM verbalization and use it in `manifest_to_system_prompt()`. Keep a provenance field on each `BoundaryConstraint` that records the ORM constraint it was generated from.
- Keep OntoUML for the governance metamodel (Principal, Agent, Mandate, Proposed Action, Intent Enforcement, Compliance Verdict, Log Entry, Accountability Trace). ORM models the content of a Mandate, OntoUML the relationships between governance constructs; the paper must justify the two notations by this division of labour.
- Evaluate by construction: show that the miscoding class of Limitation 2 (text and predicate disagree) cannot arise when text is derived from the constraint, and measure the false-positive rate of the term checks before and after replacing them with value constraints.

*Depends on* 1.2. Tooling candidates: NORMA for modeling and verbalization; SBVR as the verbalization standard closest to regulatory text (MiFID II) if the verbalizations are to be reviewed by compliance staff.

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

- **Deterministic routing for evaluation.** The orchestrator routes non-deterministically, which leaves Mandate Enforcement (ME) untestable in sessions where the target agent is not invoked. Add a routing override for the evaluation runner so that out-of-scope test cases always reach their target agent, and report ME both with and without the override.
- **Accountability note as a projection of the trace.** Generate the human-readable accountability note from the Accountability Trace rather than asking the model to write it, so that trace completeness (ATC) no longer depends on instruction following.

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
