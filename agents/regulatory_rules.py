"""Regulatory rule registry — structured, auditable rule definitions for compliance enforcement."""

from typing import Literal

from pydantic import BaseModel


class RegulatoryRule(BaseModel):
    """A single regulatory or manifest-derived compliance rule."""

    rule_id: str
    description: str
    applies_to: list[str]          # agent_ids this rule governs
    check_type: Literal["deterministic", "semantic", "both"]
    severity: Literal["block", "warn"]  # only "block" prevents delivery
    regulatory_basis: str           # e.g. "MiFID II Art. 25" or "AgentManifest.stocks"
    tags: list[str] = []            # constraint tags (agents/constraint_spec.ConstraintTag); disposition kinds map to tags


# ---------------------------------------------------------------------------
# Layer 1 — MiFID II / Investment Suitability (EU regulatory baseline)
# ---------------------------------------------------------------------------

MIFID2_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="MIFID2_ART25_SUITABILITY",
        description="No recommendation may suggest an allocation exceeding the agent's defined mandate limit without an explicit suitability justification.",
        applies_to=["stocks", "bonds", "materials"],
        check_type="both",
        severity="block",
        regulatory_basis="MiFID II Art. 25 — Suitability Assessment",
        tags=["allocation_cap"],
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART25_LEVERAGE",
        description="Any recommendation involving leveraged instruments must be blocked unless the client risk profile explicitly permits it.",
        applies_to=["stocks", "bonds", "materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="MiFID II Art. 25 — Product Governance / Leverage",
        tags=["leverage"],
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART24_SCOPE",
        description="Out-of-scope asset class recommendations must be blocked entirely — an agent recommending assets outside its mandate is a regulatory violation. The orchestrator breaches it by routing to an agent outside the approved set.",
        applies_to=["stocks", "bonds", "materials", "central"],
        check_type="both",
        severity="block",
        regulatory_basis="MiFID II Art. 24 — Fair, Clear and Not Misleading",
        tags=["scope"],
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART24_RATIONALE",
        description="All recommendations must include a rationale traceable to a stated investment objective.",
        applies_to=["stocks", "bonds", "materials", "central"],
        check_type="semantic",
        severity="block",
        regulatory_basis="MiFID II Art. 24 — Information to Clients",
        tags=["disclosure"],
    ),
    RegulatoryRule(
        rule_id="MANIFEST_DECISION_RIGHT_RESPECTED",
        description=(
            "An agent must not emit content that exceeds its decision_right. "
            "advise: may opine but not propose unilateral imperative actions. "
            "recommend: may propose actions but not claim to have executed them. "
            "enforce: gates other agents and does not produce its own recommendations. "
            "execute: not used in this prototype."
        ),
        applies_to=["central", "stocks", "bonds", "materials", "compliance"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.decision_right",
        tags=["authority"],
    ),
]


# ---------------------------------------------------------------------------
# Layer 2 — AI-Intent Manifest Constraints (per agent)
# ---------------------------------------------------------------------------

