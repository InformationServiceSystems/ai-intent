"""Single source for boundary constraints: a ConstraintSpec renders the manifest text, the predicate and the registry entry.

The ER 2026 paper's limitation "specification-predicate consistency" arose because the
natural-language text and the machine-evaluable predicate of a boundary constraint were
written separately. Here each constraint is one specification from which both are
generated, with every number taken from the agent's risk parameters. The design follows
the Object-Role Modeling principle of verbalising a constraint from its formal form,
without the ORM tooling.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Term vocabularies used by term-based predicates (canonical source)
# ---------------------------------------------------------------------------

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

NEGATION_DETAIL = (
    "Found term '{term}' but negation_context_detected — "
    "agent is declining/warning, not recommending"
)

_LEVERAGE_PATTERN = r"\b(margin|leverag|short\s*sell|short\s*position|derivative|futures?\b)"
_LEVERAGE_TERMS = ["margin", "leverage", "short selling", "derivatives", "futures"]


# ---------------------------------------------------------------------------
# The triple <text, phi, tau> as evaluated by the Compliance Agent
# ---------------------------------------------------------------------------

class Predicate(BaseModel):
    """phi: a machine-evaluable predicate over an agent's candidate output, encoded as data."""

    kind: Literal["max_threshold", "min_threshold", "in_set", "not_in_set", "required_field", "forbidden_term", "required_term"]
    variable: str                          # the subject of phi, e.g. "single_position_allocation"
    source_field: str = "analysis"         # which payload field carries the output

    # Structured evaluation: every kind reads a typed field of the payload first and
    # falls back to the prose mechanism (term pattern, synonyms, regex) when absent.
    structured_field: str | None = None    # top-level key: a number, a string, a dict or a list of items
    item_key: str | None = None            # key inside each list item, e.g. "name", "market_cap_usd"
    group_key: str | None = None           # sum item_key per value of this key (e.g. allocation per maturity year)
    set_param_key: str | None = None       # risk parameter holding the allowed set (in_set)
    forbidden_values: list[str] | None = None   # substrings that make an item value forbidden (not_in_set)
    value_scale: Literal["credit_rating"] | None = None   # ordinal scale for min_threshold on strings
    min_items: int = 1                     # required_field on a list: distinct values needed

    # max_threshold
    risk_param_key: str | None = None      # key into manifest.risk_parameters -> the bound
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
    synonyms: list[str] | None = None      # any-present satisfies phi
    present_template: str | None = None    # detail when present
    absent_template: str | None = None     # detail when absent


class BoundaryConstraint(BaseModel):
    """The triple <text, phi, tau>: one manifest boundary constraint."""

    rule_id: str                           # links to a RegulatoryRule
    agent_id: str
    text: str                              # <text>: natural-language statement, generated
    predicate: Predicate                   # <phi>: machine-evaluable predicate
    deontic_type: Literal["F", "O"]        # <tau>: prohibition (F) or obligation (O)
    regulatory_basis: str


# ---------------------------------------------------------------------------
# The specification both are generated from
# ---------------------------------------------------------------------------

class ConstraintSpec(BaseModel):
    """One boundary constraint as a single specification: template plus formal content.

    The template may use {value} (the bound from the risk parameter, formatted per unit),
    {terms} (the plain forbidden terms, joined), and any risk parameter by name, with
    list-valued parameters joined by "and" and parameters ending in "_threshold" also
    available as {<name>_billions}.
    """

    rule_id: str
    agent_id: str
    variable: str
    kind: Literal["max", "min", "in_set", "not_in_set", "required_field", "forbid", "require"]
    deontic_type: Literal["F", "O"]
    regulatory_basis: str
    template: str
    source_field: str = "analysis"

    # structured evaluation; the forbid / require fields below are the prose fallback
    structured_field: str | None = None
    item_key: str | None = None
    group_key: str | None = None
    set_param_key: str | None = None
    forbidden_values: list[str] | None = None
    value_scale: Literal["credit_rating"] | None = None
    min_items: int = 1

    # max
    risk_param_key: str | None = None
    unit: Literal["percent", "years"] | None = None
    exceed_label: str | None = None

    # forbid
    terms: list[str] | None = None          # plain terms named in the text
    term_pattern: str | None = None         # regex the gate applies
    on_lower: bool = False
    ignorecase: bool = True
    negation_aware: bool = False
    found_template: str | None = None
    clean_template: str | None = None

    # require
    synonyms: list[str] | None = None
    present_template: str | None = None
    absent_template: str | None = None


def _join(items: list[str], last: str = "and") -> str:
    """Join a list as 'a, b and c'."""
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {last} " + items[-1]


def _format_number(value: float) -> str:
    """Format a bound without a trailing .0."""
    return f"{value:g}"


