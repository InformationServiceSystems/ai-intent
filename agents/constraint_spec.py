"""Single source for boundary constraints: a ConstraintSpec renders the manifest text, the predicate, the registry entry and the response schema.

The ER 2026 paper's limitation "specification-predicate consistency" arose because the
natural-language text and the machine-evaluable predicate of a boundary constraint were
written separately. Here each constraint is one specification from which both are
generated, with every number taken from the agent's risk parameters. The design follows
the Object-Role Modeling principle of verbalising a constraint from its formal form,
without the ORM tooling.

Since ROADMAP 6.5 the specification also declares the typed field it reads, and the
specialist's response schema is derived from these declarations (agents/schemas.py).
Since ROADMAP 6.4 every specification carries tags that disposition kinds map to.
Since ROADMAP 1.1 two kinds compare the proposed action with the session state.
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
_LEVERAGE_VALUES = ["margin", "short", "leverag", "futures", "derivative", "option", "swap", "cfd"]

# Tags a specification may carry; disposition kinds map to tags (agents/dispositions.py).
ConstraintTag = Literal[
    "allocation_cap",   # a cap on a share of the portfolio or budget
    "exposure_cap",     # a cap on duration, horizon or another exposure measure
    "leverage",         # prohibition of leveraged or derivative instruments
    "disclosure",       # an obligation to state something (ESG, rationale, accountability)
    "scope",            # the agent's in-or-out boundary (universe, approved set)
    "quality_floor",    # a floor on credit quality or an equivalent
    "structure",        # a structural obligation (ladder, lots)
    "authority",        # decision rights
    "specificity",      # quantified, actionable output
    "process",          # orchestration process rules
    "monitoring",       # obligations to flag drift or thresholds
]


# ---------------------------------------------------------------------------
# The triple <text, phi, tau> as evaluated by the Compliance Agent
# ---------------------------------------------------------------------------

PredicateKind = Literal[
    "max_threshold", "min_threshold", "in_set", "not_in_set", "required_field",
    "forbidden_term", "required_term", "state_drift", "state_max", "flag_above",
]


class Predicate(BaseModel):
    """phi: a machine-evaluable predicate over an agent's candidate output, encoded as data."""

    kind: PredicateKind
    variable: str                          # the subject of phi, e.g. "single_position_allocation"
    source_field: str = "analysis"         # which payload field carries the output

    # Structured evaluation: every kind reads a typed field of the payload first and
    # falls back to the prose mechanism (term pattern, synonyms, regex) when absent.
    structured_field: str | None = None    # top-level key: a number, a string, a dict or a list of items
    item_key: str | None = None            # key inside each list item, e.g. "name", "market_cap_usd"
    group_key: str | None = None           # sum item_key per value of this key (e.g. allocation per maturity year)
    aggregate: Literal["sum"] | None = None  # sum item_key over all items into one value ("total")
    set_param_key: str | None = None       # risk parameter holding the allowed set (in_set)
    forbidden_values: list[str] | None = None   # substrings that make an item value forbidden (not_in_set)
    value_scale: Literal["credit_rating"] | None = None   # ordinal scale for min_threshold on strings
    min_items: int = 1                     # required_field on a list: distinct values needed

    # state predicates (ROADMAP 1.1)
    state_key: str | None = None           # key into SessionState.current / .target
    flag_field: str | None = None          # payload field whose truth satisfies a drift obligation
    flag_terms: list[str] | None = None    # constraint-flag substrings that satisfy a flag obligation

    # applicability (ROADMAP 2.2, D1): the predicate applies only while a boolean risk parameter has this value
    condition_param: str | None = None
    condition_value: bool = False

    # max_threshold
    risk_param_key: str | None = None      # key into manifest.risk_parameters -> the bound
    extract: Literal["percent", "duration_years", "amount", "number"] | None = None
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
    tags: list[str] = []


# ---------------------------------------------------------------------------
# The specification both are generated from
# ---------------------------------------------------------------------------