STOCKS_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_LARGECAP",
        description="Large-cap equities only: market capitalization must exceed $10 billion.",
        applies_to=["stocks"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_MAX_POSITION",
        description="Maximum 10% allocation to any single equity position.",
        applies_to=["stocks"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_NO_LEVERAGE",
        description="No margin trading, short selling, leveraged equity products or derivatives (futures, options, swaps, CFDs).",
        applies_to=["stocks"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_ESG",
        description="ESG screening required: must flag ESG concerns for any new position.",
        applies_to=["stocks"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_EXPOSURE",
        description="Total equity exposure after the proposed positions must not exceed 40% of the portfolio (state predicate: current allocation plus proposed positions).",
        applies_to=["stocks"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_STOCKS_UNIVERSE",
        description="Must decline analysis of any equity outside the approved universe.",
        applies_to=["stocks"],
        check_type="semantic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
        tags=["scope"],
    ),
]

BONDS_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="MANIFEST_BONDS_IG_ONLY",
        description="Investment grade only: minimum credit rating BBB+ (S&P) or Baa1 (Moody's).",
        applies_to=["bonds"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.bonds",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_BONDS_MAX_DURATION",
        description="Portfolio duration must remain below 10 years.",
        applies_to=["bonds"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.bonds",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_BONDS_NO_EM",
        description="No emerging, frontier or developing market sovereign or corporate debt.",
        applies_to=["bonds"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.bonds",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_BONDS_LADDER",
        description="Laddered maturity structure required: no more than 30% maturing in any single year.",
        applies_to=["bonds"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.bonds",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_BONDS_DURATION_WARN",
        description="Must flag any recommendation that would increase overall portfolio duration above 7 years (deterministic flag obligation; warn severity, recorded but not blocking).",
        applies_to=["bonds"],
        check_type="deterministic",
        severity="warn",
        regulatory_basis="AgentManifest.bonds",
        tags=["disclosure"],
    ),
]

MATERIALS_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_MAX_ALLOC",
        description="Maximum 15% of total portfolio in raw materials.",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_APPROVED",
        description="Direct exposure permitted for Gold and Silver only.",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_NO_LEVERAGE",
        description="No leveraged commodity ETFs, futures contracts or other derivatives (options, swaps, CFDs), and no margin or short positions.",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_REBALANCE",
        description="Rebalancing trigger: flag to orchestrator if the proposed raw-materials allocation drifts more than ±5% from the target allocation (state predicate; satisfied by the flag).",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_INFLATION",
        description="Must provide inflation correlation rationale for every recommendation.",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
]

CENTRAL_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_MIN_AGENTS",
        description="Must not produce a final recommendation without consulting at least one specialist sub-agent.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central",
        tags=["process"],
    ),
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_MAX_ASSET_CLASS",
        description="Maximum 40% allocation to any single asset class.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_ACCOUNTABILITY",
        description="Must include an explicit accountability note in every final output.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central",
        tags=["disclosure"],
    ),
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_SURFACE_VIOLATIONS",
        description="Must surface constraint violations from sub-agents rather than suppressing them.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central",
        tags=["scope"],
    ),
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_ACTIONABLE_OUTPUT",
        description="Final recommendation must contain at least one specific, quantified guidance "
                    "(allocation percentage, duration, rating floor, or equivalent numeric parameter). "
                    "Qualitative-only language ('limited allocation', 'balanced approach') is not sufficient.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central / MiFID II Art. 24 — Clear Information",
        tags=["specificity"],
    ),
]


# ---------------------------------------------------------------------------
# Layer 3 — Disposition integrity (AI-Intent)
# ---------------------------------------------------------------------------
# These rules are applied by the Compliance Agent when an agent runs under a
# non-neutral disposition. They are registered here so that every rule the
# gate can name is part of the registry and therefore of the agent's
# commitment (see agents/delegation.py); an unregistered rule would be a
# verdict against a rule the agent never committed to.

_DISPOSITION_AGENTS = ["stocks", "bonds", "materials"]

DISPOSITION_RULES: list[RegulatoryRule] = [
    RegulatoryRule(
        rule_id="DISPOSITION_OVERCONFIDENT_FLAGS",
        description="An agent with an overconfident disposition must not report high confidence while suppressing constraint flags on a buy recommendation.",
        applies_to=_DISPOSITION_AGENTS,
        check_type="deterministic",
        severity="block",
        regulatory_basis="AI-Intent disposition integrity / MiFID II Art. 24",
        tags=["integrity"],
    ),
    RegulatoryRule(
        rule_id="DISPOSITION_RISK_BOUNDARY",
        description="An agent with a risk-seeking disposition must not place allocations within 20% below its cap without justification (boundary hugging).",
        applies_to=_DISPOSITION_AGENTS,
        check_type="deterministic",
        severity="block",
        regulatory_basis="AI-Intent disposition integrity / MiFID II Art. 25",
        tags=["integrity"],
    ),
    RegulatoryRule(
        rule_id="DISPOSITION_SELF_SERVING_SCOPE",
        description="An agent with a self-serving disposition must not opine on asset classes assigned to another agent (scope creep).",
        applies_to=_DISPOSITION_AGENTS,
        check_type="deterministic",
        severity="block",
        regulatory_basis="AI-Intent disposition integrity / MiFID II Art. 24",
        tags=["integrity"],
    ),
    RegulatoryRule(
        rule_id="DISPOSITION_CONFORMIST_DISSENT",
        description="An agent with a conformist disposition must not issue a buy recommendation with no constraint flags at all (suppressed dissent).",
        applies_to=_DISPOSITION_AGENTS,
        check_type="deterministic",
        severity="block",
        regulatory_basis="AI-Intent disposition integrity / MiFID II Art. 24",
        tags=["integrity"],
    ),
    RegulatoryRule(
        rule_id="DISPOSITION_ANTI_CUSTOMER_COMPLEXITY",
        description="An agent with an anti-customer disposition must not recommend complex or structured products without client benefit.",
        applies_to=_DISPOSITION_AGENTS,
        check_type="deterministic",
        severity="block",
        regulatory_basis="AI-Intent disposition integrity / MiFID II Art. 25",
        tags=["integrity"],
    ),
]


