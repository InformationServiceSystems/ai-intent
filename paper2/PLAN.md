# Follow-up paper: grounding AI-Intent governance in UFO

Working title: *Commitments, Dispositions and Traces: An Ontological Account of Accountable Delegation in Multi-Agent AI Systems*

Status: planning started 6 October 2026; complete draft with results of the second campaign on 7 October 2026 (`ai-intent-ufo.tex`, 14 pages LNCS, references from page 13). All three campaigns done (the third with deterministic routing); awaiting author review. The ER 2026 paper is frozen at tag `er2026-v1.0`; everything here builds on `main`.

## 1. Motivation

The ER 2026 paper uses the Unified Foundational Ontology (UFO) for one purpose: it categorises nine governance constructs and draws on the entailments of those categories at design time. Three questions that the ER 2026 paper raises remain unanswered by that use.

1. **Accountable to whom?** The Accountability Trace records what happened, but the model does not say who owes what to whom. Delegation from Principal to Orchestrator to sub-agents is represented structurally (`parent_mandate_id`), not as a normative relation.
2. **What is a disposition, formally?** The disposition presets are prompt injections and the metric Disposition Containment is a score. The model does not say what it means for a disposition to be manifested, or how a manifestation is attributed.
3. **Can a regulator query a trace without reading Python?** The trace is a JSON export whose integrity conditions are enforced by scoring functions in the evaluation runner. Nothing lets an auditor state an invariant and check it over sessions.

UFO-C (social ontology), UFO-A/B (dispositions and events) and gUFO (the OWL rendering of UFO) answer these three questions. The follow-up paper uses them substantively, not only for categorisation.

## 2. Research questions

- **RQ1 (Delegation).** Can delegation in AI-Intent be modelled as a chain of UFO-C commitment and claim pairs such that mandate containment (a sub-mandate never grants more than its parent) is checkable at design time, and every runtime breach resolves to an answerable party?
- **RQ2 (Dispositions).** Can agent dispositions be modelled as UFO dispositions with bearer, degree, triggering situation and manifestation, such that a compliance rejection can be attributed to a disposition deterministically, and does the attribution agree with the preset that produced it?
- **RQ3 (Traces).** Can an Accountability Trace be exported as a gUFO-typed graph over which the framework's integrity invariants are stated as SPARQL queries, and do the 190 sessions of the ER 2026 evaluation satisfy them?

## 3. Contributions

1. A UFO-C account of delegation in AI-Intent: Delegation as a relator constituted by a Commitment (an extrinsic mode of the delegatee, externally dependent on the delegator) and its Claim. A containment condition over the chain, and an accountability resolution that maps a breach to the chain of answerable parties up to the Principal.
2. A UFO account of agent dispositions: Disposition as an intrinsic mode with degree, triggering situation and a characteristic rule set; a manifestation is a rejection or block whose violated rules intersect that set. This turns the ER 2026 metric Disposition Containment into a statement about dispositions, manifestations and the gate.
3. A gUFO export of sessions and eight integrity checks as SPARQL queries. The checks replace scoring heuristics with invariants a regulator can read and extend.
4. Two corrections to the ER 2026 grounding that the formalisation exposes: (a) a Compliance Verdict cannot be a mode of a Proposed Action, because modes inhere in endurants and a Proposed Action is an event; the verdict inheres in the target agent and historically depends on the action. (b) The "derived" versus "design" column should distinguish constructs whose formal behaviour the UFO category fixes completely from constructs the framework fills with content; all nine assignments are choices.

## 4. Mapping to the implementation