SpecKind = Literal["max", "min", "in_set", "not_in_set", "required_field", "forbid", "require", "drift", "state_max", "flag_above"]


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
    kind: SpecKind
    deontic_type: Literal["F", "O"]
    regulatory_basis: str
    template: str
    source_field: str = "analysis"
    tags: list[ConstraintTag] = []

    # structured evaluation; the forbid / require fields below are the prose fallback
    structured_field: str | None = None
    item_key: str | None = None
    group_key: str | None = None
    aggregate: Literal["sum"] | None = None
    set_param_key: str | None = None
    forbidden_values: list[str] | None = None
    value_scale: Literal["credit_rating"] | None = None
    min_items: int = 1

    # schema derivation (ROADMAP 6.5): how the declared field appears in the response schema
    field_shape: Literal["scalar", "list", "map"] | None = None   # inferred: item_key -> list, else scalar
    field_type: Literal["number", "string", "boolean"] | None = None   # inferred from kind
    field_enum: list[str] | None = None
    field_description: str | None = None

    # state predicates (ROADMAP 1.1) and flag obligations
    state_key: str | None = None
    flag_field: str | None = None
    flag_terms: list[str] | None = None

    # applicability: the constraint applies only while condition_param has condition_value
    condition_param: str | None = None
    condition_value: bool = False

    # max / min
    risk_param_key: str | None = None
    unit: Literal["percent", "years", "amount", "number"] | None = None
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

    @property
    def shape(self) -> str:
        """The declared field's shape in the response schema."""
        if self.field_shape:
            return self.field_shape
        return "list" if self.item_key else "scalar"

    @property
    def value_type(self) -> str:
        """The declared field's JSON type, inferred from the kind when not stated."""
        if self.field_type:
            return self.field_type
        if self.kind in ("max", "min", "drift", "state_max", "flag_above"):
            return "string" if self.value_scale == "credit_rating" else "number"
        return "string"


def _join(items: list[str], last: str = "and") -> str:
    """Join a list as 'a, b and c'."""
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {last} " + items[-1]


def _format_number(value: float) -> str:
    """Format a bound without a trailing .0."""
    return f"{value:g}"


def _format_amount(value: float) -> str:
    """Format a monetary bound with thousands separators."""
    return f"{value:,.0f}"


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
            ctx[f"{key}_amount"] = _format_amount(float(raw))
            ctx[f"{key}_percent"] = _format_number(float(raw) * 100)
        else:
            ctx[key] = str(raw)
    if spec.risk_param_key and spec.unit:
        bound = float(risk_parameters[spec.risk_param_key])
        if spec.unit == "percent":
            ctx["value"] = _format_number(bound * 100)
        elif spec.unit == "amount":
            ctx["value"] = _format_amount(bound)
        else:
            ctx["value"] = _format_number(bound)
    if spec.terms:
        ctx["terms"] = _join(spec.terms, last="or")
    return ctx


def render_text(spec: ConstraintSpec, risk_parameters: dict[str, Any]) -> str:
    """Verbalise the constraint: the text the agent sees and the gate cites."""
    return spec.template.format(**render_context(spec, risk_parameters))


_KIND_MAP: dict[str, str] = {
    "max": "max_threshold", "min": "min_threshold", "in_set": "in_set", "not_in_set": "not_in_set",
    "required_field": "required_field", "forbid": "forbidden_term", "require": "required_term",
    "drift": "state_drift", "state_max": "state_max", "flag_above": "flag_above",
}


