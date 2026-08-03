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

# Term vocabularies used by term-based predicates (canonical source).
ESG_SYNONYMS: list[str] = [
    "esg", "environmental", "social responsibility", "governance",
    "sustainable", "sustainability", "responsible investing",
    "carbon", "emission", "climate", "ethical", "socially responsible",
    "green bond", "impact invest", "corporate responsibility",
]
LADDER_SYNONYMS: list[str] = [
    "ladder", "laddered", "stagger", "spread maturit",
    "maturity structure", "maturity schedule", "maturity bucket",
    "rolling maturit", "bond maturit", "diversif", "spread across",
    "year treasur", "year bond", "short-term", "medium-term", "long-term",
]
INFLATION_SYNONYMS: list[str] = [
    "inflation", "cpi", "purchasing power", "price stability", "real return",
    "hedge against", "store of value", "safe haven", "monetary policy",
    "currency debasement", "cost of living", "price increase",
    "correlat", "inverse", "protect",
]

_NEGATION_DETAIL = (
    "Found term '{term}' but negation_context_detected — "
    "agent is declining/warning, not recommending"
)


class Predicate(BaseModel):
    """φ — a machine-evaluable predicate over an agent's candidate output.

    Encoded as data so the Compliance Agent can evaluate it generically.
    Three kinds cover every manifest boundary constraint:
      - max_threshold: fail (φ satisfied) if any extracted value exceeds a bound
      - forbidden_term: φ satisfied if a forbidden term appears (non-negated)
      - required_term:  φ satisfied if a required disclosure term appears
    """

    kind: Literal["max_threshold", "forbidden_term", "required_term"]
    variable: str                          # the subject of φ, e.g. "single_position_allocation"
    source_field: str = "analysis"         # which payload field carries the output

    # max_threshold
    risk_param_key: str | None = None      # key into manifest.risk_parameters → the bound
    extract: Literal["percent", "duration_years"] | None = None
    exceed_label: str | None = None        # detail prefix, e.g. "Positions", "Durations"

    # forbidden_term
    term_pattern: str | None = None        # regex source
    on_lower: bool = False                 # search text.lower() instead of raw text
    ignorecase: bool = True
    negation_aware: bool = False           # suppress matches inside a 15-word negation window
    found_template: str | None = None      # detail when term found (uses {term})
    clean_template: str | None = None      # detail when no term found
    negation_template: str | None = None   # detail when found but negated (uses {term})

    # required_term
    synonyms: list[str] | None = None      # any-present satisfies φ
    present_template: str | None = None    # detail when present
    absent_template: str | None = None     # detail when absent


class BoundaryConstraint(BaseModel):
    """The triple ⟨text, φ, τ⟩ — one manifest boundary constraint."""

    rule_id: str                           # links to a RegulatoryRule
    agent_id: str
    text: str                              # ⟨text⟩ — natural-language statement
    predicate: Predicate                   # ⟨φ⟩ — machine-evaluable predicate
    deontic_type: Literal["F", "O"]        # ⟨τ⟩ — prohibition (F) or obligation (O)
    regulatory_basis: str


