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
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART25_LEVERAGE",
        description="Any recommendation involving leveraged instruments must be blocked unless the client risk profile explicitly permits it.",
        applies_to=["stocks", "bonds", "materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="MiFID II Art. 25 — Product Governance / Leverage",
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART24_SCOPE",
        description="Out-of-scope asset class recommendations must be blocked entirely — an agent recommending assets outside its mandate is a regulatory violation.",
        applies_to=["stocks", "bonds", "materials"],
        check_type="both",
        severity="block",
        regulatory_basis="MiFID II Art. 24 — Fair, Clear and Not Misleading",
    ),
    RegulatoryRule(
        rule_id="MIFID2_ART24_RATIONALE",
        description="All recommendations must include a rationale traceable to a stated investment objective.",
        applies_to=["stocks", "bonds", "materials", "central"],
        check_type="semantic",
        severity="block",
        regulatory_basis="MiFID II Art. 24 — Information to Clients",
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
        description="No margin trading, short selling, or leveraged equity products.",
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
        rule_id="MANIFEST_STOCKS_UNIVERSE",
        description="Must decline analysis of any equity outside the approved universe.",
        applies_to=["stocks"],
        check_type="semantic",
        severity="block",
        regulatory_basis="AgentManifest.stocks",
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
        description="No emerging market sovereign or corporate debt.",
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
        description="Must flag any recommendation that would increase overall portfolio duration above 7 years.",
        applies_to=["bonds"],
        check_type="semantic",
        severity="warn",
        regulatory_basis="AgentManifest.bonds",
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
        description="No leveraged commodity ETFs or futures contracts.",
        applies_to=["materials"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.materials",
    ),
    RegulatoryRule(
        rule_id="MANIFEST_MATERIALS_REBALANCE",
        description="Rebalancing trigger: flag to orchestrator if allocation drifts more than ±5% from target.",
        applies_to=["materials"],
        check_type="semantic",
        severity="warn",
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
    ),
    RegulatoryRule(
        rule_id="MANIFEST_CENTRAL_SURFACE_VIOLATIONS",
        description="Must surface constraint violations from sub-agents rather than suppressing them.",
        applies_to=["central"],
        check_type="deterministic",
        severity="block",
        regulatory_basis="AgentManifest.central",
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
    ),
]


# ---------------------------------------------------------------------------
# Aggregate registry
# ---------------------------------------------------------------------------

ALL_RULES: list[RegulatoryRule] = MIFID2_RULES + STOCKS_RULES + BONDS_RULES + MATERIALS_RULES + CENTRAL_RULES

RULE_REGISTRY: dict[str, RegulatoryRule] = {r.rule_id: r for r in ALL_RULES}


def get_rules_for_agent(agent_id: str) -> list[RegulatoryRule]:
    """Return all rules that apply to a given agent."""
    return [r for r in ALL_RULES if agent_id in r.applies_to]


def get_rule(rule_id: str) -> RegulatoryRule:
    """Return a rule by ID, raising KeyError if not found."""
    if rule_id not in RULE_REGISTRY:
        raise KeyError(f"Unknown rule_id: {rule_id!r}")
    return RULE_REGISTRY[rule_id]
