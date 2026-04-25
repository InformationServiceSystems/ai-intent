# AI-Intent: Conceptual Model Alignment Analysis

This document summarizes how the AI-Intent reference implementation aligns with the three-layer conceptual model (Authorization, Constraint, Accountability). It covers entities, relationships, multiplicities, and known gaps. The analysis reflects the state of the codebase after the conceptual-alignment and ER-model-alignment PRDs have been executed.


# Verdict at a glance

- **Layer 1 — Authorization.** 4 of 4 concepts covered. 4 of 5 relationships covered. Aligned with one ER-granularity caveat.
- **Layer 2 — Constraint.** 3 of 3 concepts covered. 3 of 3 relationships covered. Aligned.
- **Layer 3 — Accountability.** 2 of 2 concepts covered. 5 of 5 relationships covered. Aligned, with one out-of-scope deployment item.

The implementation now provides every concept the model declares and every relationship except sub-delegation-as-distinct-from-decomposition, which is deliberately collapsed to a single field given that Agent and Mandate are 1:1 in this codebase.


# Concept-by-concept alignment

## Layer 1 — Authorization

**Principal.** Aligned. The `principal_id` string is threaded through `orchestrator.run()`, registered on the logger, stamped on every `mcp_messages` row, and surfaced in the trace JSON and text report.

**Mandate.** Aligned. Implemented as the `AgentManifest` Pydantic model in `agents/manifests.py`. Five module-level constants are held in `_MANIFEST_REGISTRY`.

**DecisionRight.** Aligned by content; ER granularity differs. Implemented as a `decision_right` typed Literal field on `AgentManifest` with values `execute`, `recommend`, `advise`, `enforce`. The model treats it as a separate entity carried by Mandate; the implementation inlines it as a manifest field.

**Agent.** Aligned. Implemented as `agents/*.py` modules with identity carried by the `agent_id` on the manifest. Agent and Mandate are 1:1 in this codebase.

## Layer 2 — Constraint

**Boundary.** Aligned. Implemented as `boundary_constraints: list[str]` on `AgentManifest`, plus the `RegulatoryRule` registry that maps rule IDs to those constraints.

**Capability.** Aligned. A `Capability` Pydantic model and a `capabilities: list[Capability]` field on `AgentManifest`, with twenty typed capabilities populated across the five manifests. The `risk_parameters` dictionary is retained as the compute path.

**UncertaintyPolicy.** Aligned. An `UncertaintyPolicy` model on `AgentManifest`. Escalation logic in the orchestrator emits `uncertainty.escalate.{agent}` MCP messages when a sub-agent's confidence falls at or below the policy threshold.

## Layer 3 — Accountability

**OverridePolicy.** Aligned for post-hoc revocation; mid-flight halt is documented as deployment-time. Implemented as an `OverridePolicy` model with a `DEFAULT_OVERRIDE_POLICY` instance referenced by every manifest's `override_policy` field. Compliance revision and block payloads stamp the `policy_id`. The Streamlit revocation button writes a `principal.revoke` MCP message stamped with `policy_id` and `principal_id`.

**AccountabilityTrace.** Aligned. Implemented as `MCPMessage` records in the SQLite `mcp_messages` table, with `_generate_trace()` returning a structured dict and `_format_trace_text()` rendering a human-readable report.


# Relationship-by-relationship alignment

**Principal delegates Mandate.** Multiplicity 1 to many. Recorded but not delegated per-principal. Each session binds one `principal_id` and uses the five module-level manifests; there is no per-principal mandate creation. Multi-tenancy is a deployment concern.

**Mandate decomposes into Mandate.** Recursive. Aligned. The `parent_mandate_id` and `sub_mandate_ids` typed fields encode this relationship: central decomposes into stocks, bonds, and materials. Compliance is intentionally outside the decomposition tree. The helper is `get_sub_mandates(agent_id)`.

**Mandate carries DecisionRight.** Multiplicity 1 to many in the diagram, 1 to 1 in implementation. Reduced multiplicity. Defensible for this prototype: an agent has one authority level. If a deployment needs context-specific rights, the field can be promoted to a list of grants.

**Agent operates under Mandate.** Multiplicity 1 to 1. Aligned. The `_MANIFEST_REGISTRY[agent_id]` lookup enforces 1:1.

**Agent sub-delegates Agent.** Recursive. Deliberately merged with mandate decomposition because Agent and Mandate are 1:1 in this codebase. Documented in `PRD-er-model-alignment.md`, Item 3. The two relationships diverge only when multiple agents share a manifest.

**Mandate constrained by Boundary.** Multiplicity 1 to many. Aligned. At least one boundary constraint per manifest, enforced by Pydantic and by the well-formedness condition in paper section 3.2.

**Mandate permits Capability.** Multiplicity 1 to many. Aligned. Twenty typed capabilities across the manifests.

**Mandate governed by UncertaintyPolicy.** Multiplicity 1 to 1. Aligned.

**Principal invokes OverridePolicy.** Multiplicity 1 to many. Aligned for the post-hoc revocation path. The Streamlit button writes a `principal.revoke` MCP message gated on `OverridePolicy.principal_revoke_enabled`. Mid-flight halt is `principal_halt_enabled=False` in the prototype.