BOUNDARY_CONSTRAINTS: list[BoundaryConstraint] = [
    # ---- Stocks (order preserved from the legacy checker) ----
    BoundaryConstraint(
        rule_id="MANIFEST_STOCKS_NO_LEVERAGE", agent_id="stocks",
        text="No margin trading, short selling, or leveraged equity products",
        deontic_type="F", regulatory_basis="AgentManifest.stocks",
        predicate=Predicate(
            kind="forbidden_term", variable="leverage_instrument",
            term_pattern=r"\b(margin|leverag|short\s*sell|short\s*position|derivative|futures?\b)",
            negation_aware=True,
            found_template="Found forbidden term: '{term}'",
            clean_template="No leverage terms found",
            negation_template=_NEGATION_DETAIL,
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_STOCKS_MAX_POSITION", agent_id="stocks",
        text="Maximum 10% allocation to any single equity position",
        deontic_type="F", regulatory_basis="AgentManifest.stocks",
        predicate=Predicate(
            kind="max_threshold", variable="single_position_allocation",
            risk_param_key="max_single_position", extract="percent",
            exceed_label="Positions",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_STOCKS_ESG", agent_id="stocks",
        text="ESG screening required: must flag ESG concerns for any new position",
        deontic_type="O", regulatory_basis="AgentManifest.stocks",
        predicate=Predicate(
            kind="required_term", variable="esg_disclosure",
            synonyms=ESG_SYNONYMS,
            present_template="ESG screening present",
            absent_template="No ESG screening language found in analysis",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_STOCKS_LARGECAP", agent_id="stocks",
        text="Large-cap equities only: market capitalization must exceed $10 billion",
        deontic_type="F", regulatory_basis="AgentManifest.stocks",
        predicate=Predicate(
            kind="forbidden_term", variable="market_cap_tier",
            term_pattern=r"\b(mid[- ]?cap|small[- ]?cap|micro[- ]?cap|penny stock|otc)\b",
            on_lower=True, ignorecase=False,
            found_template="Found non-large-cap reference: '{term}'",
            clean_template="No non-large-cap references",
        ),
    ),
    # ---- Bonds ----
    BoundaryConstraint(
        rule_id="MANIFEST_BONDS_IG_ONLY", agent_id="bonds",
        text="Investment grade only: minimum credit rating BBB+",
        deontic_type="F", regulatory_basis="AgentManifest.bonds",
        predicate=Predicate(
            kind="forbidden_term", variable="credit_rating",
            term_pattern=r"\b(BB[+-]?|B[+-]?|CCC|CC|C\b|junk|high[- ]yield)\b",
            found_template="Found sub-investment-grade reference: '{term}'",
            clean_template="No sub-investment-grade references",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_BONDS_MAX_DURATION", agent_id="bonds",
        text="Portfolio duration must remain below 10 years",
        deontic_type="F", regulatory_basis="AgentManifest.bonds",
        predicate=Predicate(
            kind="max_threshold", variable="duration_years",
            risk_param_key="max_duration_years", extract="duration_years",
            exceed_label="Durations",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds",
        text="No more than 30% maturing in any single year",
        deontic_type="F", regulatory_basis="AgentManifest.bonds",
        predicate=Predicate(
            kind="max_threshold", variable="single_maturity_bucket",
            risk_param_key="max_single_maturity_bucket", extract="percent",
            exceed_label="Buckets",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_BONDS_NO_EM", agent_id="bonds",
        text="No emerging market sovereign or corporate debt",
        deontic_type="F", regulatory_basis="AgentManifest.bonds",
        predicate=Predicate(
            kind="forbidden_term", variable="emerging_market_debt",
            term_pattern=r"\b(emerging market|em debt|frontier market|developing countr)",
            on_lower=True, ignorecase=False,
            found_template="Found emerging market reference: '{term}'",
            clean_template="No emerging market references",
        ),
    ),
    # Second obligation carried by the ladder rule: the structure must be present.
    # Legitimately shares rule_id MANIFEST_BONDS_LADDER (violated_rules dedupes).
    BoundaryConstraint(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds",
        text="Laddered maturity structure required",
        deontic_type="O", regulatory_basis="AgentManifest.bonds",
        predicate=Predicate(
            kind="required_term", variable="ladder_structure",
            synonyms=LADDER_SYNONYMS,
            present_template="Maturity ladder structure discussed",
            absent_template="No laddered maturity language found in analysis",
        ),
    ),
    # ---- Materials ----
    BoundaryConstraint(
        rule_id="MANIFEST_MATERIALS_APPROVED", agent_id="materials",
        text="Direct exposure permitted for Gold and Silver only",
        deontic_type="F", regulatory_basis="AgentManifest.materials",
        predicate=Predicate(
            kind="forbidden_term", variable="commodity_type",
            term_pattern=r"\b(oil|crude|natural\s*gas|copper|platinum|palladium|wheat|corn|soybean|crypto|bitcoin|ethereum)\b",
            negation_aware=True,
            found_template="Found non-approved commodity: '{term}'",
            clean_template="Only approved commodities referenced",
            negation_template=_NEGATION_DETAIL,
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_MATERIALS_MAX_ALLOC", agent_id="materials",
        text="Maximum 15% of total portfolio in raw materials",
        deontic_type="F", regulatory_basis="AgentManifest.materials",
        predicate=Predicate(
            kind="max_threshold", variable="total_materials_allocation",
            risk_param_key="max_total_allocation", extract="percent",
            exceed_label="Allocations",
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_MATERIALS_NO_LEVERAGE", agent_id="materials",
        text="No leveraged commodity ETFs or futures contracts",
        deontic_type="F", regulatory_basis="AgentManifest.materials",
        predicate=Predicate(
            kind="forbidden_term", variable="leverage_instrument",
            term_pattern=r"\b(margin|leverag|short\s*sell|short\s*position|derivative|futures?\b)",
            negation_aware=True,
            found_template="Found forbidden term: '{term}'",
            clean_template="No leverage terms found",
            negation_template=_NEGATION_DETAIL,
        ),
    ),
    BoundaryConstraint(
        rule_id="MANIFEST_MATERIALS_INFLATION", agent_id="materials",
        text="Must provide inflation correlation rationale for every recommendation",
        deontic_type="O", regulatory_basis="AgentManifest.materials",
        predicate=Predicate(
            kind="required_term", variable="inflation_rationale",
            synonyms=INFLATION_SYNONYMS,
            present_template="Inflation rationale present",
            absent_template="No inflation rationale found in analysis",
        ),
    ),
    # ---- Central (synthesis checkpoint) ----
    BoundaryConstraint(
        rule_id="MANIFEST_CENTRAL_MAX_ASSET_CLASS", agent_id="central",
        text="Maximum 40% allocation to any single asset class",
        deontic_type="F", regulatory_basis="AgentManifest.central",
        predicate=Predicate(
            kind="max_threshold", variable="single_asset_class_allocation",
            risk_param_key="max_single_asset_class", extract="percent",
            exceed_label="Asset class allocations",
            source_field="final_recommendation",
        ),
    ),
]

BOUNDARY_CONSTRAINT_INDEX: dict[str, list[BoundaryConstraint]] = {}
for _bc in BOUNDARY_CONSTRAINTS:
    BOUNDARY_CONSTRAINT_INDEX.setdefault(_bc.agent_id, []).append(_bc)


def get_boundary_constraints_for_agent(agent_id: str) -> list[BoundaryConstraint]:
    """Return the ⟨text, φ, τ⟩ boundary constraints for an agent, in checker order."""
    return BOUNDARY_CONSTRAINT_INDEX.get(agent_id, [])