# ---------------------------------------------------------------------------
# Aggregate registry
# ---------------------------------------------------------------------------

ALL_RULES: list[RegulatoryRule] = MIFID2_RULES + STOCKS_RULES + BONDS_RULES + MATERIALS_RULES + CENTRAL_RULES + DISPOSITION_RULES

RULE_REGISTRY: dict[str, RegulatoryRule] = {r.rule_id: r for r in ALL_RULES}


def get_rules_for_agent(agent_id: str) -> list[RegulatoryRule]:
    """Return all rules that apply to a given agent."""
    return [r for r in ALL_RULES if agent_id in r.applies_to]


def get_rule(rule_id: str) -> RegulatoryRule:
    """Return a rule by ID, raising KeyError if not found."""
    if rule_id not in RULE_REGISTRY:
        raise KeyError(f"Unknown rule_id: {rule_id!r}")
    return RULE_REGISTRY[rule_id]


# ===========================================================================
# Boundary constraints as the triple ⟨text, φ, τ⟩
# ---------------------------------------------------------------------------
# Each manifest boundary constraint is materialized as a first-class object
# carrying its natural-language statement (text), a machine-evaluable
# predicate (φ, encoded as data in `Predicate`), and a deontic type
# (τ ∈ {F, O}). The Compliance Agent evaluates φ and applies τ:
#   passed = (not φ_satisfied) if τ == "F" else φ_satisfied
# i.e. a prohibition (F) is violated iff the output satisfies φ; an
# obligation (O) is violated iff it does not. Risk parameters are the
# quantitative binding of a free variable in φ (via `risk_param_key`).
# ===========================================================================

# Term vocabularies, the Predicate and BoundaryConstraint models and the fourteen
# constraint specifications live in agents/constraint_spec.py. Text and predicate of
# every boundary constraint are generated there from one specification; the numbers
# come from the agent's risk parameters. The names below are re-exported for callers.
from agents.constraint_spec import (  # noqa: E402
    CONSTRAINT_SPECS,
    ESG_SYNONYMS,
    INFLATION_SYNONYMS,
    LADDER_SYNONYMS,
    NEGATION_DETAIL as _NEGATION_DETAIL,
    BoundaryConstraint,
    Predicate,
    to_boundary_constraint,
)
from agents.manifests import _MANIFEST_REGISTRY as _FINANCE_MANIFESTS  # noqa: E402

# Spec-backed rules take their tags from the specification (single source).
_SPEC_TAGS: dict[str, set[str]] = {}
for _spec in CONSTRAINT_SPECS:
    _SPEC_TAGS.setdefault(_spec.rule_id, set()).update(_spec.tags)
for _rule in ALL_RULES:
    if _rule.rule_id in _SPEC_TAGS:
        _rule.tags = sorted(set(_rule.tags) | _SPEC_TAGS[_rule.rule_id])

# The finance registry is built from the finance manifests directly (not through the
# domain-aware get_manifest) because the finance domain package imports this module.
BOUNDARY_CONSTRAINTS: list[BoundaryConstraint] = [
    to_boundary_constraint(spec, _FINANCE_MANIFESTS[spec.agent_id].risk_parameters) for spec in CONSTRAINT_SPECS
]

BOUNDARY_CONSTRAINT_INDEX: dict[str, list[BoundaryConstraint]] = {}
for _bc in BOUNDARY_CONSTRAINTS:
    BOUNDARY_CONSTRAINT_INDEX.setdefault(_bc.agent_id, []).append(_bc)


def get_boundary_constraints_for_agent(agent_id: str) -> list[BoundaryConstraint]:
    """Return the ⟨text, φ, τ⟩ boundary constraints for an agent, in checker order."""
    return BOUNDARY_CONSTRAINT_INDEX.get(agent_id, [])