**OverridePolicy subject to Mandate.** Multiplicity 1 to 1. Aligned. The implementation stores the relationship as a Mandate-has-a-OverridePolicy field, which carries the same data as the diagram's reverse navigation.

**OverridePolicy triggers Mandate re-evaluation.** Multiplicity 1 to many. Aligned. The revision loop in `compliance.route()` re-evaluates the message against the manifest. Revision and block payloads carry the `policy_id`.

**Agent produces AccountabilityTrace.** Multiplicity 1 to many. Aligned. Every `build_message()` plus `logger.log()` call writes a row attributed to a `from_agent`.

**Principal recorded in AccountabilityTrace.** Multiplicity many to 1. Aligned. The `principal_id` column is stamped on every row and surfaced in the trace JSON and text report.

**Trace cross-references Mandate, DecisionRight, Boundary, Capability, UncertaintyPolicy, and OverridePolicy by identifier.** This is the diagram's caption claim. Aligned. The `_generate_trace()` function emits a `referenced_entities` block listing mandates, decision rights, capabilities, uncertainty policies, override policies, and boundary rules. Verified end-to-end in the synthetic test included with the ER-model-alignment PRD.


# Multiplicity audit

The diagram's multiplicities are honored except in one place where the implementation knowingly diverges.

**Mandate to DecisionRight is 1:1, not 1:N.** The diagram suggests a Mandate could carry multiple DecisionRights. In domain terms, an agent could plausibly hold different rights for different contexts — for example, recommend for stocks, execute for cash sweeps. The prototype binds one right per agent. If that becomes load-bearing, the field can be promoted to a list of grants with context filters.

All other multiplicities are honored. The fields `boundary_constraints`, `capabilities`, and `sub_mandate_ids` are list-typed. The fields `uncertainty_policy` and `override_policy` are 1:1. The field `parent_mandate_id` is optional.


# Layer-by-layer verdict

## Layer 1 — Authorization

Fully populated. The only ER-style imperfection is that DecisionRight is a typed manifest field rather than a typed entity, and 1:1 instead of 1:N. Both are deliberate prototype choices that the paper now documents in section 3.3.

## Layer 2 — Constraint

Fully aligned. Boundary, Capability, and UncertaintyPolicy are typed, populated for every manifest, surfaced in the system prompt, and enforced. Boundary is enforced by deterministic rules and the semantic checker. Capability is enforced through deterministic value bounds in `compliance.py`. UncertaintyPolicy is enforced through the orchestrator escalation loop.

## Layer 3 — Accountability

Delivers the model's headline claim. The AccountabilityTrace cross-references all six entities by identifier, verified end-to-end in the synthetic test included with the ER-model-alignment PRD. The Principal can invoke an override via post-hoc revocation. Mid-flight halt is the only deployment-dependent piece, and the `OverridePolicy.principal_halt_enabled` flag is the explicit hook for deployments that wire one in.


# What the implementation provides beyond the diagram

The diagram is principal-authorization-flavored. It omits the enforcement layer that the framework actually uses. The implementation adds the following framework contributions, which are consistent with the diagram and live below its level of abstraction.

**ComplianceAgent.** First-class gatekeeper with three checkpoints — CP1 routing, CP2 analysis, CP3 synthesis — and a revision loop.

**ComplianceVerdict.** Typed output at every checkpoint.

**RegulatoryRule registry.** Canonical machine-readable rule table backing the Boundary checks, in `agents/regulatory_rules.py`.

**MCPMessage.** Explicit message bus over which the orchestrator and compliance agent communicate.

**DispositionProfile.** Adversarial behavior model used to test enforcement under pressure.

These are documented from section 3.4 onward in the paper.


# Remaining gaps

**Multi-tenant Principal-Mandate delegation.** Severity low. Per-principal mandates are not modeled; each session uses the global manifests. Add a `mandate_overrides_by_principal` registry if a deployment needs it.

**1:N Mandate carries DecisionRight.** Severity low. Promote `decision_right` to a list of grants with context filters if a deployment needs it.

**Mid-flight principal halt.** Documented out-of-scope. Requires asynchronous task restructure. The flag `OverridePolicy.principal_halt_enabled=False` is intentional.

**Cryptographic tamper-evidence on the trace.** Documented in paper section 3.6. Hash chain or external WORM store at deployment time.

**Agent sub-delegates Agent as a separate relationship.** Documented in `PRD-er-model-alignment.md`, Item 3. Diverges from `sub_mandate_ids` only when Agent and Mandate are not 1:1.

None of these are framework defects. Each is either a deployment-time concern, a documented prototype scope decision, or a multiplicity choice that is defensible for the current use case.


# Bottom line

The implementation now satisfies the diagram's three-layer model.

Layer 1 is fully populated. The only imperfection is the ER granularity choice on DecisionRight.

Layer 2 is fully aligned. All three constraint entities are typed, populated, and enforced.

Layer 3 delivers the headline claim that the AccountabilityTrace cross-references every constraint and override entity by identifier, enabling full provenance reconstruction.

The `referenced_entities` block emitted by `_generate_trace()` is the single artifact most worth showing to a reviewer. It makes the diagram's caption — "enabling full provenance reconstruction" — concretely demonstrable rather than aspirational.