def render_context(spec: ConstraintSpec, risk_parameters: dict[str, Any]) -> dict[str, str]:
    """Build the placeholder values for a spec's template from the risk parameters."""
    ctx: dict[str, str] = {}
    for key, raw in risk_parameters.items():
        if isinstance(raw, list):
            ctx[key] = _join([str(x) for x in raw])
        elif isinstance(raw, bool):
            ctx[key] = "permitted" if raw else "not permitted"
        elif isinstance(raw, (int, float)):
            ctx[key] = _format_number(float(raw))
            if key.endswith("_threshold") and float(raw) >= 1e9:
                ctx[f"{key}_billions"] = _format_number(float(raw) / 1e9)
        else:
            ctx[key] = str(raw)
    if spec.risk_param_key and spec.unit:
        bound = float(risk_parameters[spec.risk_param_key])
        ctx["value"] = _format_number(bound * 100) if spec.unit == "percent" else _format_number(bound)
    if spec.terms:
        ctx["terms"] = _join(spec.terms, last="or")
    return ctx


def render_text(spec: ConstraintSpec, risk_parameters: dict[str, Any]) -> str:
    """Verbalise the constraint: the text the agent sees and the gate cites."""
    return spec.template.format(**render_context(spec, risk_parameters))


def to_predicate(spec: ConstraintSpec) -> Predicate:
    """Derive the predicate the Compliance Agent evaluates; every spec kind maps to one predicate kind."""
    kind = {"max": "max_threshold", "min": "min_threshold", "in_set": "in_set", "not_in_set": "not_in_set",
            "required_field": "required_field", "forbid": "forbidden_term", "require": "required_term"}[spec.kind]
    return Predicate(
        kind=kind, variable=spec.variable, source_field=spec.source_field,
        structured_field=spec.structured_field, item_key=spec.item_key, group_key=spec.group_key,
        set_param_key=spec.set_param_key, forbidden_values=spec.forbidden_values,
        value_scale=spec.value_scale, min_items=spec.min_items,
        risk_param_key=spec.risk_param_key,
        extract=(None if spec.unit is None else ("percent" if spec.unit == "percent" else "duration_years")),
        exceed_label=spec.exceed_label,
        term_pattern=spec.term_pattern, on_lower=spec.on_lower, ignorecase=spec.ignorecase,
        negation_aware=spec.negation_aware,
        found_template=spec.found_template, clean_template=spec.clean_template,
        negation_template=NEGATION_DETAIL if spec.negation_aware else None,
        synonyms=spec.synonyms, present_template=spec.present_template, absent_template=spec.absent_template,
    )


def to_boundary_constraint(spec: ConstraintSpec, risk_parameters: dict[str, Any]) -> BoundaryConstraint:
    """Produce the registry entry: generated text, derived predicate, deontic type."""
    return BoundaryConstraint(
        rule_id=spec.rule_id, agent_id=spec.agent_id,
        text=render_text(spec, risk_parameters), predicate=to_predicate(spec),
        deontic_type=spec.deontic_type, regulatory_basis=spec.regulatory_basis,
    )


# ---------------------------------------------------------------------------
# The fourteen specifications, in the order the Compliance Agent evaluates them
# ---------------------------------------------------------------------------

