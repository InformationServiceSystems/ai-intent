# Response to Reviewers — Submission 40

**Title:** AI-Intent: A Conceptual Modeling Framework for Accountable Multi-Agent AI Systems
**Decision:** Conditionally accepted (ER'26)

We thank the Program Chairs and the three reviewers for their careful and
constructive assessment. Below we respond to each point and indicate the
corresponding change in the revised manuscript. Section/label references
are to the revised version (`ai-intent-er2026-v3.tex`). Reviewer wording
is paraphrased for brevity. The response is organized around the six
meta-review conditions (C1–C6), which the individual reviewer points map
into; explicit reviewer requirements not in the meta-review are grouped
under G.

---

## C1 — The nature and scope of the framework is not clear (R3.1, R2.2)

**R3.1 (nature of the artifact).** We now state explicitly, in a "Nature
and scope of the contribution" paragraph, that AI-Intent is **not** a new
modeling language nor a syntactic extension of one, but a
domain-independent **conceptual model / metamodel** — governance
constructs with their metamodel relationships and well-formedness
conditions — grounded in UFO and rendered in OntoUML, that *augments*
existing agent-oriented languages. The paper is reframed exactly as the
reviewer suggested: gap analysis of existing languages → additional
constructs that close the gaps. *§1 (Introduction); lead paragraph of §3.*

**R2.2 (Compliance Agent: framework vs. simplistic implementation).** We
separated the **framework-level requirements** on Intent Enforcement —
(R1) non-bypassability/totality, (R2) independence/externality, (R3)
decidable verdict with named violated constraint, (R4) terminating
revision — from the reference realization, and explicitly labeled the
deterministic checker a "deliberately minimal realization" that discharges
R1–R4. *§3.2 (Enforcement pillar); §4.1.*

## C2 — Ontological foundations insufficiently developed; unclear how UFO is used (R1.2, R1.3a–c)

**R1.2 ("sortal" not grounded).** We keep the term and ground it in its
ontological sense — grounded in Gupta's *The Logic of Common Nouns*
(1980) and Guizzardi (2005) — a sortal universal supplies a principle of
identity/individuation, explaining why the sortal reading, not a mere
subtype predicate, is the right one for the paraphrastic variation of
natural-language queries. *§3.1, "Intent scope as a sortal boundary."*

**R1.3a (dependent on UFO?).** New "Dependence on UFO" paragraph: AI-Intent
is UFO-**grounded** but not UFO-**dependent** — instantiating it requires
no UFO reasoner or UFO-based language at runtime; UFO supplies the
ontological justification, not a runtime prerequisite. *§3.1.*

**R1.3b (extent of UFO's contribution).** Rebuilt the mapping table
(**Table 2**) to do the job the reviewers asked of it: columns are
**Construct | UFO category / OntoUML stereotype | Src (derived/design) |
Realization in the reference implementation**, across all ten constructs
(Principal … Regulatory Framework). One table now answers R1.3b, carries
the OntoUML stereotypes for R3.3a, and shows the model's realization for
C5. *§3.1, Table 2.*

**R1.3c (which constructs are UFO-derived, and how would a non-UFO design
differ?).** The "Dependence on UFO" paragraph now names the **three
counterfactuals** a non-UFO design would plausibly have produced: (i)
Mandate as a goal-set rather than a normative description; (ii) the audit
trail as an infrastructure artifact rather than a derived situation; (iii)
messages permitted to exist without an attached verdict. The three
UFO-derived commitments are precisely what exclude these alternatives.
*§3.1.*

## C3 — Positioning with respect to related work is weak (R2.1, R3.2)

**R2.1 (missing trustworthy-agent state of the art).** New positioning
paragraph citing and differentiating the three works the reviewer supplied
— Verifiability-First Agents (arXiv:2512.17259), a unified
evaluation/governance TechRxiv preprint (DOI
10.36227/techrxiv.176799772.28164151), and an IEEE governance framework
— plus two more. We position AI-Intent as a *conceptual model* specifying
the constructs these runtime/policy/evaluation mechanisms leave implicit,
and note their complementarity. *§2.3.*
> **Action needed from authors:** the TechRxiv preprint title is confirmed
> (*A Unified Evaluation and Governance Framework for Trustworthy LLM
> Agents*, 2026), but its **author list** and the **title/authors of IEEE
> document 11485555** remain behind access controls and could not be
> verified externally; both bib entries are flagged `[to verify]` — please
> fill from your IEEE/TechRxiv access, or drop the IEEE entry (four other
> state-of-the-art citations already engage the literature).

**R3.2 (heterogeneous related work; identify truly-related work).** Added
(a) an explicit **selection criterion** as §2's opening: directly-related
work proposes *modeling constructs* for agent governance (§2.1);
implementation frameworks (§2.2) and AI-governance policy work (§2.3) are
surveyed as deployment substrate and normative context; (b) the conceded
**terminological distinction** (i\*/Tropos are goal-oriented; GAIA/NMAS
agent-oriented); (c) citations of **Alqithami** (AIES 2025) and **Pujari,
Goel & Sharma** (IJST 2024) with differentiation; and (d) **two new
columns in Table 1** — a **Trust. MAS** column (Alqithami's AAF +
verifiability-first agents) and an **AI-Intent** column — so the
differentiation is *shown*: the runtime trustworthy-agent frameworks have
audit-native communication but no declarative modeling constructs for
scope/prohibition/risk, while AI-Intent covers all eight capabilities.
*§2 opening, §2.1, §2.3, Table 1.*

## C4 — Lack of conceptual precision in the model (R3.3a–b, R2.3, R3.4)

**R3.3a (adopt OntoUML).** The conceptual model now carries OntoUML
stereotypes: they appear in Table 2 for every construct
(«kind»/«mode»/«event»/«situation»), and the diagram (Fig. 3) will show
them on the classes while retaining UML notation for accessibility, with a
note that a full OntoUML formalization is future work. *§3.1, Table 2;
Fig. 3.*

**R3.3b (cardinalities and attributes) / R2.3 (font too small).** The
conceptual-model figure will be redrawn with a cardinality on every
association (e.g., Agent 1→1 Mandate; Proposed Action 1→1 Compliance
Verdict; Accountability Trace 1→1..\* Log Entry) and typed attribute
compartments, at ≥8 pt final print size (splitting the figure if needed).
*Fig. 3 — figure production pending.*

**R3.4 (risk parameters ↔ predicates unclear; detailed example).** Two
changes: (a) the constraint triple ⟨text, φ, τ⟩ was **moved up** from
Limitations (§5.4) into the Mandate description in §3.2, where it belongs
— it was previously introduced for the first time inside Limitations,
which was the likely source of the confusion; (b) a **worked example**
now ties a risk parameter to a verdict: `max_allocation = 0.15` →
prohibition `F(allocation > 0.15)` → a Proposed Action at 0.18 → a
*blocked* Compliance Verdict, with an explicit cross-reference to the
figure. The risk parameter is stated to be the quantitative binding of the
free variable in φ, and a prohibition is violated *iff* a Proposed Action
*satisfies* φ. *§3.2 (Boundaries and worked example); §5.4 now recalls the
triple rather than introducing it.*

## C5 — Evaluation needs a fuller presentation and discussion of the model's role (R3.5a–d, R1.5)

**R3.5a (figure shows 2 agents not 4; how is the mandate represented?).**
The architecture figure (Fig. 4) will be redrawn to make the four agents
(Orchestrator + Stocks + Bonds + Materials) plus the interposed Compliance
Agent unambiguous, and to attach each sub-agent's Mandate visually. The
caption already enumerates the four agents and states the mandate
attachment. *Fig. 4 — figure production pending.*

**R3.5b (purpose of the validation).** New bridging paragraph opening §4
states the two evaluation questions and the method for each: expressiveness
(scenario-based comparison against the four baselines) and
operativity/applicability (can a model expressed in AI-Intent be
instantiated and enforced at runtime). *§4 (opening).*

**R3.5c (which requirements are tested; role of the model).** The bridge
now maps **each dimension to the framework claim it tests** (BVC/CGP →
Compliance Verdict gate; ME/CDA → Mandate boundary detection; ATC →
Accountability Trace population; DC → disposition-invariant enforcement)
and states explicitly that the evaluation tests the **model's operativity,
not the LLM's competence** — which reframes the sub-threshold ATC/CDA
results as findings rather than failures. *§4 (opening).*

**R3.5d (case study "constructed to confirm its premise").** One candid
paragraph concedes and bounds: this is a proof-of-concept in a designed
setting, and MiFID II was chosen precisely because its norms are
**externally specified and not authored by us**, which bounds the risk of
building the case around the solution. *§4 (opening).*

**R1.5 (auditability under-operationalized).** Added the trace
**derivation function** `T(s) = ⟨l₁…lₙ⟩` and two **well-formedness
conditions** (WFC-1: every Compliance Verdict is recorded in exactly one
Log Entry; WFC-2: a completed session's Trace has a Log Entry for every
cross-agent Proposed Action), plus the verifiable differences from
conventional logging: completeness by well-formedness, reconstructibility
(entries carry Mandate + constraint IDs), and negative evidence (blocked
actions are recorded). *§3.2, Pillar 3.*

## C6 — Generalizability to other domains should be clarified (R1.4b)

**R1.4b.** Retitled the passage **"Scope of validity and conditions for
transfer,"** separated the **domain-independent** core (metamodel, pillars,
well-formedness conditions) from **domain-specific** content (Mandate text,
predicate registry, risk parameters), and gave four transfer conditions —
including the **lexicographic-priority** condition (a compliant non-answer
must be acceptable, as in regulated finance but not in emergency triage) —
with an explicit "proof-of-concept pending replication" positioning and a
named next domain (clinical decision support). *§5 (Threats to Validity →
Scope of validity).*

---

## G — Explicit reviewer requirements and housekeeping

**R1.4a (predicate-consistency limitation assessed more directly).**
Enumerated the failure modes — over-restrictive φ → false block; under-
restrictive φ → silent false pass (which BVC structurally cannot detect);
mis-scoped φ → wrong rule ID — and stated candidly that the evaluation was
designed to **avoid** rather than **expose** this mode, since expected
rules were derived from the same Mandate definitions used to code the
predicates. We also **tie the four 14.8% gold borderline cases** (§4.3,
BVC) explicitly to the under-restrictive-φ class: the numeric predicate
`allocation > 0.15` is under-restrictive relative to the text's intent
that the cap not be circumvented, so a numerically-compliant but
circumvention-phrased response passes the gate — which is why post-hoc
human review, not the deterministic checker, surfaced them. *§5.4.*

**R1.6 (drafting tells / "demonstrates").** Swept the manuscript: reduced
"demonstrates," removed "Notably,", varied all four "the present
paper/work" instances, and reworded "a pattern that generalizes." *Global.*

**G.1 (consistency & overclaim).** Fixed the "and and" typo; softened the
§6 overclaim ("not merely convenient but necessary" → "external compliance
enforcement is needed rather than optional"). The 97.9% / 12.9% / 190-
session figures were checked for consistency across abstract, §1, §4, §5,
§6.

**G.2 (this document).** Response-to-conditions letter, organized by the
six meta-review conditions with reviewer points nested beneath.

---

## Preserved strengths (no change)

The motivation framing, the domain rationale, the internally-consistent
scoring methodology, and the headline result (97.9% boundary violation
containment across 190 sessions, zero forced-pass) are preserved through
the revision.

## Out-of-scope items (bounded in the text, not ignored)

- **More expressive predicate language** (SHACL/SMT-backed checking):
  noted as future work; the reference checker is now explicitly framed as a
  minimal realization of requirements R1–R4 (C1/R2.2).
- **Full OntoUML formalization** with UFO axioms and validated
  well-formedness constraints: noted as future work; stereotypes are given
  in Table 2 and on the diagram (C4/R3.3a).
- **Empirical replication in a second domain**: named (clinical decision
  support) with explicit transfer conditions (C6/R1.4b).
- **Predicate mutation testing**: named as the way to convert the
  specification-consistency limitation from mitigated to eliminated (G/R1.4a).

## Notes for the camera-ready

- **Figures (author action):** two figures to be produced — (1) the
  conceptual model in OntoUML with stereotypes/cardinalities/typed
  attributes at readable font (C4: R3.3a/b, R2.3), and (2) the reference
  architecture showing four agents + Compliance Agent + attached mandates
  (C5: R3.5a).
- **Two citations to verify:** the TechRxiv preprint authors/title and IEEE
  document 11485555 (C3/R2.1).
- **Page budget (16 pp max):** the current revision compiles to ~20–21 pp
  in our local TeX (the submission baseline is 17 pp in the same
  environment). A companion page-budget plan lists offsetting cuts that net
  the additions to ≤ 0 without sacrificing findings — most notably merging
  the two results tables (which also delivers C5's claim-next-to-result
  link), compressing the §5.1 restatement, and moving the CDA denominator
  footnote to the repository.
