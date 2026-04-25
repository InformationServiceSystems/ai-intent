# PRD: ER-Model Alignment for AI-Intent

## Context

A new ER-style conceptual diagram (three layers: Authorization,
Constraint, Accountability) introduces relationships and entities the
current implementation does not represent structurally. The diagram
reads:

- **Layer 1 (Authorization):** Principal → Mandate → DecisionRight,
  Mandate ↔ Agent, Agent self-sub-delegation, Mandate self-decomposition.
- **Layer 2 (Constraint):** Mandate constrained by Boundary, permits
  Capability, governed by UncertaintyPolicy.
- **Layer 3 (Accountability):** Principal invokes OverridePolicy;
  OverridePolicy subject to / triggers Mandate; Agent produces
  AccountabilityTrace; Principal recorded in AccountabilityTrace; trace
  cross-references all five constraint and override entities by
  identifier.

The current implementation aligns on Layer 1 (with DecisionRight
inlined as a Mandate field) and partially on Layer 2 (Capability is
an untyped dict, not a typed entity). Layer 3 has the largest gap:
OverridePolicy is not modeled as an entity, mandate decomposition has
no structural representation, and Capability/OverridePolicy are not
cross-referenced in the trace.

This PRD specifies five changes that close the structural gap without
forcing a rewrite. Items are independent and can land in any order;
recommended order is 2 → 3 → 1 → 4 → 5.

---

## Item 1 — Promote Capability to a typed entity

### Problem

The diagram models Capability as a first-class entity that a Mandate
*permits* (1:N). The implementation has `AgentManifest.risk_parameters:
dict[str, Any]`, an untyped bundle. There is no `capability_id` to
reference from the trace, no shape contract, no decomposition between
"asset universe", "value range", "actuator grant", or "tool access".

### Fix

Add a typed model:

```python
class Capability(BaseModel):
    capability_id: str           # globally unique within the registry
    description: str             # plain-language statement
    kind: Literal["asset_universe", "value_range", "actuator", "tool", "data_source"]
    parameter: str               # name (mirrors a key in risk_parameters)
    value: Any                   # the bound (number, list, bool, etc.)
```

Add `capabilities: list[Capability]` to `AgentManifest`. Populate
explicitly per manifest (no auto-derivation from `risk_parameters` —
the typing decisions need human judgment). Keep `risk_parameters` as
the canonical compute-side dict for backwards compatibility with
`compliance.py` reads.

Capability shape is parameterised by Decision Right (per the paper's
extended definition): for `recommend` and `advise` agents, kinds are
`asset_universe` / `value_range` / `data_source`; the `actuator` kind
is reserved for `execute`-tier agents (none in the prototype).

### Acceptance

- `AgentManifest.capabilities` is a non-empty list for every manifest.
- Each capability has a `capability_id` unique within the manifest.
- For each existing `risk_parameters` entry, there is a corresponding
  capability with `parameter` = that key and `value` = that value.
- A new helper `get_capability(capability_id)` returns the
  `Capability` (raises KeyError otherwise).

---

## Item 2 — Add mandate decomposition fields

### Problem

The diagram shows `Mandate decomposes into Mandate` as a recursive
structural relationship. The implementation has the central agent
calling sub-agents at runtime via `compliance.route()`, but no
structural record on the manifest itself: nothing says "central's
mandate decomposes into stocks/bonds/materials".

### Fix

Add to `AgentManifest`:

```python
parent_mandate_id: str | None = None
sub_mandate_ids: list[str] = []
```

Populate:

| Manifest | parent | sub |
|---|---|---|
| central | None | ["stocks", "bonds", "materials"] |
| stocks | "central" | [] |
| bonds | "central" | [] |
| materials | "central" | [] |
| compliance | None | [] |

Compliance is intentionally outside the decomposition tree — it's a
gate, not a sub-mandate. Document this in the manifest comments.

### Acceptance

- `CENTRAL_MANIFEST.sub_mandate_ids == ["stocks", "bonds", "materials"]`.
- For every `m` with `m.parent_mandate_id == "central"`,
  `m.agent_id in CENTRAL_MANIFEST.sub_mandate_ids`.
- A new helper `get_sub_mandates(agent_id) -> list[AgentManifest]`.

---

## Item 3 — Make sub-delegation visible at Agent level

### Problem

Diagram has `Agent sub-delegates Agent` as a recursive relationship
distinct from `Mandate decomposes into Mandate`. In this codebase
Agent and Mandate are 1:1 — every agent has exactly one manifest, no
agent exists without one. So `sub_mandate_ids` already implies
sub-delegation. But the diagram lists them separately.

### Fix

This item is **deliberately a no-op at the data layer**. The
implementation already encodes sub-delegation via `sub_mandate_ids`;
adding a duplicate `sub_agent_ids` field would be redundant given the
1:1 mapping enforced by `_MANIFEST_REGISTRY`.

Instead, document the equivalence in the paper:

> In the reference implementation, every Agent has exactly one
> Mandate (the manifest registry enforces this 1:1 mapping). The
> diagram's distinct `Agent sub-delegates Agent` and `Mandate
> decomposes into Mandate` relationships therefore collapse to a
> single field, `sub_mandate_ids`. In a deployment where multiple
> agents share a manifest (e.g., a fleet of stocks-tier specialists),
> the two relationships would diverge and require separate
> representation.

### Acceptance

- The paper's discussion of decomposition explicitly covers the
  collapse-to-one-field claim.
- No new code field added.

---

## Item 4 — OverridePolicy as a first-class entity

### Problem

The diagram's heaviest claim is on OverridePolicy: it is a typed
entity that the *Principal invokes*, that is *subject to* a Mandate,
that *triggers* (mandate re-evaluation), and that is *recorded in*
the AccountabilityTrace. The implementation has the *behavior* (the
revision loop, `forced_block`) but no *entity* — there's no
`OverridePolicy` Pydantic model, no `policy_id` to reference, no
principal-invoked override path at all.

### Fix

**Data model.** Add to `agents/manifests.py`:

```python
class OverridePolicy(BaseModel):
    policy_id: str                              # e.g. "default_override_v1"
    description: str
    automated_max_revisions: int = 2            # mirrors compliance _max_revisions
    automated_block_terminal: bool = True       # forced_block drops the message permanently
    principal_halt_enabled: bool = False        # mid-flight halt (deployment-dependent)
    principal_revoke_enabled: bool = True       # post-hoc session revocation
```

Define a module-level `DEFAULT_OVERRIDE_POLICY` instance. Reference
it from every `AgentManifest` via a new field
`override_policy: OverridePolicy = DEFAULT_OVERRIDE_POLICY`.

**Wire automated overrides through the policy.** In `compliance.py`,
every `compliance.revision`, `compliance.block`, and `compliance.
escalate` MCP message gains `policy_id` in its payload. The orchestrator's
`compliance_multiplier` continues to scale `automated_max_revisions` at
runtime.

**Principal revocation.** Add a Streamlit button in the Results tab:
"⚠ Revoke this session". On click:

1. Create `principal.revoke` MCP message with payload
   `{policy_id, principal_id, revoked_at, reason}`.
2. The orchestration is already complete — revocation is post-hoc.
   It does not retract the recommendation; it stamps the trace with
   the principal's revocation event.
3. Surface revocation in `_generate_trace()` as
   `revocation: { revoked: true, at: ..., by: ..., policy_id: ... }`.

**Mid-flight halt is out of scope.** It requires running the
orchestrator in a thread/task and polling a halt event between phases —
a non-trivial restructure of the sync `asyncio.run()` flow. Document
as deployment-time.

### Acceptance

- `OverridePolicy` is importable from `agents.manifests`.
- Every `AgentManifest.override_policy.policy_id` is non-empty.
- The Streamlit revocation button appears after a successful run and
  writes a `principal.revoke` MCP message stamped with the
  principal's `principal_id`.
- The accountability trace contains a `revocation` block when the
  session was revoked, absent otherwise.
- Existing automated revision/block events log `policy_id` in their
  payloads.

---

## Item 5 — Cross-reference Capability and OverridePolicy in the trace

### Problem

The conceptual diagram's caption: *"AccountabilityTrace entries
cross-reference Mandate, DecisionRight, Boundary, Capability,
UncertaintyPolicy, and OverridePolicy by identifier, enabling full
provenance reconstruction."* The current trace cross-references:

- Mandate: yes (via `agent_id`)
- DecisionRight: indirectly (via manifest lookup)
- Boundary: yes (via `violated_rules` → rule_id)
- UncertaintyPolicy: yes (via `uncertainty.escalate.*` events)
- Capability: **no** (untyped dict, no IDs)
- OverridePolicy: **no** (no entity)

### Fix

Once Items 1 and 4 are in:

1. **In `agents/compliance.py`:** when a deterministic check fails on
   a value bound (e.g. allocation > `max_single_position`), include
   `capability_id` in the `RuleResult.detail` JSON or as a new
   `RuleResult.capability_ids: list[str]` field. Map known
   `parameter` names to `capability_id` via the manifest.
2. **In every revision/block/escalate MCP payload:** include the
   `policy_id` of the active override policy.
3. **In `app.py::_generate_trace()`:** add a top-level
   `referenced_entities` block:
   ```json
   {
     "referenced_entities": {
       "mandates":          ["central", "stocks", "bonds", "materials"],
       "decision_rights":   {"central": "advise", "stocks": "recommend", ...},
       "capabilities":      ["stocks_max_position", "materials_approved_commodities", ...],
       "uncertainty_policies": ["central:escalate_below=low", ...],
       "override_policies": ["default_override_v1"],
       "boundary_rules":    ["MANIFEST_STOCKS_LARGECAP", ...]
     }
   }
   ```

### Acceptance

- `_generate_trace(result)` includes a non-empty `referenced_entities`
  block.
- For every constraint violation in the trace, the originating
  `capability_id` (or `rule_id` for non-Capability boundaries) is
  resolvable.
- Every revision/block/revoke event includes a `policy_id` in its
  payload.

---

## Out of scope for this PRD

- Mid-flight session halt (requires async-task restructure).
- Multiple `Principal` entities per session (multi-tenant audit).
- Treating Boundary, DecisionRight, UncertaintyPolicy as separate
  entities with their own tables — they remain inlined Mandate fields.
- Refactoring `risk_parameters` callsites in `compliance.py` to read
  from `Capability` objects. Capabilities are additive documentation
  for now; risk_parameters remains the compute path.

## File touch list

| Item | Files |
|---|---|
| 1 | `agents/manifests.py` |
| 2 | `agents/manifests.py` |
| 3 | `paper/ai-intent-er2026-v2.tex` (paper note only) |
| 4 | `agents/manifests.py`, `agents/compliance.py`, `app.py`, `mcp/logger.py` |
| 5 | `agents/compliance.py`, `app.py` |
