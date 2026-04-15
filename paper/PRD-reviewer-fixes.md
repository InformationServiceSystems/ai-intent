# PRD: Reviewer Assessment Fixes for AI-Intent Paper

## Context

A senior reviewer assessment of `ai-intent-er2026-v2.tex` identified 10 issues. This PRD addresses each with a specific fix. Issues are ordered by priority. Some reviewer observations are based on a prior version and do not apply to the current file — those are noted.

---

## Issue 1 — Internally Inconsistent Figures (CRITICAL)

### Problem

The reviewer sees three numbers that appear contradictory:
- 25.6% of "all sessions" had first-attempt violations (necessity argument)
- 12.9% neutral violation rate (13 of 101 sessions)
- 72 of 110 CDA-applicable sessions had violations (CDA section)

The reviewer expects these to be drawn from the same universe of 190 sessions. They are not — they measure different things on different subsets:

- **Self-compliance** counts sessions where the materials agent was consulted (129 sessions across all TCs and presets) and checks whether the first response exceeded the 15% cap.
- **CDA conditioned** counts sessions where CDA is a scored dimension (110 sessions across 11 CDA-applicable TCs) and checks whether any compliance rejection occurred (revisions > 0 or violated rules found).

These are consistent but the paper does not explain the different denominators.

### Fix

In Section 3.3 (necessity argument), add the denominator explicitly:

**Before:**
> the materials agent violated its 15% allocation cap on first attempt in 25.6% of all sessions

**After:**
> the materials agent violated its 15% allocation cap on first attempt in 25.6% of the 129 sessions in which it was consulted

In Section 5.2 (CDA interpretation), clarify the denominator:

**Before:**
> Conditioned on violation-occurring sessions only (72 of 110 CDA-applicable sessions across 10 runs)

**After:**
> Conditioned on violation-occurring sessions only (72 of 110 sessions where CDA is a scored dimension across 10 runs — a subset that excludes test cases with no expected violations and test cases where CDA is not applicable)

Add a footnote after the first mention of CDA conditioned:

> The CDA and self-compliance denominators differ because CDA is scored only on test cases with expected constraint violations or where violations were detected, while self-compliance is measured across all sessions involving the materials agent regardless of test case category.

### File to edit
`paper/ai-intent-er2026-v2.tex`, lines 505-512 and 1052-1066

---

## Issue 2 — Metamodel Arrow Direction Error

### Problem

Well-formedness condition 2 says MCPMessage has exactly one ComplianceVerdict (verdict is part of message). But the TikZ arrow goes from Verdict to Message labeled "produced for [1..1]", which reads as an association from Verdict to Message, not a composition of Verdict inside Message.

### Fix

Change the arrow to a composition from Message to Verdict:

**Before (line ~394):**
```latex
\draw[rel] (verdict) to[bend right=20]
    node[right, font=\scriptsize] {produced for [1..1]}
    (message);
```

**After:**
```latex
\draw[fcomp] (message) to[bend left=20]
    node[left, font=\scriptsize] {has [1..1]}
    (verdict);
```

This makes Message the composite and Verdict the component, matching the well-formedness condition. The filled diamond (`fcomp`) on the Message end shows composition.

### File to edit
`paper/ai-intent-er2026-v2.tex`, TikZ figure at lines 335-399

---

## Issue 3 — Orchestrator-ComplianceAgent Relationship Not Modeled

### Problem

The metamodel has no explicit relationship between the Orchestrator and ComplianceAgent. The protocol describes their interaction but the formal model omits it.

### Fix

Add a new node `Orchestrator` to the metamodel as a specialization of Agent, with a dependency arrow to ComplianceAgent labeled "invokes [1..1]". This is minimal and consistent with the protocol.

Add to the TikZ figure:
```latex
\node[class, above=0.9cm of agent] (orch) {\textbf{Orchestrator}};
\draw[rel] (orch) -- node[right, font=\scriptsize] {is-a} (agent);
\draw[dep] (orch) to[bend left=25]
    node[above, font=\scriptsize] {invokes [1..1]}
    (compliance);
```

Update the caption to mention the Orchestrator.

### File to edit
`paper/ai-intent-er2026-v2.tex`, TikZ figure at lines 335-399

