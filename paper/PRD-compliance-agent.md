# PRD: Compliance Agent — Runtime Intent Enforcement

**Product:** AI-Intent Investment System
**Author:** Wolfgang Maass
**Date:** 2026-03-31
**Status:** Draft

---

## 1. Problem Statement

The AI-Intent framework declares agent behavior through manifests (intent scope, boundary constraints, risk parameters) and logs all inter-agent communication via the MCP message bus. However, **no component verifies that messages actually comply with manifests before they are forwarded**. The system relies entirely on LLM self-assessment: each agent is prompted to report its own violations via `out_of_scope: true`.

This creates three concrete failure modes observed in production:

**F1 — Routing inconsistency:** The orchestrator's routing rationale claims it will consult bonds, but `agents_to_call` only contains `["stocks"]`. The sub-question for bonds is populated (`query_for_bonds`) but never sent. No code detects the contradiction.

**F2 — Self-assessment bias:** A sub-agent may produce a response that violates its manifest constraints (e.g., recommending a mid-cap stock when the constraint says large-cap only) while self-reporting `out_of_scope: false`. The violation passes silently through to synthesis.

**F3 — Synthesis suppression:** The orchestrator's synthesis step may downplay or omit sub-agent constraint flags when producing the final recommendation. The central manifest says "Must surface constraint violations from sub-agents rather than suppressing them," but this is enforced only by prompting.

A **Compliance Agent** addresses all three by intercepting every MCP message, evaluating it against the relevant manifests, and either forwarding it or returning it for revision.

---

## 2. Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | Every inter-agent message is evaluated against relevant manifest constraints before forwarding | 100% of messages pass through compliance gate; no direct agent-to-agent communication |
| G2 | Deterministic constraint violations are caught programmatically without LLM calls | All `risk_parameters` with numeric/boolean/list values are checked in code |
| G3 | Semantic constraint violations are caught via independent LLM evaluation | A second LLM call with an adversarial prompt evaluates natural-language constraints |
| G4 | Non-compliant messages are returned to the issuing agent with specific revision instructions | Issuing agent receives feedback naming the violated constraint and what to fix |
| G5 | All compliance decisions are logged to the MCP bus as first-class audit events | Compliance check results appear in the MCP stream and accountability trace |
| G6 | The compliance agent itself is governed by a manifest | Compliance agent has its own AgentManifest with explicit scope and constraints |

---

## 3. Non-Goals

- Modifying manifest content or adding new constraints
- Blocking the entire pipeline on a single violation (graceful degradation preferred)
- Real-time user approval of compliance decisions
- Replacing the sub-agents' own constraint awareness (defense in depth, not replacement)

---

## 4. Architecture

### 4.1 Current Message Flow

```
User → Central (routing) → Stocks/Bonds/Materials (parallel) → Central (synthesis) → User
```

All arrows are direct. No verification at any point.

### 4.2 Proposed Message Flow

```
User → Central → [Compliance Gate] → Stocks/Bonds/Materials
                                            ↓
                                    [Compliance Gate]
                                            ↓
                          Central (synthesis) → [Compliance Gate] → User
```

The Compliance Agent operates as an **inline message interceptor** at three checkpoints:

| Checkpoint | Location | What It Checks |
|-----------|----------|----------------|
| **CP1: Post-Routing** | After orchestrator produces routing decision, before sub-agent calls | Routing consistency, minimum agent count, sub-question relevance to target agent scope |
| **CP2: Post-Analysis** | After each sub-agent returns its result, before results reach orchestrator | Agent stayed within intent scope, risk parameter compliance, constraint flag consistency |
| **CP3: Post-Synthesis** | After orchestrator produces final recommendation, before delivery to user | All violations surfaced, allocation limits respected, accountability note completeness |

### 4.3 Compliance Agent Manifest

```python
COMPLIANCE_MANIFEST = AgentManifest(
    agent_id="compliance",
    name="Compliance Gate Agent",
    emoji="🛡️",
    role="Intent Enforcement & Audit Verifier",
    intent_scope=(
        "Verify that all inter-agent messages comply with the sender's and "
        "receiver's manifest constraints. Evaluate messages at routing, "
        "analysis, and synthesis checkpoints. Return non-compliant messages "
        "for revision with specific feedback."
    ),
    boundary_constraints=[
        "Must never modify message content — only accept, reject, or return for revision",
        "Must never override or relax another agent's manifest constraints",
        "Must evaluate every message against both sender and receiver manifests",
        "Must log every compliance decision to the MCP bus with full rationale",
        "Must allow messages to proceed after max_revisions even if non-compliant, with a hard compliance flag",
        "Must complete evaluation within the timeout window — never block indefinitely",
    ],
    risk_parameters={
        "max_revisions": 2,
        "timeout_seconds": 30,
        "deterministic_checks_first": True,
    },
    plain_language_summary=(
        "The gatekeeper. Sits between all agents and checks every message "
        "against the rules. Cannot change messages, only approve them or "
        "send them back with feedback. After two failed revisions, lets "
        "the message through with a warning flag so the pipeline doesn't stall."
    ),
)
```

