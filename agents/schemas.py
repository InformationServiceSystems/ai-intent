"""Response schemas for every LLM call, derived from the constraint specifications (ROADMAP 6.5) and passed to the serving layer for constrained decoding.

A specialist's response model is the kernel's base fields plus one field per
`structured_field` its specifications declare: a list of items (each with a `name` and the
declared `item_key`s, typed by the specification's kind), a scalar, or a map. The hand-written
finance models at the end of the module are kept as the oracle the derivation is tested against.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

from agents.constraint_spec import ConstraintSpec

Recommendation = Literal["buy", "hold", "sell", "not_applicable"]
Confidence = Literal["high", "medium", "low"]

_JSON_TYPES: dict[str, type] = {"number": float, "string": str, "boolean": bool}


def _field_type(spec: ConstraintSpec) -> Any:
    """The Python type of a declared field: an enum when the spec states one, else the inferred JSON type."""
    if spec.field_enum:
        return Literal[tuple(spec.field_enum)]  # type: ignore[return-value]
    return _JSON_TYPES[spec.value_type]


def _item_model(field_name: str, specs: list[ConstraintSpec]) -> type[BaseModel]:
    """Build the item model of a list field from every spec that declares an item_key on it."""
    fields: dict[str, Any] = {"name": (str, ...)}
    for spec in specs:
        if not spec.item_key or spec.item_key in fields:
            continue
        fields[spec.item_key] = (_field_type(spec), Field(..., description=spec.field_description) if spec.field_description else ...)
    name = "".join(part.capitalize() for part in field_name.split("_")) + "Item"
    return create_model(name, **fields)  # type: ignore[call-overload]


def derive_response_model(
    agent_id: str,
    specs: list[ConstraintSpec],
    recommendation_values: list[str] | None = None,
    model_name: str | None = None,
    exceptions: list | None = None,
) -> type[BaseModel]:
    """Derive a specialist's response model from its specifications and the exceptions that defeat them (ROADMAP 1.3)."""
    values = tuple(recommendation_values or ["buy", "hold", "sell", "not_applicable"])
    fields: dict[str, Any] = {
        "analysis": (str, ...),
        "constraint_flags": (list[str], ...),
        "recommendation": (Literal[values], ...),  # type: ignore[valid-type]
        "confidence": (Confidence, ...),
        "proposed_allocation": (list[float], ...),
        "out_of_scope": (bool, ...),
    }
    own = [s for s in specs if s.agent_id == agent_id and s.structured_field]
    by_field: dict[str, list[ConstraintSpec]] = {}
    for s in own:
        by_field.setdefault(s.structured_field, []).append(s)  # type: ignore[arg-type]
    for field_name, field_specs in by_field.items():
        shapes = {s.shape for s in field_specs}
        if "list" in shapes:
            fields[field_name] = (list[_item_model(field_name, field_specs)], ...)  # type: ignore[valid-type]
        elif "map" in shapes:
            fields[field_name] = (dict[str, float], ...)
        else:
            spec = field_specs[0]
            fields[field_name] = (_field_type(spec), Field(..., description=spec.field_description) if spec.field_description else ...)
    own_rules = {s.rule_id for s in own}
    for exc in exceptions or []:
        if exc.defeats not in own_rules:
            continue
        if exc.when_field and exc.when_field not in fields:
            fields[exc.when_field] = (bool, Field(..., description=f"true only if documented: {exc.description}"))
        if exc.requires_field and exc.requires_field not in fields:
            fields[exc.requires_field] = (str, Field(..., description=f"the documentation reference for {exc.exception_id}; empty if none"))
    for s in own:
        if s.flag_field and s.flag_field not in fields:
            fields[s.flag_field] = (bool, Field(..., description=f"true if the obligation '{s.variable}' applies and you are flagging it"))
    return create_model(model_name or f"{agent_id.capitalize()}Response", **fields)  # type: ignore[call-overload]


