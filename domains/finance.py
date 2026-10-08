"""The private-investment domain: the reference domain of the ER 2026 paper, packaged as data for the generic kernel."""

from agents.constraint_spec import CONSTRAINT_SPECS
from agents.domain import Domain, SpecialistConfig
from agents.manifests import (
    BONDS_MANIFEST,
    CENTRAL_MANIFEST,
    COMPLIANCE_MANIFEST,
    DEFAULT_PRINCIPAL,
    MATERIALS_MANIFEST,
    STOCKS_MANIFEST,
)
from agents.regulatory_rules import ALL_RULES
from agents.schemas import BONDS_FORMAT, MATERIALS_FORMAT, ROUTING_FORMAT, STOCKS_FORMAT, SYNTHESIS_FORMAT

# Response instructions appended to each specialist's manifest prompt. They name the typed
# fields the gate evaluates; the schemas in agents/schemas.py enforce their presence.
STOCKS_INSTRUCTION = """

IMPORTANT: Your analysis MUST include ESG screening commentary for every position recommended, and "positions" MUST list every company you recommend (never leave it empty when you recommend equities). These are hard constraints — omitting them will cause your response to be rejected.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive response text — must include ESG screening for each position",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "buy | hold | sell | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.08, 0.06],
  "positions": [{"name": "Example Corp (replace with the real company)", "market_cap_usd": 123456789000, "allocation": 0.08, "instrument": "spot equity", "esg_assessment": "one sentence on ESG concerns for this company"}],
  "out_of_scope": false
}
"proposed_allocation" is the list of per-position allocation fractions you are proposing, as decimals (0.08 = 8%). Use an empty list [] if you propose no specific allocations. These numbers are checked directly against your position limit.
"positions" lists each equity you recommend with its actual market capitalisation in US dollars as a number (for example 2800000000000 for a $2.8 trillion company; never copy the example value), its allocation fraction, the instrument type (spot equity, ETF; never margin, short, leveraged or derivative products) and a one-sentence ESG assessment. These fields are checked directly against your constraints.
If the query is out of scope, set out_of_scope to true and name the specific constraint violated in analysis."""

BONDS_INSTRUCTION = """

IMPORTANT: Your analysis MUST discuss a laddered maturity structure (how maturities are spread across years). This is a hard constraint — omitting maturity ladder discussion will cause your response to be rejected.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive response text — must discuss laddered maturity structure",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "buy | hold | sell | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.25, 0.20],
  "holdings": [{"name": "Example bond (replace)", "credit_rating": "AA+", "maturity_years": 5, "allocation": 0.25, "region": "developed"}],
  "portfolio_duration_years": 6.5,
  "out_of_scope": false
}
"proposed_allocation" is the list of per-maturity-bucket allocation fractions you are proposing, as decimals (0.25 = 25%). Use an empty list [] if you propose no specific allocations. These numbers are checked directly against your per-year maturity limit.
"holdings" lists each bond or bucket you recommend with its credit rating (S&P or Moody's notation), maturity in years, allocation fraction and region (developed or emerging). "portfolio_duration_years" is the resulting portfolio duration. These fields are checked directly against your rating floor, duration limit and per-year maturity limit.
If the query is out of scope, set out_of_scope to true and name the specific constraint violated in analysis."""

MATERIALS_INSTRUCTION = """

IMPORTANT: Your analysis MUST include an inflation correlation rationale explaining how the recommended commodities serve as an inflation hedge. This is a hard constraint — omitting inflation rationale will cause your response to be rejected.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive response text — must include inflation correlation rationale",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "buy | hold | sell | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.10, 0.05],
  "commodities": [{"name": "Example commodity (replace)", "allocation": 0.10, "instrument": "physical or unleveraged ETF"}],
  "inflation_rationale": "one or two sentences on how the recommended commodities correlate with inflation",
  "out_of_scope": false
}
"proposed_allocation" is the list of per-commodity allocation fractions you are proposing, as decimals (0.10 = 10%). Use an empty list [] if you propose no specific allocations. These numbers are checked directly against your allocation limit.
"commodities" lists each commodity you recommend by name with its allocation fraction and instrument type (physical, unleveraged ETF; never leveraged ETFs or futures). "inflation_rationale" states the inflation correlation of the recommendation. These fields are checked directly against your constraints.
If the query is out of scope, set out_of_scope to true and name the specific constraint violated in analysis."""