---

## 5. Feature Specifications

### 5.1 Compliance Check Model

**File:** `agents/compliance.py`

Define the result model for every compliance evaluation:

```python
class ComplianceVerdict(BaseModel):
    checkpoint: Literal["post_routing", "post_analysis", "post_synthesis"]
    target_agent: str                    # Agent whose message is being checked
    target_manifest: str                 # agent_id of the manifest checked against
    passed: bool
    deterministic_results: list[RuleResult]   # Programmatic checks
    semantic_results: list[RuleResult]         # LLM-based checks
    overall_status: Literal["pass", "revision_requested", "forced_pass"]
    revision_feedback: str | None        # What to fix (None if passed)
    revision_count: int                  # How many times this message has been revised
    
class RuleResult(BaseModel):
    rule: str                            # The constraint text
    source: Literal["deterministic", "semantic"]
    passed: bool
    detail: str                          # Why it passed or failed
```

### 5.2 Deterministic Rule Engine

**File:** `agents/compliance.py`

Programmatic checks derived directly from `risk_parameters`. These run first (fast, no LLM call needed).

**CP1 — Post-Routing Checks:**

| Rule | Source | Check |
|------|--------|-------|
| Minimum agents consulted | `central.risk_parameters["min_sub_agents_consulted"]` | `len(agents_to_call) >= 1` |
| Agents in approved set | Hardcoded agent registry | Every entry in `agents_to_call` is in `["stocks", "bonds", "materials"]` |
| Routing-rationale consistency | Structural | If `query_for_X` is non-null, then `X` must be in `agents_to_call` |
| Sub-question not empty | Structural | Every agent in `agents_to_call` has a non-empty `query_for_X` |

**CP2 — Post-Analysis Checks (per agent):**

| Rule | Source | Check |
|------|--------|-------|
| Stocks: large-cap only | `stocks.risk_parameters["max_market_cap_threshold"]` | If analysis mentions a specific company, flag if known mid/small-cap |
| Stocks: max single position | `stocks.risk_parameters["max_single_position"]` | If analysis suggests a percentage, verify ≤ 10% |
| Stocks: no leverage | `stocks.risk_parameters["leverage_permitted"]` | Scan for keywords: margin, leverage, short, derivative |
| Bonds: credit rating | `bonds.risk_parameters["min_credit_rating"]` | Scan for sub-investment-grade mentions: BB, B, CCC, junk, high-yield |
| Bonds: max duration | `bonds.risk_parameters["max_duration_years"]` | If duration mentioned, verify ≤ 10 years |
| Bonds: maturity concentration | `bonds.risk_parameters["max_single_maturity_bucket"]` | If percentages per year mentioned, verify ≤ 30% |
| Materials: approved commodities | `materials.risk_parameters["approved_commodities"]` | Scan for commodities not in ["Gold", "Silver"] |
| Materials: max allocation | `materials.risk_parameters["max_total_allocation"]` | If allocation percentage mentioned, verify ≤ 15% |
| Materials: no leverage | `materials.risk_parameters["leverage_permitted"]` | Scan for keywords: leveraged, futures, derivative, ETF (leveraged) |
| All: self-assessment consistency | Structural | If `constraint_flags` is non-empty but `out_of_scope` is false, flag for review |

**CP3 — Post-Synthesis Checks:**

| Rule | Source | Check |
|------|--------|-------|
| Max single asset class | `central.risk_parameters["max_single_asset_class"]` | If allocation percentages mentioned, verify none > 40% |
| Violations surfaced | Structural | Every sub-agent `out_of_scope: true` must appear in `constraint_violations` |
| Accountability note present | Structural | Non-empty, contains session_id |
| Accountability note complete | Structural | Contains: session ID, agents consulted, timestamp |

```python
def run_deterministic_checks(
    checkpoint: str,
    message_payload: dict,
    sender_manifest: AgentManifest,
    receiver_manifest: AgentManifest | None,
) -> list[RuleResult]:
    """Execute all programmatic compliance rules for a checkpoint."""
```

### 5.3 Semantic Compliance Evaluation

**File:** `agents/compliance.py`