def derive_routing_model(specialist_ids: list[str], model_name: str = "RoutingResponse") -> type[BaseModel]:
    """Derive the orchestrator's routing model: the agents to call and one sub-question per specialist."""
    ids = tuple(specialist_ids)
    fields: dict[str, Any] = {
        "routing_rationale": (str, ...),
        "agents_to_call": (list[Literal[ids]], ...),  # type: ignore[valid-type]
    }
    for agent_id in specialist_ids:
        fields[f"query_for_{agent_id}"] = (str | None, None)
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def derive_synthesis_model(orchestrator_id: str, specs: list[ConstraintSpec], model_name: str = "SynthesisResponse") -> type[BaseModel]:
    """Derive the synthesis model: the recommendation plus every structured field the orchestrator's specs declare."""
    fields: dict[str, Any] = {"final_recommendation": (str, ...)}
    for s in specs:
        if s.agent_id != orchestrator_id or not s.structured_field or s.structured_field in fields:
            continue
        if s.shape == "map":
            fields[s.structured_field] = (dict[str, float], Field(..., description=s.field_description) if s.field_description else ...)
        elif s.shape == "list":
            fields[s.structured_field] = (list[_item_model(s.structured_field, [x for x in specs if x.structured_field == s.structured_field])], ...)  # type: ignore[valid-type]
        else:
            fields[s.structured_field] = (_field_type(s), ...)
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def response_format(model: type[BaseModel]) -> dict[str, Any]:
    """Build the OpenAI-style response_format carrying the model's JSON schema."""
    return {"type": "json_schema", "json_schema": {"name": model.__name__, "schema": model.model_json_schema()}}


# ---------------------------------------------------------------------------
# Hand-written finance models: the oracle for tests/test_schemas.py
# ---------------------------------------------------------------------------

class Position(BaseModel):
    """One recommended equity position."""

    name: str
    market_cap_usd: float = Field(description="market capitalisation in US dollars as a number")
    allocation: float = Field(description="allocation fraction, 0.08 means 8%")
    instrument: str = Field(description="spot equity or ETF; never margin, short, leveraged or derivative products")
    esg_assessment: str = Field(description="one sentence on ESG concerns for this company")


class Holding(BaseModel):
    """One recommended bond or maturity bucket."""

    name: str
    credit_rating: str = Field(description="S&P or Moody's notation, e.g. AA+ or Baa1")
    maturity_years: float
    allocation: float = Field(description="allocation fraction, 0.25 means 25%")
    region: Literal["developed", "emerging"]


class Commodity(BaseModel):
    """One recommended commodity exposure."""

    name: str
    allocation: float = Field(description="allocation fraction, 0.10 means 10%")
    instrument: str = Field(description="physical or unleveraged ETF; never leveraged ETFs or futures")


class _AgentResponse(BaseModel):
    """Fields every specialist returns."""

    analysis: str
    constraint_flags: list[str]
    recommendation: Recommendation
    confidence: Confidence
    proposed_allocation: list[float]
    out_of_scope: bool


class StocksResponse(_AgentResponse):
    """Equity specialist: positions carry the typed fields the gate evaluates."""

    positions: list[Position]


class BondsResponse(_AgentResponse):
    """Fixed-income specialist: holdings and the resulting portfolio duration."""

    holdings: list[Holding]
    portfolio_duration_years: float


class MaterialsResponse(_AgentResponse):
    """Commodities specialist: commodities, the inflation rationale and the rebalancing flag."""

    commodities: list[Commodity]
    inflation_rationale: str
    rebalance_flag: bool


class RoutingResponse(BaseModel):
    """Orchestrator routing decision."""

    routing_rationale: str
    agents_to_call: list[Literal["stocks", "bonds", "materials"]]
    query_for_stocks: str | None = None
    query_for_bonds: str | None = None
    query_for_materials: str | None = None


class SynthesisResponse(BaseModel):
    """Orchestrator synthesis: recommendation and allocation per asset class (the accountability note is a projection of the trace)."""

    final_recommendation: str
    allocation_by_asset_class: dict[str, float]


STOCKS_FORMAT = response_format(StocksResponse)
BONDS_FORMAT = response_format(BondsResponse)
MATERIALS_FORMAT = response_format(MaterialsResponse)
ROUTING_FORMAT = response_format(RoutingResponse)
SYNTHESIS_FORMAT = response_format(SynthesisResponse)