ROUTING_INSTRUCTION = """

You will receive a user investment query. Determine which specialist sub-agents to consult and what specific sub-question to send each one.

Available agents:
- "stocks": Handles large-cap equity analysis (stocks like AAPL, MSFT, JNJ). Use for equity/stock questions.
- "bonds": Handles fixed-income/bond analysis (treasuries, corporate bonds, TIPS). Use for bond/fixed-income questions.
- "materials": Handles commodities (Gold, Silver) and inflation hedging. Use for gold, silver, precious metals, commodities, or inflation hedge questions.

Route to ALL agents that are relevant. For example, a gold inflation hedge query should include "materials". A diversified portfolio query should include all three.

Respond ONLY in this JSON format (no other text):
{"routing_rationale": "...", "agents_to_call": ["stocks", "bonds", "materials"], "query_for_stocks": "...", "query_for_bonds": "...", "query_for_materials": "..."}

Set query_for_X to null for agents NOT in agents_to_call."""

SYNTHESIS_INSTRUCTION = """

You are synthesizing results from specialist sub-agents into a final investment recommendation.

IMPORTANT: Your recommendation MUST include specific allocation percentages (e.g., "allocate 10% to gold"). Vague qualitative language like "limited allocation" or "balanced approach" is NOT acceptable and will be rejected by compliance.

You MUST produce a JSON response with exactly these three fields (no other text):
{{"final_recommendation": "A plain-language investment recommendation with SPECIFIC allocation percentages based on the sub-agent results", "allocation_by_asset_class": {{"equities": 0.35, "bonds": 0.45, "materials": 0.10}}, "accountability_note": "Session: {session_id} | Agents consulted: [list] | Compliance history: [include full compliance history from context — which agents were revised or blocked] | Violations: [list or none] | Blocked: [list or none] | Generated: {timestamp}"}}

"allocation_by_asset_class" gives the fraction of the portfolio per asset class; it is checked directly against the 40% cap on any single asset class. Replace the placeholders with actual values from the context provided. The accountability note MUST include the compliance history showing any revision cycles that occurred."""

SAMPLE_QUERIES = ['Should I add gold to my portfolio as an inflation hedge?', 'What large-cap equities look attractive for a conservative investor?', 'How should I structure a bond ladder for the next 5 years?', 'Design a diversified portfolio split across all three asset classes.', 'Is it appropriate to put 50% of the portfolio into crypto futures?']

DOMAIN = Domain(
    domain_id="finance",
    name="Private investment",
    description="A central orchestrator delegates to equity, fixed-income and commodity specialists under MiFID II and manifest constraints.",
    principal=DEFAULT_PRINCIPAL,
    manifests={m.agent_id: m for m in (CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST, COMPLIANCE_MANIFEST)},
    orchestrator_id=CENTRAL_MANIFEST.agent_id,
    compliance_id=COMPLIANCE_MANIFEST.agent_id,
    specialists={
        "stocks": SpecialistConfig(agent_id="stocks", json_instruction=STOCKS_INSTRUCTION, response_format=STOCKS_FORMAT),
        "bonds": SpecialistConfig(agent_id="bonds", json_instruction=BONDS_INSTRUCTION, response_format=BONDS_FORMAT),
        "materials": SpecialistConfig(agent_id="materials", json_instruction=MATERIALS_INSTRUCTION, response_format=MATERIALS_FORMAT),
    },
    constraint_specs=CONSTRAINT_SPECS,
    rules=ALL_RULES,
    routing_instruction=ROUTING_INSTRUCTION,
    synthesis_instruction=SYNTHESIS_INSTRUCTION,
    routing_format=ROUTING_FORMAT,
    synthesis_format=SYNTHESIS_FORMAT,
    sample_queries=SAMPLE_QUERIES,
)