CONSTRAINT_SPECS: list[ConstraintSpec] = [
    # ---- Stocks ----
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_NO_LEVERAGE", agent_id="stocks", variable="leverage_instrument",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.stocks",
        template="No margin trading, short selling, or leveraged equity products",
        structured_field="positions", item_key="instrument", forbidden_values=["margin", "short", "leverag", "futures", "derivative", "option", "swap", "cfd"],
        terms=_LEVERAGE_TERMS, term_pattern=_LEVERAGE_PATTERN, negation_aware=True,
        found_template="Found forbidden term: '{term}'", clean_template="No leverage terms found",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_MAX_POSITION", agent_id="stocks", variable="single_position_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.stocks",
        template="Maximum {value}% allocation to any single equity position",
        risk_param_key="max_single_position", unit="percent", exceed_label="Positions",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_ESG", agent_id="stocks", variable="esg_disclosure",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.stocks",
        template="ESG screening required: must flag ESG concerns for any new position",
        structured_field="positions", item_key="esg_assessment",
        synonyms=ESG_SYNONYMS, present_template="ESG screening present",
        absent_template="No ESG screening language found in analysis",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_LARGECAP", agent_id="stocks", variable="market_cap_usd",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.stocks",
        template="Large-cap equities only: market capitalization must exceed ${max_market_cap_threshold_billions} billion; {terms} equities are outside the universe",
        structured_field="positions", item_key="market_cap_usd", risk_param_key="max_market_cap_threshold",
        exceed_label="Positions below the market-cap floor",
        terms=["mid-cap", "small-cap", "micro-cap", "penny stock", "OTC"],
        term_pattern=r"\b(mid[- ]?cap|small[- ]?cap|micro[- ]?cap|penny stock|otc)\b", on_lower=True, ignorecase=False,
        found_template="Found non-large-cap reference: '{term}'", clean_template="No non-large-cap references",
    ),
    # ---- Bonds ----
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_IG_ONLY", agent_id="bonds", variable="credit_rating",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.bonds",
        template="Investment grade only: minimum credit rating {min_credit_rating} (S&P) or Baa1 (Moody's); {terms} debt is not permitted",
        structured_field="holdings", item_key="credit_rating", risk_param_key="min_credit_rating",
        value_scale="credit_rating", exceed_label="Holdings below the rating floor",
        terms=["BB", "B", "CCC", "CC", "C", "junk", "high-yield"],
        term_pattern=r"\b(BB[+-]?|B[+-]?|CCC|CC|C\b|junk|high[- ]yield)\b",
        found_template="Found sub-investment-grade reference: '{term}'", clean_template="No sub-investment-grade references",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_MAX_DURATION", agent_id="bonds", variable="duration_years",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.bonds",
        template="Portfolio duration must remain below {value} years",
        structured_field="portfolio_duration_years",
        risk_param_key="max_duration_years", unit="years", exceed_label="Durations",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds", variable="single_maturity_bucket",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.bonds",
        template="Laddered maturity structure required: no more than {value}% maturing in any single year",
        structured_field="holdings", item_key="allocation", group_key="maturity_years",
        risk_param_key="max_single_maturity_bucket", unit="percent", exceed_label="Buckets",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_NO_EM", agent_id="bonds", variable="emerging_market_debt",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.bonds",
        template="No emerging market sovereign or corporate debt",
        structured_field="holdings", item_key="region", forbidden_values=["emerging", "frontier", "developing"],
        terms=["emerging market", "EM debt", "frontier market", "developing country"],
        term_pattern=r"\b(emerging market|em debt|frontier market|developing countr)", on_lower=True, ignorecase=False,
        found_template="Found emerging market reference: '{term}'", clean_template="No emerging market references",
    ),
    # Second obligation carried by the ladder rule: the structure must be present.
    # Shares rule_id MANIFEST_BONDS_LADDER and its text (violated_rules dedupes).
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds", variable="ladder_structure",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.bonds",
        template="Laddered maturity structure required: no more than {value}% maturing in any single year",
        structured_field="holdings", item_key="maturity_years", min_items=2,
        risk_param_key="max_single_maturity_bucket", unit="percent",
        synonyms=LADDER_SYNONYMS, present_template="Maturity ladder structure discussed",
        absent_template="No laddered maturity language found in analysis",
    ),
    # ---- Materials ----
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_APPROVED", agent_id="materials", variable="commodity_type",
        kind="in_set", deontic_type="F", regulatory_basis="AgentManifest.materials",
        template="Direct exposure permitted for {approved_commodities} only; {terms} are not permitted",
        structured_field="commodities", item_key="name", set_param_key="approved_commodities",
        terms=["oil", "crude", "natural gas", "copper", "platinum", "palladium", "wheat", "corn", "soybeans", "crypto assets"],
        term_pattern=r"\b(oil|crude|natural\s*gas|copper|platinum|palladium|wheat|corn|soybean|crypto|bitcoin|ethereum)\b",
        negation_aware=True,
        found_template="Found non-approved commodity: '{term}'", clean_template="Only approved commodities referenced",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_MAX_ALLOC", agent_id="materials", variable="total_materials_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.materials",
        template="Maximum {value}% of total portfolio in raw materials",
        risk_param_key="max_total_allocation", unit="percent", exceed_label="Allocations",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_NO_LEVERAGE", agent_id="materials", variable="leverage_instrument",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.materials",
        template="No leveraged commodity ETFs or futures contracts",
        structured_field="commodities", item_key="instrument", forbidden_values=["margin", "short", "leverag", "futures", "derivative", "option", "swap", "cfd"],
        terms=_LEVERAGE_TERMS, term_pattern=_LEVERAGE_PATTERN, negation_aware=True,
        found_template="Found forbidden term: '{term}'", clean_template="No leverage terms found",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_INFLATION", agent_id="materials", variable="inflation_rationale",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.materials",
        template="Must provide inflation correlation rationale for every recommendation",
        structured_field="inflation_rationale",
        synonyms=INFLATION_SYNONYMS, present_template="Inflation rationale present",
        absent_template="No inflation rationale found in analysis",
    ),
    # ---- Central (synthesis checkpoint) ----
    ConstraintSpec(
        rule_id="MANIFEST_CENTRAL_MAX_ASSET_CLASS", agent_id="central", variable="single_asset_class_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.central",
        template="Maximum {value}% allocation to any single asset class",
        structured_field="allocation_by_asset_class",
        risk_param_key="max_single_asset_class", unit="percent", exceed_label="Asset class allocations",
        source_field="final_recommendation",
    ),
]


def specs_for(agent_id: str) -> list[ConstraintSpec]:
    """Return the specifications of an agent in evaluation order."""
    return [s for s in CONSTRAINT_SPECS if s.agent_id == agent_id]


def generated_text(rule_id: str, risk_parameters: dict[str, Any]) -> str:
    """Return the manifest text of a rule, rendered from its specification and the risk parameters."""
    spec = next(s for s in CONSTRAINT_SPECS if s.rule_id == rule_id)
    return render_text(spec, risk_parameters)