For natural-language constraints that cannot be checked deterministically, a separate LLM call evaluates compliance. This LLM uses an **adversarial system prompt** — it is told to find violations, not to be helpful.

```python
SEMANTIC_CHECK_PROMPT = """You are a compliance auditor. Your job is to determine whether 
an agent's message violates any of its declared constraints.

You will receive:
1. The agent's manifest (intent scope and boundary constraints)
2. The message the agent produced

For EACH boundary constraint, determine:
- PASS: The message clearly complies with this constraint
- FAIL: The message violates this constraint (explain specifically how)
- UNCLEAR: Cannot determine compliance from the message content

Be adversarial. Look for subtle violations. Do not give the benefit of the doubt.
If a constraint requires something (e.g., "ESG screening required") and the message 
does not mention it, that is a FAIL, not a PASS.

Respond ONLY in this JSON format:
{"results": [{"constraint": "...", "verdict": "PASS|FAIL|UNCLEAR", "detail": "..."}]}"""
```

```python
async def run_semantic_checks(
    message_payload: dict,
    manifest: AgentManifest,
    session_id: str,
) -> list[RuleResult]:
    """Use an independent LLM call to evaluate natural-language constraint compliance."""
```

The semantic check runs **only if all deterministic checks pass**. If deterministic checks already found a violation, there's no need for the LLM call — the message is already non-compliant.

### 5.4 Revision Loop

**File:** `agents/compliance.py`

When a message fails compliance:

```python
class RevisionRequest(BaseModel):
    original_message: dict
    violated_constraints: list[str]
    revision_feedback: str
    revision_number: int
    max_revisions: int
```

The revision loop:

```
1. Agent produces message
2. Compliance evaluates → FAIL
3. Compliance builds RevisionRequest with specific feedback:
   "Your response violated constraint 'Large-cap equities only: market 
   capitalization must exceed $10 billion' — you recommended ACME Corp 
   which has a market cap of $3.2B. Revise your analysis to exclude 
   this company or explain why it qualifies."
4. Sub-agent re-runs with appended context:
   [Original system prompt] + [Original query] + 
   [Previous response] + [Compliance feedback]
5. Compliance re-evaluates revised response
6. If PASS → forward. If FAIL and revision_count < max_revisions → goto 3.
7. If FAIL and revision_count >= max_revisions → FORCED PASS:
   Forward message with compliance flag attached.
   Log status: "forced_pass" (not "ok", not "constraint_violation").
```

```python
async def evaluate_and_revise(
    agent_id: str,
    agent_func: Callable,
    query: str,
    session_id: str,
    checkpoint: str,
) -> tuple[dict, ComplianceVerdict]:
    """Run agent, evaluate compliance, loop revisions if needed, return final result."""
```

### 5.5 Orchestrator Integration

**File:** `agents/orchestrator.py`

The orchestrator pipeline changes from 5 steps to 5 steps with 3 compliance gates:

```
Step A: Log user query                          (unchanged)
Step B: Routing call                            (unchanged)
  → CP1: Compliance evaluates routing           (NEW)
  → If revision needed: re-run routing call     (NEW)
Step C: Parallel sub-agent calls                (unchanged)
  → CP2: Compliance evaluates each result       (NEW)
  → If revision needed: re-run that sub-agent   (NEW)
Step D: Synthesis call                          (unchanged)
  → CP3: Compliance evaluates synthesis         (NEW)
  → If revision needed: re-run synthesis        (NEW)
Step E: Log final output                        (unchanged)
```

The `OrchestrationResult` model gains new fields:

```python
class OrchestrationResult(BaseModel):
    # ... existing fields ...
    compliance_verdicts: list[ComplianceVerdict]  # All compliance checks performed
    total_revisions: int                          # Total revision loops across all checkpoints
    forced_passes: list[str]                      # Agent IDs that were force-passed
```

### 5.6 MCP Message Types

New MCP message methods for compliance events:

| Method | Direction | Description |
|--------|-----------|-------------|
| `compliance.check.routing` | internal | CP1 evaluation result |
| `compliance.check.{agent_id}` | internal | CP2 evaluation result for a sub-agent |
| `compliance.check.synthesis` | internal | CP3 evaluation result |
| `compliance.revision.{agent_id}` | outbound | Revision request sent to an agent |
| `compliance.forced_pass.{agent_id}` | internal | Message force-passed after max revisions |

New `response_status` value:

| Status | Meaning |
|--------|---------|
| `"forced_pass"` | Compliance check failed but message forwarded after max revisions |

This requires updating the `MCPMessage` model's `response_status` literal:

```python
response_status: Literal["pending", "ok", "error", "constraint_violation", "forced_pass"]
```