---

## Issue 4 — Orphaned Bibliography Entry

### Status: NOT APPLICABLE

The reviewer claims `bai2022constitutional` is in the bibliography but not cited. This entry does not exist in the current file. The two previously orphaned entries (`mylopoulos1992conceptual`, `olivePMD07`) were already removed. No action needed.

---

## Issue 5 — Gap 3 Audit Log Literature

### Problem

The paper claims communication-as-evidence is a modeling gap but does not engage with existing audit log patterns (OMG standards, enterprise architecture audit trails).

### Fix

Add 2-3 sentences to Section 2.3 (AI Governance and Accountability) acknowledging enterprise audit patterns and distinguishing AI-Intent's approach:

> Enterprise architecture standards (e.g., OMG's audit trail patterns) and compliance logging in SOA systems provide audit logging as an infrastructure service. However, these treat the audit log as an operational artifact external to the system model: it records what happened but is not a first-class element of the metamodel that constrains system behavior. In AI-Intent, the accountability trace is a structural model component: its existence is a well-formedness condition (WFC-3), and the compliance verdict attached to each message is a metamodel relationship, not a log entry. This distinction — between logging as infrastructure and communication-as-evidence as a metamodel property — is the modeling gap we address.

No new citation needed — this is a conceptual distinction, not a literature survey claim.

### File to edit
`paper/ai-intent-er2026-v2.tex`, after line 261

---

## Issue 6 — DC Variance Makes Metric Unreliable

### Problem

DC_c has std 40.5% and range 0-100%, indicating a binary per-run outcome. The reviewer correctly notes this is not a useful metric.

### Fix

Replace DC_c with a simpler, more defensible claim. Remove the DC_c row from Table 4 (results). Replace the DC interpretation paragraph with:

> **DC (disposition containment).** The policy-relevant disposition containment property is binary: did any adversarial preset produce a `forced_pass`? Across all 40 disposition test evaluations (4 presets × 10 runs), zero `forced_pass` events occurred. The `reckless_portfolio` preset — which explicitly instructs agents that constraints are guidelines overridable by compelling rationale — consistently triggered compliance revisions but never breached the compliance gate. Under the strict rubric (DC_s = 57.5%), adversarial presets require 2-5× more revisions than neutral, reflecting increased compliance effort without containment failure.

This reports the actual evidence (zero forced_pass) rather than a heuristic-based percentage with meaningless variance.

### File to edit
`paper/ai-intent-er2026-v2.tex`, lines 1017 (remove DC_c row), 1075-1090 (rewrite DC paragraph)

---

## Issue 7 — Missing Liveness Property

### Problem

The protocol states the safety property but not liveness: if a message is compliant, will it eventually be delivered?

### Fix

Add after the Safety paragraph (line 577):

> **Liveness (conditional):** If the constrained agent $a$ produces a response $\mu$ such that $\mathit{eval}_D(\mu) = \mathit{pass}$ for all applicable rules, then $\mu$ is delivered in step (2) without revision. Liveness is \emph{conditional} on the agent's ability to produce a compliant response: the protocol guarantees delivery for compliant messages but intentionally does not guarantee delivery for messages that remain non-compliant after $\mathit{maxRev}$ revisions.

### File to edit
`paper/ai-intent-er2026-v2.tex`, after line 577

---

## Issue 8 — Missing Guardrails Discussion

### Status: PARTIALLY APPLICABLE

The reviewer claims the bibliography includes `rebedea2023nemo` and `dong2024guardrails` — these do NOT exist in the current file. However, the reviewer's point about missing guardrails discussion is valid: the paper should position against LLM guardrail systems.

### Fix

Add a paragraph to Section 2.4 (Multi-Agent LLM Architectures):

> LLM guardrail systems such as NeMo Guardrails~\cite{rebedea2023nemo} and Constitutional AI~\cite{bai2022constitutional} address output safety for individual models through input/output filtering and self-critique. These systems enforce constraints on single-agent outputs but do not model inter-agent accountability: they cannot trace a multi-agent decision to its constituent sub-agent outputs, do not maintain compliance histories across revision cycles, and do not produce structured audit artifacts. AI-Intent's compliance agent shares the guardrails motivation (constraint enforcement on stochastic outputs) but operates at the multi-agent communication level rather than the single-model output level.

Add the bibliography entries:

```latex
\bibitem{rebedea2023nemo}
Rebedea, T., Dinu, R., Sreedhar, M., Parisien, C., Cohen, J.:
NeMo Guardrails: A toolkit for controllable and safe LLM applications
with programmable rails.
In: Proc.\ EMNLP 2023 System Demonstrations, pp.~431--445 (2023)

\bibitem{bai2022constitutional}
Bai, Y., Kadavath, S., Kundu, S., et al.:
Constitutional AI: Harmlessness from AI feedback.
arXiv preprint arXiv:2212.08073 (2022)
```

### File to edit
`paper/ai-intent-er2026-v2.tex`, after line 273 (new paragraph) and bibliography section

---

## Issue 9 — Necessity Argument Step 4 Unsupported

### Problem

Step 4 claims self-evaluation is subject to the same stochasticity but provides no citation. The Huang et al. (2023) citation was present in an earlier version but removed.

### Fix

Restore the citation. Add to the end of Step 4 (line 499-500):

**Before:**
> The agent whose output is being evaluated cannot be the evaluator: self-evaluation is subject to the same stochasticity as the original output.

**After:**
> The agent whose output is being evaluated cannot be the evaluator: self-evaluation is subject to the same stochasticity as the original output~\cite{huang2023selfcorrect}. Huang et al. show that LLMs cannot reliably self-correct reasoning without external feedback, supporting the claim that self-evaluation accuracy does not exceed generation accuracy.

Add bibliography entry:

```latex
\bibitem{huang2023selfcorrect}
Huang, J., Gu, S.S., Hou, L., Wu, Y., Wang, X., Yu, H., Han, J.:
Large language models cannot self-correct reasoning yet.
arXiv preprint arXiv:2310.01798 (2023)
```

### File to edit
`paper/ai-intent-er2026-v2.tex`, lines 498-500 and bibliography section

---

## Issue 10 — Materials Table Missing Inflation Rationale Obligation

### Problem

Table 2 shows three F-constraints for Materials but omits the O(inflation rationale) obligation that appears as `MANIFEST_MATERIALS_INFLATION` in the evaluation.

### Fix

Add the fourth constraint to the Materials row in Table 2:

**Before (line 790-793):**
```latex
Materials & Commodities & 5 & 4 &
    $\mathbf{F}$(\textit{non-Au/Ag commodity});
    $\mathbf{F}$(\textit{allocation} $> 15\%$);
    $\mathbf{F}$(\textit{leveraged ETF/futures}) \\
```

**After:**
```latex
Materials & Commodities & 5 & 4 &
    $\mathbf{F}$(\textit{non-Au/Ag commodity});
    $\mathbf{F}$(\textit{allocation} $> 15\%$);
    $\mathbf{F}$(\textit{leveraged ETF/futures});
    $\mathbf{O}$(\textit{inflation rationale}) \\
```

### File to edit
`paper/ai-intent-er2026-v2.tex`, lines 790-793

---

## Execution Order

1. **Issue 1** (figures consistency) — editorial fix, no computation needed
2. **Issue 2** (metamodel arrow) — TikZ edit
3. **Issue 3** (orchestrator node) — TikZ edit (combine with Issue 2)
4. **Issue 6** (DC metric) — remove DC_c row, rewrite paragraph
5. **Issue 7** (liveness) — add paragraph
6. **Issue 9** (necessity citation) — add citation + bibentry
7. **Issue 8** (guardrails) — add paragraph + 2 bibentries
8. **Issue 5** (audit log) — add sentences
9. **Issue 10** (materials table) — add constraint to table row
10. Verify: no new orphaned references, all cross-refs valid

Issues 4 is not applicable. Issues 2+3 should be done together (same TikZ figure).

---

## What NOT to Do

- Do not rerun evaluations — the data is correct, just under-explained
- Do not change the CDA or self-compliance computation — the numbers are consistent
- Do not add a full guardrails survey — 1 paragraph positioning is sufficient
- Do not change the BVC or CGP results — those are empirically sound
- Do not restructure the paper — the reviewer said "minor revision (borderline accept)"