| Theme | Module | Log methods | Status |
|---|---|---|---|
| Delegation | `agents/delegation.py` | `delegation.establish`, `delegation.breach.{agent}` | implemented, tested |
| Dispositions | `agents/dispositions.py` (constructs section) | `disposition.manifest.{agent}` | implemented, tested |
| Traces | `mcp/gufo_export.py`, `evaluation/sparql_checks.py` | reads the log only | implemented, tested |
| Orchestrator hooks | `agents/orchestrator.py` | emits the three methods above | implemented |
| Domain package and generic specialist (ROADMAP 6, steps 1 and 2) | `agents/domain.py`, `agents/specialist.py`, `domains/finance.py` | README, ROADMAP 6 | done 8 Oct 2026, behaviour unchanged |
| Roles instead of names, dispositions over tags, schemas from specs, test cases in the domain (ROADMAP 6.3 to 6.6) | `agents/domain.py`, `agents/compliance.py`, `agents/dispositions.py`, `agents/schemas.py`, `evaluation/runner.py --domain` | `tests/test_generalisation.py` | done 9 Oct 2026; finance manifestation map and schemas reproduced exactly |
| Second domain: public procurement, Directive 2014/24/EU (ROADMAP 6.7) | `domains/procurement.py` | `tests/test_procurement_domain.py`, `paper2/generalisation-notes.md` | done 9 Oct 2026; 19 specs, 12 cases, C1 to C3 hold, dry run with llama3.1:8b |
| State predicates: drift and concentration against a session state (ROADMAP 1.1) | `agents/constraint_spec.py` (`drift`, `state_max`), `agents/compliance.py`, `state.snapshot` log method | `tests/test_state_predicates.py`, TC-20, TC-21, dimension SP | done 9 Oct 2026 |
| Accountability note as a projection of the trace (ROADMAP 4) | `agents/accountability.py` | ATC no longer depends on instruction following | done 9 Oct 2026 |
| Structured outputs for all constraints (ROADMAP 1.2) | `agents/stocks.py`, `agents/materials.py`, `agents/compliance.py`, `agents/constraint_spec.py` | `tests/test_structured_constraints.py` | done 8 Oct 2026 |
| Constraints as a single source (ConstraintSpec) | `agents/constraint_spec.py`; manifests and registry generated from it | ROADMAP 2.1, `paper2/spec-consistency.md` | done 8 Oct 2026; C1 to C3 hold by construction |
| Specification-predicate consistency check C1 to C4 | `evaluation/spec_consistency.py`, `tests/test_spec_consistency.py` | `paper2/spec-consistency.md` | done 8 Oct 2026; 2 proxy predicates remain, ORM assessed |
| Accountability tab in the UI | `ui/accountability_panel.py` | chain, breaches, manifestations, Q1 to Q9 per session | done 8 Oct 2026 |
| OntoUML model, verified and transformed to gUFO | `ontology/ontouml/` (`build_model.js`, `.ontouml.json`, `.gufo.ttl`, `verification.json`), `evaluation/ontouml_alignment.py` | README in `ontology/ontouml/` | done 8 Oct 2026, 0 verification issues, 13/13 constructs aligned |
| Q9, OWL-RL consistency against gUFO | `evaluation/gufo_consistency.py`, `evaluation/ontology/gufo.ttl` | `paper2/q9-gufo-consistency.md` | done 8 Oct 2026, 0 inconsistent graphs in campaigns 1 and 2 |
| Third campaign, deterministic routing (10 runs, HPC) | `evaluation/ufo_hpc3_*`, `evaluation/sessions/ufo_hpc3_*` | `paper2/e2-e3-results-run3.md`, `paper2/e2-e3-notes-run3.md` | done 7 Oct 2026, ME 80.0% |
| First full campaign (10 runs, HPC) | `evaluation/ufo_hpc_p*_results_*.json`, `evaluation/sessions/ufo_hpc_*` | `paper2/e2-e3-results.md`, `paper2/e2-e3-notes.md` | done 7 Oct 2026 |
| Runner persistence and E2/E3 fields | `evaluation/runner.py`, `evaluation/paper2_analysis.py` | writes `evaluation/sessions/*.json|ttl`, `paper2/e2-e3-results.md` | implemented, dry run passed |
| Verdict provenance | `agents/compliance.py` | `message_id` now names the evaluated action | implemented |

The export reads nothing but the MCP log, in keeping with the invariant that the log is the source of truth. Delegation chains, dispositions and manifestations therefore appear in the graph only if the orchestrator logged them, which is itself an auditable fact.

## 5. Evaluation design

- **E1, containment at design time.** Mutate each numeric sub-mandate parameter above its parent bound and show that `check_chain_containment` reports it before any session runs. Deterministic; no LLM.
- **E2, attribution agreement.** Re-run TC-16 to TC-19 (four presets, ten runs) with the hooks active. For each rejection, compare the attributed disposition kinds with the preset in force. Report precision (attributed kinds whose degree in the preset is at or above threshold) and the share of rejections left unattributed. Under the neutral preset the expected attribution rate is zero.
- **E3, invariants over fresh sessions.** The MCP logs of the 190 ER 2026 sessions were not preserved: the result files hold scores and session ids only, and the database no longer contains those sessions (see `e3-archive-checks.md` for the 21 sessions that remain). The runner therefore now persists every session's log and gUFO graph under `evaluation/sessions/` and runs the eight checks per session; E3 reports per-check pass rates over the regenerated suite (19 cases, several runs). The 21 remaining archived sessions serve as the before-hooks comparison.
- **E4, cost.** Graph size and query time per session, to show the export is practical.

## 6. Paper structure

1. Introduction: the three open questions and the claim that UFO answers them.
2. Background: UFO-A/B/C in the extent needed; gUFO; AI-Intent summary with the nine constructs.
3. Delegation as commitment and claim (RQ1).
4. Dispositions and their manifestation (RQ2).
5. Traces as gUFO situations and integrity queries (RQ3).
6. Reference implementation and evaluation (E1 to E4).
7. Related work: UFO-C and commitments (Guizzardi, Nardi), delegation in Tropos and GAIA, norm ontologies (LegalRuleML, ODRL), provenance (PROV-O) as the natural comparison for the trace export.
8. Discussion, corrections to the ER 2026 grounding, limitations, conclusion.

## 7. Open decisions for the author

- Target venue: **ER 2027** (decided 7 October 2026). LNCS, 14 pages plus references, same format as the ER 2026 paper.
- Whether to align `aii:` with PROV-O (`prov:Activity`, `prov:wasInformedBy`) in addition to gUFO. Alignment widens tool support; it also lengthens the paper.
- Whether E2 should use llama3.1:8b for continuity with ER 2026, or a more capable model so that rejections are rarer and attribution is tested on harder cases.
- Decided 7 October 2026: a third campaign with deterministic routing for the evaluation (ROADMAP item 4) runs after the paper draft is written, not before. The override is implemented (commit 637c61c): `run_parallel.py --deterministic-routing --prefix ufo_hpc3`; it waits for the author's review of the draft.

## 8. Risks

- gUFO has no class for normative descriptions. Mandate is exported as `gufo:Object`, which is defensible but weak. The paper must state this and may propose `aii:Mandate` as a subclass with a documented reading.
- Attribution by rule set is a modelling decision. The rule sets per disposition kind (`MANIFESTATION_MAP`) need a justification in the paper and a sensitivity check in E2.
- The archived sessions lack the new log methods. E3 must separate what the export can show on old data from what it shows on new data.