---

## 6. UI Integration

### 6.1 Compliance Gate Indicators in Timeline

The intent lifecycle timeline (from PRD-intent-visualization) gains compliance gate indicators between phases:

```
[1. Query] → [CP1 🛡️] → [2. Routing] → [CP2 🛡️] → [3. Delegation] → [CP3 🛡️] → [4. Synthesis] → [5. Response]
```

Each gate indicator shows:
- Green shield: all checks passed
- Orange shield: passed after revision(s)
- Red shield: forced pass (violations not resolved)

Clicking a gate expands to show the full `ComplianceVerdict` with per-rule results.

### 6.2 Compliance Column in Constraint Enforcement View

The existing constraint enforcement view (right column, "Constraint Audit" tab) gains a new column showing whether each constraint was verified by the compliance agent:

```
✅ Large-cap only (>$10B)      [self-reported: passed] [compliance: passed]
⚠️ ESG screening required      [self-reported: passed] [compliance: FAIL — not mentioned]
```

This directly surfaces the gap between self-assessment and independent verification.

### 6.3 Revision History Panel

New UI component showing the revision loop for any agent that required revisions:

```
╔══════════════════════════════════════════════╗
║  📈 Stock Broker Agent — 1 revision          ║
╠══════════════════════════════════════════════╣
║  Attempt 1:                                  ║
║  ❌ Recommended ACME Corp (mid-cap $3.2B)    ║
║  Compliance: "Violates large-cap constraint" ║
║                                              ║
║  Attempt 2:                                  ║
║  ✅ Revised to exclude ACME Corp             ║
║  Compliance: "All constraints satisfied"     ║
╚══════════════════════════════════════════════╝
```

### 6.4 Agent Graph Update

The agent graph gains:
- A compliance node (shield icon) in the center between central and sub-agents
- Edges route through the compliance node
- Shield node color reflects worst-case status across all checkpoints

---

## 7. Data Flow

```
Orchestrator produces routing decision
        ↓
CP1: Compliance Gate (post-routing)
  ├─ Deterministic: min_agents, routing consistency, sub-question presence
  ├─ Semantic: sub-questions match target agent scope
  ├─ PASS → proceed to sub-agent calls
  └─ FAIL → return to orchestrator with revision feedback → re-route
        ↓
Sub-agent produces analysis
        ↓
CP2: Compliance Gate (post-analysis) — per agent
  ├─ Deterministic: risk_parameter checks, keyword scans, self-assessment consistency
  ├─ Semantic: analysis stays within intent scope, constraints honored
  ├─ PASS → forward result to orchestrator
  └─ FAIL → return to sub-agent with revision feedback → re-analyze
        ↓
Orchestrator produces synthesis
        ↓
CP3: Compliance Gate (post-synthesis)
  ├─ Deterministic: violations surfaced, accountability note complete, allocation limits
  ├─ Semantic: recommendation consistent with sub-agent results
  ├─ PASS → deliver to user
  └─ FAIL → return to orchestrator with revision feedback → re-synthesize
```

---

## 8. Implementation Plan

### Phase 1: Core Compliance Engine

| Task | File(s) | Description |
|------|---------|-------------|
| 1.1 | `agents/manifests.py` | Add `COMPLIANCE_MANIFEST` |
| 1.2 | `agents/compliance.py` | Define `ComplianceVerdict`, `RuleResult`, `RevisionRequest` models |
| 1.3 | `agents/compliance.py` | Implement `run_deterministic_checks()` for all three checkpoints |
| 1.4 | `mcp/logger.py` | Add `"forced_pass"` to `response_status` literal |

### Phase 2: Semantic Checks & Revision Loop

| Task | File(s) | Description |
|------|---------|-------------|
| 2.1 | `agents/compliance.py` | Implement `run_semantic_checks()` with adversarial LLM prompt |
| 2.2 | `agents/compliance.py` | Implement `evaluate_and_revise()` revision loop |
| 2.3 | `agents/compliance.py` | Implement `check_routing()`, `check_analysis()`, `check_synthesis()` top-level functions |

### Phase 3: Orchestrator Integration

| Task | File(s) | Description |
|------|---------|-------------|
| 3.1 | `agents/orchestrator.py` | Insert CP1 after routing call with revision loop |
| 3.2 | `agents/orchestrator.py` | Wrap sub-agent calls with CP2 via `evaluate_and_revise()` |
| 3.3 | `agents/orchestrator.py` | Insert CP3 after synthesis with revision loop |
| 3.4 | `agents/orchestrator.py` | Extend `OrchestrationResult` with compliance fields |