def to_predicate(spec: ConstraintSpec) -> Predicate:
    """Derive the predicate the Compliance Agent evaluates; every spec kind maps to one predicate kind."""
    extract = None
    if spec.unit == "percent":
        extract = "percent"
    elif spec.unit == "years":
        extract = "duration_years"
    elif spec.unit == "amount":
        extract = "amount"
    elif spec.unit == "number":
        extract = "number"
    return Predicate(
        kind=_KIND_MAP[spec.kind], variable=spec.variable, source_field=spec.source_field,
        structured_field=spec.structured_field, item_key=spec.item_key, group_key=spec.group_key,
        aggregate=spec.aggregate, set_param_key=spec.set_param_key, forbidden_values=spec.forbidden_values,
        value_scale=spec.value_scale, min_items=spec.min_items,
        state_key=spec.state_key, flag_field=spec.flag_field, flag_terms=spec.flag_terms,
        condition_param=spec.condition_param, condition_value=spec.condition_value,
        risk_param_key=spec.risk_param_key, extract=extract, exceed_label=spec.exceed_label,
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
        deontic_type=spec.deontic_type, regulatory_basis=spec.regulatory_basis, tags=list(spec.tags),
    )


# ---------------------------------------------------------------------------
# The finance specifications, in the order the Compliance Agent evaluates them
# ---------------------------------------------------------------------------

