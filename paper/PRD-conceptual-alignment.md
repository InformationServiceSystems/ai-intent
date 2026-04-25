# PRD: Conceptual-Model Alignment for AI-Intent

## Context

A re-analysis of the 13-concept AI-Intent conceptual model against the
current implementation surfaced five remaining gaps after the
`principal_id`, `decision_right`, and `uncertainty_policy` changes
landed. Two are code gaps (the framework declares a concept but does
not enforce it; a default that produces audit noise). Three are
conceptual-definition gaps (the model claims properties the
implementation does not — and arguably should not — provide). This PRD
specifies the fixes for both halves so the paper, the conceptual
model, and the running system describe the same artifact.

The five items below are independent and can land in any order.

---

## Item 1 — Enforce Decision Right (code)

### Problem

`AgentManifest.decision_right` is now a typed `Literal["execute",
"recommend", "advise", "enforce"]` field, surfaced in each agent's
system prompt. But the compliance gate has no rule that checks it.
An `advise`-tier agent (e.g. the central orchestrator) could in
principle emit an `execute`-shaped allocation ("buy 10% AAPL now")
and the gate would not flag it as a decision-right violation. The
concept is declared but not enforced — the audit trail records what
each agent said, not whether it overstepped its authority.

### Fix

Add a regulatory rule and a deterministic check.

**File: `agents/regulatory_rules.py`**

Add to the registry:

```python
RegulatoryRule(
    rule_id="MANIFEST_DECISION_RIGHT_RESPECTED",
    description=(
        "An agent must not emit content that exceeds its decision_right. "
        "advise: may opine but not propose unilateral actions. "
        "recommend: may propose actions but not execute them. "
        "enforce: gates other agents and does not produce its own actions. "
        "execute: not used in this prototype."
    ),
    applies_to=["central", "stocks", "bonds", "materials", "compliance"],
    check_type="both",
    severity="block",
    regulatory_basis=["AgentManifest.decision_right"],
),
```

**File: `agents/compliance.py`**

Add a deterministic checker invoked during routing (CP1), analysis
(CP2), and synthesis (CP3) checkpoints. Match against:

- For `advise`: detect imperative trade verbs without a synthesis
  framing ("buy", "sell", "execute", "place order") in the
  `final_recommendation` or `analysis` field. *Quantified guidance
  remains permitted* — this rule targets unilateral action, not
  numeric specificity (the existing
  `MANIFEST_CENTRAL_ACTIONABLE_OUTPUT` rule covers specificity).
- For `recommend`: detect language claiming the action has been or
  will be taken by the agent itself ("I have placed", "I will
  execute", "order submitted").
- For `enforce`: the compliance agent never emits `recommendation`
  fields; if it does, that is a decision-right violation.

The rule fires only when the deterministic check matches. The
semantic checker is not invoked for this rule — false positives on
phrasing are too costly.

### Acceptance criteria

1. The rule appears in `regulatory_rules.py` and in
   `ComplianceVerdict.regulatory_basis` when triggered.
2. A synthetic test where the central agent emits "I am buying 10%
   AAPL" produces a `forced_block` after max revisions with
   `MANIFEST_DECISION_RIGHT_RESPECTED` listed.
3. A normal advisory recommendation
   ("Allocate 10% to AAPL") does **not** trigger the rule — only
   first-person execution language does.
4. No regression in TC-08, TC-09, TC-15 when run with `--dry-run`.

---

## Item 2 — Broaden Override Policy (paper)

### Problem

The conceptual-model definition of Override Policy reads:
*"Mechanisms and intervention routes allowing a **human** to halt,
revert, or revoke the agent's actions mid-execution."* The
implementation provides automated mechanisms (revision budget,
`forced_block`) but no human halt. As written, the model claims a
property the framework does not deliver. A reviewer reading the
paper and then the code will see a gap that does not need to exist
— the framework's actual override teeth are the gate.

### Fix

In `paper/ai-intent-er2026-v2.tex`, in the Compliance Agent section
(`\subsection{Compliance Agent}`, around line 521) or in a new
paragraph in the Orchestration Protocol section, add:

> **Override Mechanisms.** AI-Intent's override policy is delivered
> at two layers. The framework provides *automated* override:
> compliance verdicts can reject a proposed action, request a
> revision, or — after a configurable revision budget — drop it as
> `forced_block`. Human override (mid-flight cancellation, manual
> revert, principal-initiated revocation) is a deployment-time
> property, achievable by exposing the `principal_id`-stamped
> session log as a control surface. The conceptual model treats
> these as one capability with two delivery modes; the prototype
> implements only the automated layer.

If the canonical conceptual-model definition is maintained
externally (slide deck, governance handbook), update its Override
Policy entry to read:

> "Mechanisms — automated, human, or both — by which proposed
> actions can be halted, revised, or revoked before delivery.
> Includes deterministic revision budgets and gate-enforced blocks
> at framework level, and (deployment-dependent) human intervention
> routes."

### Acceptance criteria

1. The paper's claim about override is consistent with the
   implementation (no claim of human-in-the-loop the code does not
   provide).
2. The conceptual-model entry, wherever maintained, names both
   automated and human modes.

---

## Item 3 — Tie Capability to Decision Right (paper / concept)

### Problem

The conceptual-model entry for Capability reads:
*"The authorized tools, data sources, and system actuators (e.g.,
API write access) the agent is permitted to use."* This conflates
two distinct things with very different audit properties:

1. **Recommendation surface** — what an agent may opine on (e.g. "Gold
   and Silver only" for the materials agent). Already encoded in
   `risk_parameters`.
2. **Actuator grants** — what side effects the agent may cause
   ("submit order to broker API"). The prototype has none, because
   no agent has `decision_right="execute"`.

A reviewer reading the conceptual model and the code will see
"Capability includes API write access" but no actuator wiring,
because there are no execute-tier agents. The two are coherent if
Capability is parameterised by Decision Right — but that
parameterisation is not stated.

### Fix

Update the Capability definition to state the dependency:

> **Capability.** The authorized tools, data sources, and system
> actuators the agent is permitted to use. The shape of capability
> depends on the agent's Decision Right: for `recommend` and
> `advise` agents, capability is the *opinable surface* (asset
> universe, data sources, allowed value ranges). For `execute`
> agents, capability additionally includes actuator grants (write
> access to external APIs, order routing, etc.). For `enforce`
> agents, capability is the read-only access required to evaluate
> proposed actions. The reference implementation contains only
> non-execute agents, so capability is exercised exclusively as
> recommendation surface.

In `paper/ai-intent-er2026-v2.tex`, this can land as:

- A revision to the formal manifest definition
  (`\subsection{Agent Manifest}`, around line 481) to add Capability
  and Decision Right as explicit fields:

  ```
  M = ⟨id, name, role, dr, scope, C, K, R, U, summary⟩
  ```

  where `dr ∈ DecisionRight = {execute, recommend, advise, enforce}`,
  `K` is the capability set (typed by `dr`), and `U` is the
  uncertainty policy. Document each in prose.

- A footnote or paragraph stating that the prototype operates in
  `recommend` / `advise` / `enforce` modes only.

### Acceptance criteria

1. The paper's formal definition of `M` includes `dr`, `K` (capability),
   and `U` (uncertainty policy), matching the implemented
   `AgentManifest`.
2. The text states that capability shape depends on decision right
   and that the prototype contains no `execute`-tier agents.

---

## Item 4 — Soften "tamper-evident" claim (paper / concept)

### Problem

The conceptual-model entry for Accountability Trace reads:
*"The **immutable, tamper-evident** log recording what the agent
attempted, what the enforcer decided, and the rationale behind
it."* The implementation persists messages in SQLite. SQLite is
append-only by convention only — anyone with file access can edit
a row. There is no hash chain, no signature, no WORM store. The
claim is stronger than what the code delivers.

### Fix

In the conceptual-model entry, change "immutable, tamper-evident"
to:

> "An append-only audit log of what the agent attempted, what the
> enforcer decided, and the rationale behind it. Tamper-evidence
> is a deployment-time property (achievable via hash chain,
> append-only WORM storage, or external attestation), not a
> framework-level guarantee."

In `paper/ai-intent-er2026-v2.tex`, in
`\subsection{Accountability Trace}` (around line 691), add at the
end of the section:

> The trace is structurally append-only: the orchestrator never
> rewrites or deletes prior messages. Cryptographic
> tamper-evidence (hash chains, signed entries) is a deployment
> hardening — the reference implementation persists to SQLite,
> which is append-only by convention. Productionising the trace
> for regulator-grade evidence is a deployment concern, not a
> framework defect.

### Acceptance criteria

1. No claim of tamper-evidence appears unqualified anywhere in the
   paper or conceptual model.
2. The Accountability Trace section names the deployment-hardening
   path explicitly.

---

## Item 5 — Tune escalate_below default (code)

### Problem

`UncertaintyPolicy.escalate_below` defaults to `"medium"`. This
means any sub-agent that self-rates as `"medium"` *or* `"low"`
triggers an `uncertainty.escalate.{agent}` log entry. LLMs default
to medium confidence very frequently, so under the current default,
nearly every consulted agent in nearly every session produces an
escalation. This floods the audit trail and dilutes the signal —
a true low-confidence escalation looks identical to a routine
medium-confidence one.

### Fix

In `agents/manifests.py`, change the default:

```python
class UncertaintyPolicy(BaseModel):
    escalate_below: ConfidenceLevel = "low"   # was "medium"
    block_below: ConfidenceLevel | None = None
```

The system prompt text generated from the policy will continue to
say "results at confidence={escalate_below} or below will be
escalated" — accurate either way.

Per-manifest overrides remain available; the central agent or any
sub-agent can opt back into `medium`-threshold escalation by
setting `uncertainty_policy=UncertaintyPolicy(escalate_below="medium")`
explicitly.

### Acceptance criteria

1. Default `UncertaintyPolicy().escalate_below == "low"`.
2. A run of TC-08, TC-09, TC-15 with neutral disposition produces
   zero `uncertainty.escalate.*` entries when sub-agents respond
   with `"medium"` or `"high"` confidence.
3. A synthetic run where a sub-agent returns `"low"` confidence
   still produces the escalation entry.

---

## Out of scope for this PRD

- Adding a hash-chained accountability trace (item 4 alternative).
  Defer until a reviewer asks for tamper-evidence.
- Adding a human-in-the-loop cancel button to the Streamlit UI
  (item 2 alternative). Out of scope for the prototype.
- Promoting `risk_parameters` to a strongly-typed `Capability`
  Pydantic model. The current dict is sufficient and the typing
  effort is high.
- Adding `confidence` to the central agent's synthesis JSON schema.
  Worth doing eventually, separate work item.

## File touch list

| Item | File | Type |
|---|---|---|
| 1 | `agents/regulatory_rules.py` | code |
| 1 | `agents/compliance.py` | code |
| 2 | `paper/ai-intent-er2026-v2.tex` | paper |
| 3 | `paper/ai-intent-er2026-v2.tex` | paper |
| 4 | `paper/ai-intent-er2026-v2.tex` | paper |
| 5 | `agents/manifests.py` | code |