### Phase 4: UI Integration

| Task | File(s) | Description |
|------|---------|-------------|
| 4.1 | `ui/intent_timeline.py` | Add compliance gate indicators between phases |
| 4.2 | `ui/constraint_view.py` | Add compliance verification column alongside self-reported status |
| 4.3 | `ui/revision_history.py` | New component: revision history panel |
| 4.4 | `ui/agent_graph.py` | Add compliance node to graph |
| 4.5 | `app.py` | Wire compliance data into all UI components |

### Phase 5: Testing & Edge Cases

| Task | File(s) | Description |
|------|---------|-------------|
| 5.1 | — | Test: crypto futures query triggers CP2 violations across all agents |
| 5.2 | — | Test: routing inconsistency (rationale vs. agents_to_call mismatch) triggers CP1 |
| 5.3 | — | Test: max revision limit reached → forced pass with flag |
| 5.4 | — | Test: compliance timeout → forced pass |
| 5.5 | — | Test: normal query passes all checkpoints with zero revisions |

---

## 9. New & Modified Files

| File | Status | Purpose |
|------|--------|---------|
| `agents/compliance.py` | **New** | Compliance engine: deterministic checks, semantic checks, revision loop |
| `ui/revision_history.py` | **New** | Revision history UI component |
| `agents/manifests.py` | Modified | Add `COMPLIANCE_MANIFEST` |
| `agents/orchestrator.py` | Modified | Insert 3 compliance gates, extend result model |
| `mcp/logger.py` | Modified | Add `"forced_pass"` status |
| `ui/intent_timeline.py` | Modified | Compliance gate indicators |
| `ui/constraint_view.py` | Modified | Dual-column: self-reported vs. compliance-verified |
| `ui/agent_graph.py` | Modified | Compliance node in graph |
| `app.py` | Modified | Wire compliance data into UI |

---

## 10. Performance Considerations

| Concern | Mitigation |
|---------|-----------|
| Additional LLM calls per message | Semantic checks only run if deterministic checks pass (short-circuit) |
| Revision loops add latency | Max 2 revisions; timeout per check (30s); forced pass as escape valve |
| Parallel sub-agent checks | CP2 checks run in parallel (one per sub-agent), same as current sub-agent calls |
| Total pipeline cost | Worst case: 3 checkpoints × (1 deterministic + 1 semantic + 2 revisions × 1 agent + 1 semantic) = ~9 additional LLM calls. Best case (all deterministic pass): 3 checkpoints × 0 additional LLM calls |

Expected typical run: 1-2 additional LLM calls (semantic checks at CP2 and CP3, no revisions needed).

---

## 11. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC1 | Routing inconsistency (rationale mentions agent not in `agents_to_call`) is caught at CP1 | Reproduce the stocks/bonds example from the problem statement |
| AC2 | Sub-agent recommending out-of-scope asset is caught at CP2 even when self-reporting `out_of_scope: false` | Craft prompt that tricks agent into recommending a mid-cap stock |
| AC3 | Synthesis that omits a sub-agent violation is caught at CP3 | Verify with crypto futures query |
| AC4 | Revision loop produces improved response on second attempt | Compare attempt 1 vs attempt 2 analysis text |
| AC5 | Forced pass after max revisions does not block pipeline | Set max_revisions=0, verify message goes through with flag |
| AC6 | Compliance events appear in MCP stream with correct methods | Visual inspection of `compliance.check.*` and `compliance.revision.*` messages |
| AC7 | Timeline shows shield indicators between phases | Visual inspection |
| AC8 | Constraint enforcement view shows dual columns (self-reported vs. compliance) | Run query and compare columns |
| AC9 | No regressions: existing pipeline works identically when all compliance checks pass | Run standard queries, verify same results with added compliance metadata |
| AC10 | Compliance agent's own manifest is viewable in the UI | Click compliance node in agent graph |

---

## 12. Conceptual Modeling Implications

This PRD introduces a new first-class construct to the AI-Intent metamodel:

**ComplianceGate** — a verification point that evaluates messages against manifests before forwarding. It has:
- A position in the message flow (checkpoint)
- A reference to the manifest(s) it checks against
- Two evaluation layers (deterministic + semantic)
- A revision protocol with bounded retry

This closes the **enforcement triangle**:

```
AgentManifest (declares)  →  MCPMessage (records)  →  ComplianceGate (enforces)
       ↑                                                        ↓
       └────────────────── revision feedback ──────────────────┘
```

Manifests go from being operative (embedded in prompts) and observable (logged in MCP) to **enforceable** (validated at compliance gates). This is a stronger claim than any existing multi-agent governance framework offers.