CONSTRAINT_SPECS: list[ConstraintSpec] = [
    # ---- Stocks ----
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_NO_LEVERAGE", agent_id="stocks", variable="leverage_instrument",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.stocks", tags=["leverage"],
        template="No margin trading, short selling, leveraged equity products or derivatives (futures, options, swaps, CFDs)",
        condition_param="leverage_permitted", condition_value=False,
        structured_field="positions", item_key="instrument", forbidden_values=_LEVERAGE_VALUES,
        field_description="spot equity or ETF; never margin, short, leveraged or derivative products",
        terms=_LEVERAGE_TERMS, term_pattern=_LEVERAGE_PATTERN, negation_aware=True,
        found_template="Found forbidden term: '{term}'", clean_template="No leverage terms found",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_MAX_POSITION", agent_id="stocks", variable="single_position_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.stocks", tags=["allocation_cap"],
        template="Maximum {value}% allocation to any single equity position",
        structured_field="positions", item_key="allocation", field_description="allocation fraction, 0.08 means 8%",
        risk_param_key="max_single_position", unit="percent", exceed_label="Positions",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_ESG", agent_id="stocks", variable="esg_disclosure",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.stocks", tags=["disclosure"],
        template="ESG screening required: must flag ESG concerns for any new position",
        structured_field="positions", item_key="esg_assessment", field_description="one sentence on ESG concerns for this company",
        synonyms=ESG_SYNONYMS, present_template="ESG screening present",
        absent_template="No ESG screening language found in analysis",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_LARGECAP", agent_id="stocks", variable="market_cap_usd",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.stocks", tags=["scope"],
        template="Large-cap equities only: market capitalization must exceed ${max_market_cap_threshold_billions} billion; {terms} equities are outside the universe",
        structured_field="positions", item_key="market_cap_usd", risk_param_key="max_market_cap_threshold",
        field_description="market capitalisation in US dollars as a number",
        exceed_label="Positions below the market-cap floor",
        terms=["mid-cap", "small-cap", "micro-cap", "penny stock", "OTC"],
        term_pattern=r"\b(mid[- ]?cap|small[- ]?cap|micro[- ]?cap|penny stock|otc)\b", on_lower=True, ignorecase=False,
        found_template="Found non-large-cap reference: '{term}'", clean_template="No non-large-cap references",
    ),
    # ROADMAP 1.1: concentration after the proposed trade, against the session state.
    ConstraintSpec(
        rule_id="MANIFEST_STOCKS_EXPOSURE", agent_id="stocks", variable="equity_exposure_after_trade",
        kind="state_max", deontic_type="F", regulatory_basis="AgentManifest.stocks", tags=["allocation_cap"],
        template="Total equity exposure after the proposed positions must not exceed {value}% of the portfolio (current equity allocation plus proposed positions)",
        structured_field="positions", item_key="allocation", aggregate="sum", state_key="equities",
        risk_param_key="max_equity_exposure", unit="percent", exceed_label="Equity exposure after trade",
    ),
    # ---- Bonds ----
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_IG_ONLY", agent_id="bonds", variable="credit_rating",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.bonds", tags=["quality_floor"],
        template="Investment grade only: minimum credit rating {min_credit_rating} (S&P) or Baa1 (Moody's); {terms} debt is not permitted",
        structured_field="holdings", item_key="credit_rating", risk_param_key="min_credit_rating",
        value_scale="credit_rating", exceed_label="Holdings below the rating floor",
        field_description="S&P or Moody's notation, e.g. AA+ or Baa1",
        terms=["BB", "B", "CCC", "CC", "C", "junk", "high-yield"],
        term_pattern=r"\b(BB[+-]?|B[+-]?|CCC|CC|C\b|junk|high[- ]yield)\b",
        found_template="Found sub-investment-grade reference: '{term}'", clean_template="No sub-investment-grade references",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_MAX_DURATION", agent_id="bonds", variable="duration_years",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.bonds", tags=["exposure_cap"],
        template="Portfolio duration must remain below {value} years",
        structured_field="portfolio_duration_years", field_description="the resulting portfolio duration in years",
        risk_param_key="max_duration_years", unit="years", exceed_label="Durations",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds", variable="single_maturity_bucket",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.bonds", tags=["structure"],
        template="Laddered maturity structure required: no more than {value}% maturing in any single year",
        structured_field="holdings", item_key="allocation", group_key="maturity_years",
        field_description="allocation fraction, 0.25 means 25%",
        risk_param_key="max_single_maturity_bucket", unit="percent", exceed_label="Buckets",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_NO_EM", agent_id="bonds", variable="emerging_market_debt",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.bonds", tags=["quality_floor"],
        template="No emerging, frontier or developing market sovereign or corporate debt",
        structured_field="holdings", item_key="region", forbidden_values=["emerging", "frontier", "developing"],
        field_enum=["developed", "emerging"],
        terms=["emerging market", "EM debt", "frontier market", "developing country"],
        term_pattern=r"\b(emerging market|em debt|frontier market|developing countr)", on_lower=True, ignorecase=False,
        found_template="Found emerging market reference: '{term}'", clean_template="No emerging market references",
    ),
    # Second obligation carried by the ladder rule: the structure must be present.
    # Shares rule_id MANIFEST_BONDS_LADDER and its text (violated_rules dedupes).
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_LADDER", agent_id="bonds", variable="ladder_structure",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.bonds", tags=["structure"],
        template="Laddered maturity structure required: no more than {value}% maturing in any single year",
        structured_field="holdings", item_key="maturity_years", min_items=2, field_type="number",
        risk_param_key="max_single_maturity_bucket", unit="percent",
        synonyms=LADDER_SYNONYMS, present_template="Maturity ladder structure discussed",
        absent_template="No laddered maturity language found in analysis",
    ),
    # The duration warning: O(duration <= warn_duration_years OR flagged); a warn-severity rule, recorded but not blocking.
    ConstraintSpec(
        rule_id="MANIFEST_BONDS_DURATION_WARN", agent_id="bonds", variable="duration_warning",
        kind="flag_above", deontic_type="O", regulatory_basis="AgentManifest.bonds", tags=["disclosure"],
        template="Must flag any recommendation that would increase overall portfolio duration above {value} years",
        structured_field="portfolio_duration_years", risk_param_key="warn_duration_years", unit="years",
        flag_terms=["duration"], exceed_label="Portfolio duration",
    ),
    # ---- Materials ----
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_APPROVED", agent_id="materials", variable="commodity_type",
        kind="in_set", deontic_type="F", regulatory_basis="AgentManifest.materials", tags=["scope"],
        template="Direct exposure permitted for {approved_commodities} only; {terms} are not permitted",
        structured_field="commodities", item_key="name", set_param_key="approved_commodities",
        terms=["oil", "crude", "natural gas", "copper", "platinum", "palladium", "wheat", "corn", "soybeans", "crypto assets"],
        term_pattern=r"\b(oil|crude|natural\s*gas|copper|platinum|palladium|wheat|corn|soybean|crypto|bitcoin|ethereum)\b",
        negation_aware=True,
        found_template="Found non-approved commodity: '{term}'", clean_template="Only approved commodities referenced",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_MAX_ALLOC", agent_id="materials", variable="total_materials_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.materials", tags=["allocation_cap"],
        template="Maximum {value}% of total portfolio in raw materials",
        structured_field="commodities", item_key="allocation", aggregate="sum",
        field_description="allocation fraction, 0.10 means 10%",
        risk_param_key="max_total_allocation", unit="percent", exceed_label="Allocations",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_NO_LEVERAGE", agent_id="materials", variable="leverage_instrument",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.materials", tags=["leverage"],
        template="No leveraged commodity ETFs, futures contracts or other derivatives (options, swaps, CFDs), and no margin or short positions",
        condition_param="leverage_permitted", condition_value=False,
        structured_field="commodities", item_key="instrument", forbidden_values=_LEVERAGE_VALUES,
        field_description="physical or unleveraged ETF; never leveraged ETFs or futures",
        terms=_LEVERAGE_TERMS, term_pattern=_LEVERAGE_PATTERN, negation_aware=True,
        found_template="Found forbidden term: '{term}'", clean_template="No leverage terms found",
    ),
    # ROADMAP 1.1: the rebalancing trigger as a checkable obligation,
    # O(|proposed - target| <= rebalance_drift_threshold  OR  flagged).
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_REBALANCE", agent_id="materials", variable="allocation_drift",
        kind="drift", deontic_type="O", regulatory_basis="AgentManifest.materials", tags=["monitoring"],
        template="Rebalancing trigger: flag to orchestrator (rebalance_flag) if the proposed raw-materials allocation drifts more than ±{value}% from the target allocation",
        structured_field="commodities", item_key="allocation", aggregate="sum", state_key="materials",
        flag_field="rebalance_flag", risk_param_key="rebalance_drift_threshold", unit="percent",
        exceed_label="Allocation drift",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_MATERIALS_INFLATION", agent_id="materials", variable="inflation_rationale",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.materials", tags=["disclosure"],
        template="Must provide inflation correlation rationale for every recommendation",
        structured_field="inflation_rationale",
        field_description="one or two sentences on how the recommended commodities correlate with inflation",
        synonyms=INFLATION_SYNONYMS, present_template="Inflation rationale present",
        absent_template="No inflation rationale found in analysis",
    ),
    # ---- Central (synthesis checkpoint) ----
    ConstraintSpec(
        rule_id="MANIFEST_CENTRAL_MAX_ASSET_CLASS", agent_id="central", variable="single_asset_class_allocation",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.central", tags=["allocation_cap"],
        template="Maximum {value}% allocation to any single asset class",
        structured_field="allocation_by_asset_class", field_shape="map",
        field_description="fraction of the portfolio per asset class, e.g. equities, bonds, materials",
        risk_param_key="max_single_asset_class", unit="percent", exceed_label="Asset class allocations",
        source_field="final_recommendation",
    ),
]


def specs_for(agent_id: str, specs: list[ConstraintSpec] | None = None) -> list[ConstraintSpec]:
    """Return the specifications of an agent in evaluation order (finance specs unless given)."""
    return [s for s in (specs if specs is not None else CONSTRAINT_SPECS) if s.agent_id == agent_id]


def generated_text(rule_id: str, risk_parameters: dict[str, Any], specs: list[ConstraintSpec] | None = None) -> str:
    """Return the manifest text of a rule, rendered from its specification and the risk parameters."""
    spec = next(s for s in (specs if specs is not None else CONSTRAINT_SPECS) if s.rule_id == rule_id)
    return render_text(spec, risk_parameters)
