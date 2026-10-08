"""Response schemas for every LLM call: passed to the serving layer so that typed fields are produced by constrained decoding."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Recommendation = Literal["buy", "hold", "sell", "not_applicable"]
Confidence = Literal["high", "medium", "low"]


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
    """Commodities specialist: commodities and the inflation rationale."""

    commodities: list[Commodity]
    inflation_rationale: str


class RoutingResponse(BaseModel):
    """Orchestrator routing decision."""

    routing_rationale: str
    agents_to_call: list[Literal["stocks", "bonds", "materials"]]
    query_for_stocks: str | None = None
    query_for_bonds: str | None = None
    query_for_materials: str | None = None


class SynthesisResponse(BaseModel):
    """Orchestrator synthesis: recommendation, allocation per asset class, accountability note."""

    final_recommendation: str
    allocation_by_asset_class: dict[str, float]
    accountability_note: str


def response_format(model: type[BaseModel]) -> dict[str, Any]:
    """Build the OpenAI-style response_format carrying the model's JSON schema."""
    return {"type": "json_schema", "json_schema": {"name": model.__name__, "schema": model.model_json_schema()}}


STOCKS_FORMAT = response_format(StocksResponse)
BONDS_FORMAT = response_format(BondsResponse)
MATERIALS_FORMAT = response_format(MaterialsResponse)
ROUTING_FORMAT = response_format(RoutingResponse)
SYNTHESIS_FORMAT = response_format(SynthesisResponse)
