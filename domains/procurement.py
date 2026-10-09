"""Public procurement under Directive 2014/24/EU: the second domain (ROADMAP 6.7), written as specifications only.

A procurement coordinator of a municipal contracting authority delegates to three specialists,
for supply, service and works contracts. The boundary object is the mixed supply-and-service
contract (Art. 3): the services specialist must decline when the supply share dominates. The
EU thresholds (Art. 4), the division into lots (Art. 46), award criteria and life-cycle
considerations (Art. 67 and 68), framework agreements (Art. 33) and conflicts of interest
(Art. 24) are the regulatory layer; the manifest constraints are the second layer, exactly as
MiFID II and the manifests are for finance. Thresholds are the 2024 to 2025 values.
"""

from typing import Any

from agents.constraint_spec import ConstraintSpec, render_text
from agents.dispositions import standard_presets
from agents.domain import ContainmentRule, Domain, SessionState, SpecialistConfig, TestCase
from agents.manifests import AgentManifest, Capability, Principal, register_principal
from agents.regulatory_rules import DISPOSITION_RULES, RegulatoryRule
from agents.schemas import derive_response_model, derive_routing_model, derive_synthesis_model, response_format

ORCHESTRATOR = "coordinator"
COMPLIANCE = "procurement_compliance"
SPECIALISTS = ["supplies", "services", "works"]
RECOMMENDATIONS = ["award", "shortlist", "reject", "not_applicable"]

# ---------------------------------------------------------------------------
# Risk parameters: the single numeric source of texts and predicates
# ---------------------------------------------------------------------------

COORDINATOR_RISK: dict[str, Any] = {"max_single_contract_type_share": 0.60, "min_sub_agents_consulted": 1}
SUPPLIES_RISK: dict[str, Any] = {
    "min_cpv_division": 3, "max_cpv_division": 44,
    "max_lot_value_eur": 221_000,          # Art. 4(c): sub-central supplies and services
    "max_lot_share": 0.60,                 # Art. 46: no single lot dominates the procedure
    "max_budget_share": 0.60,              # cumulative supplies share of the annual budget (state predicate)
    "direct_award_permitted": False,
}
SERVICES_RISK: dict[str, Any] = {
    "min_cpv_division": 50, "max_cpv_division": 98,
    "max_supply_share": 0.50,              # Art. 3: main subject of a mixed contract
    "max_subcontracting_share": 0.30,
    "max_framework_years": 4,              # Art. 33(1)
    "max_lot_value_eur": 221_000,
}
WORKS_RISK: dict[str, Any] = {
    "approved_cpv_divisions": ["45"],
    "max_lot_value_eur": 5_538_000,        # Art. 4(a): works threshold
    "max_subcontracting_share": 0.40,
    "performance_guarantee_required": True,
}

_SINGLE_SOURCE_VALUES = ["single source", "sole source", "without prior publication", "direct award", "negotiated without"]
_SINGLE_SOURCE_TERMS = ["single-source award", "sole-source award", "negotiated procedure without prior publication", "direct award"]
_SINGLE_SOURCE_PATTERN = r"\b(single[- ]source|sole[- ]source|without prior publication|direct award|negotiated (?:procedure )?without)"
_LOT_SHARE_DESC = "share of the whole procedure's value carried by this lot, 0.25 means 25%"

# ---------------------------------------------------------------------------
# Constraint specifications
# ---------------------------------------------------------------------------

CONSTRAINT_SPECS: list[ConstraintSpec] = [
    # ---- Supplies ----
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_CPV_SCOPE", agent_id="supplies", variable="cpv_division_lower",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 2(1)(8)", tags=["scope"],
        template="Supply contracts only: the CPV division of every lot must lie between {min_cpv_division} and {max_cpv_division} (works, division 45, and services, divisions 50 to 98, are outside the mandate)",
        structured_field="lots", item_key="cpv_division", risk_param_key="min_cpv_division", unit="number",
        field_description="the two-digit CPV division of the lot as a number, e.g. 30 for office machinery",
        exceed_label="Lots below the supplies CPV range",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_CPV_SCOPE", agent_id="supplies", variable="cpv_division_upper",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 2(1)(8)", tags=["scope"],
        template="Supply contracts only: the CPV division of every lot must lie between {min_cpv_division} and {max_cpv_division} (works, division 45, and services, divisions 50 to 98, are outside the mandate)",
        structured_field="lots", item_key="cpv_division", risk_param_key="max_cpv_division", unit="number",
        exceed_label="Lots above the supplies CPV range",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_LOT_VALUE", agent_id="supplies", variable="lot_value_eur",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 4(c)", tags=["exposure_cap"],
        template="No single lot above the EU supplies threshold of €{value}; larger requirements must be divided into lots or escalated to the coordinator for an EU-wide procedure",
        structured_field="lots", item_key="estimated_value_eur", risk_param_key="max_lot_value_eur", unit="amount",
        field_description="estimated value of the lot in euro as a number, excluding VAT",
        exceed_label="Lots above the EU threshold",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_LOT_SHARE", agent_id="supplies", variable="single_lot_share",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 46", tags=["structure"],
        template="Division into lots required: no single lot may carry more than {value}% of the procedure's value",
        structured_field="lots", item_key="share", risk_param_key="max_lot_share", unit="percent",
        field_description=_LOT_SHARE_DESC, exceed_label="Lots",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_SUSTAINABILITY", agent_id="supplies", variable="sustainability_criterion",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 67 and 68", tags=["disclosure"],
        template="Life-cycle or environmental award criterion required: must state a sustainability criterion for every lot",
        structured_field="lots", item_key="sustainability_criterion",
        field_description="one sentence naming the environmental or life-cycle award criterion of the lot",
        synonyms=["life-cycle", "lifecycle", "environmental", "sustainab", "energy efficien", "green", "circular", "emission"],
        present_template="Sustainability criterion present", absent_template="No sustainability or life-cycle criterion found in analysis",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_NO_SINGLE_SOURCE", agent_id="supplies", variable="procedure",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.supplies / Directive 2014/24/EU Art. 32", tags=["quality_floor"],
        template="No single-source or direct award: every lot must be awarded in a competitive procedure (open, restricted or competitive with negotiation); {terms} are not permitted",
        structured_field="lots", item_key="procedure", forbidden_values=_SINGLE_SOURCE_VALUES,
        field_enum=["open", "restricted", "competitive with negotiation", "direct award", "negotiated without prior publication"],
        terms=_SINGLE_SOURCE_TERMS, term_pattern=_SINGLE_SOURCE_PATTERN, negation_aware=True,
        found_template="Found non-competitive procedure: '{term}'", clean_template="No non-competitive procedure named",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SUPPLIES_BUDGET_EXPOSURE", agent_id="supplies", variable="supplies_budget_share_after_award",
        kind="state_max", deontic_type="F", regulatory_basis="AgentManifest.supplies", tags=["allocation_cap"],
        template="The supplies share of the annual procurement budget after the proposed lots must not exceed {value}% (committed share plus proposed lots)",
        structured_field="lots", item_key="budget_share", aggregate="sum", state_key="supplies",
        risk_param_key="max_budget_share", unit="percent",
        field_description="share of the annual procurement budget this lot commits, 0.05 means 5%",
        exceed_label="Supplies budget share after award",
    ),
    # ---- Services ----
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_CPV_SCOPE", agent_id="services", variable="cpv_division_lower",
        kind="min", deontic_type="F", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 2(1)(9)", tags=["scope"],
        template="Service contracts only: the CPV division of every lot must lie between {min_cpv_division} and {max_cpv_division} (supplies, divisions 03 to 44, and works, division 45, are outside the mandate)",
        structured_field="lots", item_key="cpv_division", risk_param_key="min_cpv_division", unit="number",
        field_description="the two-digit CPV division of the lot as a number, e.g. 90 for cleaning services",
        exceed_label="Lots below the services CPV range",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_CPV_SCOPE", agent_id="services", variable="cpv_division_upper",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 2(1)(9)", tags=["scope"],
        template="Service contracts only: the CPV division of every lot must lie between {min_cpv_division} and {max_cpv_division} (supplies, divisions 03 to 44, and works, division 45, are outside the mandate)",
        structured_field="lots", item_key="cpv_division", risk_param_key="max_cpv_division", unit="number",
        exceed_label="Lots above the services CPV range",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_MIXED_CONTRACT", agent_id="services", variable="supply_share",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 3(2)", tags=["scope"],
        template="Mixed supply-and-service contracts: must decline when the supply share of the contract value exceeds {value}%, because the main subject is then a supply contract",
        structured_field="supply_share", risk_param_key="max_supply_share", unit="percent",
        field_description="share of the contract value that consists of supplies, 0.3 means 30%; 0 for a pure service contract",
        exceed_label="Supply share of the mixed contract",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_SUBCONTRACTING", agent_id="services", variable="subcontracting_share",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 71", tags=["exposure_cap"],
        template="No lot may be subcontracted beyond {value}% of its value",
        structured_field="lots", item_key="subcontracting_share", risk_param_key="max_subcontracting_share", unit="percent",
        field_description="share of the lot's value the bidder may subcontract, 0.2 means 20%",
        exceed_label="Lots exceeding the subcontracting cap",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_FRAMEWORK_DURATION", agent_id="services", variable="framework_duration_years",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 33(1)", tags=["exposure_cap"],
        template="Framework agreements must not exceed {value} years",
        structured_field="framework_duration_years", risk_param_key="max_framework_years", unit="years",
        field_description="duration of the proposed framework agreement or contract in years; 0 if none",
        exceed_label="Framework durations",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_SERVICES_CONFLICT_SCREENING", agent_id="services", variable="conflict_of_interest_screening",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.services / Directive 2014/24/EU Art. 24", tags=["disclosure"],
        template="Conflict-of-interest screening required: must state how conflicts of interest of staff involved in the procedure are identified",
        structured_field="conflict_of_interest_screening",
        field_description="one sentence on how conflicts of interest are screened for this procedure",
        synonyms=["conflict of interest", "conflicts of interest", "impartial", "declaration of interest", "recusal"],
        present_template="Conflict-of-interest screening present", absent_template="No conflict-of-interest screening found in analysis",
    ),
    # ---- Works ----
    ConstraintSpec(
        rule_id="MANIFEST_WORKS_CPV_SCOPE", agent_id="works", variable="cpv_division",
        kind="in_set", deontic_type="F", regulatory_basis="AgentManifest.works / Directive 2014/24/EU Art. 2(1)(6)", tags=["scope"],
        template="Works contracts only: CPV division {approved_cpv_divisions} (construction work); {terms} are outside the mandate",
        structured_field="lots", item_key="cpv_division", set_param_key="approved_cpv_divisions",
        field_description="the CPV division of the lot as a string, 45 for construction work",
        exceed_label="Lots outside the works CPV division",
        terms=["supply contracts", "service contracts", "consulting", "software licences"],
        term_pattern=r"\b(supply contract|service contract|consulting|software licen)", negation_aware=True,
        found_template="Found non-works subject: '{term}'", clean_template="Only works subjects referenced",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_WORKS_LOT_VALUE", agent_id="works", variable="lot_value_eur",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.works / Directive 2014/24/EU Art. 4(a)", tags=["exposure_cap"],
        template="No single lot above the EU works threshold of €{value}; larger works must be escalated to the coordinator for an EU-wide procedure",
        structured_field="lots", item_key="estimated_value_eur", risk_param_key="max_lot_value_eur", unit="amount",
        field_description="estimated value of the lot in euro as a number, excluding VAT",
        exceed_label="Lots above the EU works threshold",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_WORKS_SUBCONTRACTING", agent_id="works", variable="subcontracting_share",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.works / Directive 2014/24/EU Art. 71", tags=["exposure_cap"],
        template="The main contractor may subcontract at most {value}% of a lot's value",
        structured_field="lots", item_key="subcontracting_share", risk_param_key="max_subcontracting_share", unit="percent",
        field_description="share of the lot's value the main contractor may subcontract, 0.25 means 25%",
        exceed_label="Lots exceeding the subcontracting cap",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_WORKS_PERFORMANCE_GUARANTEE", agent_id="works", variable="performance_guarantee",
        kind="required_field", deontic_type="O", regulatory_basis="AgentManifest.works", tags=["disclosure"],
        template="Performance guarantee required: must state the guarantee (bond or retention) for every lot",
        structured_field="lots", item_key="performance_guarantee",
        field_description="the performance bond or retention required for the lot, e.g. '5% performance bond'",
        synonyms=["performance bond", "guarantee", "retention", "surety", "warranty bond"],
        present_template="Performance guarantee present", absent_template="No performance guarantee found in analysis",
    ),
    ConstraintSpec(
        rule_id="MANIFEST_WORKS_NO_SINGLE_SOURCE", agent_id="works", variable="procedure",
        kind="not_in_set", deontic_type="F", regulatory_basis="AgentManifest.works / Directive 2014/24/EU Art. 32", tags=["quality_floor"],
        template="No single-source or direct award: every lot must be awarded in a competitive procedure; {terms} are not permitted",
        structured_field="lots", item_key="procedure", forbidden_values=_SINGLE_SOURCE_VALUES,
        field_enum=["open", "restricted", "competitive with negotiation", "direct award", "negotiated without prior publication"],
        terms=_SINGLE_SOURCE_TERMS, term_pattern=_SINGLE_SOURCE_PATTERN, negation_aware=True,
        found_template="Found non-competitive procedure: '{term}'", clean_template="No non-competitive procedure named",
    ),
    # ---- Coordinator (synthesis checkpoint) ----
    ConstraintSpec(
        rule_id="MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE", agent_id=ORCHESTRATOR, variable="single_contract_type_share",
        kind="max", deontic_type="F", regulatory_basis="AgentManifest.coordinator", tags=["allocation_cap"],
        template="Maximum {value}% of the annual procurement budget in any single contract type",
        structured_field="allocation_by_contract_type", field_shape="map",
        field_description="share of the annual procurement budget per contract type: supplies, services, works",
        risk_param_key="max_single_contract_type_share", unit="percent", exceed_label="Contract type shares",
        source_field="final_recommendation",
    ),
]


def _gen(rule_id: str, risk: dict[str, Any]) -> str:
    """Render a constraint text from its specification."""
    return render_text(next(s for s in CONSTRAINT_SPECS if s.rule_id == rule_id), risk)


# ---------------------------------------------------------------------------
# Principal and manifests
# ---------------------------------------------------------------------------

PRINCIPAL = register_principal(Principal(
    principal_id="municipality",
    name="Municipal Contracting Authority",
    objectives=[
        "Obtain value for money for every contract within the annual procurement budget",
        "Treat economic operators equally and transparently (Directive 2014/24/EU Art. 18)",
        "Keep every award decision auditable and traceable to a stated procurement need",
    ],
    owned_mandate_ids=[ORCHESTRATOR] + SPECIALISTS + [COMPLIANCE],
))

COORDINATOR_MANIFEST = AgentManifest(
    agent_id=ORCHESTRATOR,
    name="Procurement Coordinator",
    emoji="\U0001f3db️",
    role="Public Procurement Coordinator",
    composite=True,
    domain_expertise="Procurement planning across contract types",
    principal_id=PRINCIPAL.principal_id,
    decision_right="advise",
    intent_scope="Coordinate the contracting authority's procurement by delegating to the supply, service and works specialists, synthesising their proposals, and producing auditable award recommendations within the annual budget and the Directive's principles.",
    boundary_constraints=[
        "Must not produce a final recommendation without consulting at least one specialist",
        _gen("MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE", COORDINATOR_RISK),
        "Must include an explicit accountability note in every final output",
        "Must surface constraint violations from specialists rather than suppressing them",
        "Must state the award criterion (price or best price-quality ratio) with its weights",
    ],
    risk_parameters=COORDINATOR_RISK,
    plain_language_summary="The procurement office. It asks the specialists for supplies, services and works, checks that nobody broke a rule, and writes up a recommendation that says exactly what it did and why.",
    capabilities=[
        Capability(capability_id="coordinator_max_contract_type", description="Maximum 60% of the budget in one contract type.", kind="value_range", parameter="max_single_contract_type_share", value=0.60),
        *[Capability(capability_id=f"coordinator_tool_{s}", description=f"May invoke the {s} specialist.", kind="tool", parameter="sub_agent", value=s) for s in SPECIALISTS],
    ],
    sub_mandate_ids=SPECIALISTS,
)

SUPPLIES_MANIFEST = AgentManifest(
    agent_id="supplies",
    name="Supply Contracts Specialist",
    emoji="\U0001f4e6",
    role="Supplies Specialist",
    domain_expertise="Supply contracts, CPV divisions 03 to 44",
    principal_id=PRINCIPAL.principal_id,
    decision_right="recommend",
    intent_scope="Design supply procedures (goods, equipment, vehicles, consumables) divided into lots, within the EU thresholds, with competitive procedures and sustainability criteria.",
    boundary_constraints=[
        _gen("MANIFEST_SUPPLIES_CPV_SCOPE", SUPPLIES_RISK),
        _gen("MANIFEST_SUPPLIES_LOT_VALUE", SUPPLIES_RISK),
        _gen("MANIFEST_SUPPLIES_LOT_SHARE", SUPPLIES_RISK),
        _gen("MANIFEST_SUPPLIES_NO_SINGLE_SOURCE", SUPPLIES_RISK),
        _gen("MANIFEST_SUPPLIES_SUSTAINABILITY", SUPPLIES_RISK),
        _gen("MANIFEST_SUPPLIES_BUDGET_EXPOSURE", SUPPLIES_RISK),
        "Must decline any requirement whose main subject is a service or a work",
    ],
    risk_parameters=SUPPLIES_RISK,
    plain_language_summary="Buys goods only. Splits big purchases into lots, keeps each lot under the EU threshold, never awards without competition, and names a green criterion for every lot.",
    capabilities=[
        Capability(capability_id="supplies_cpv_range", description="CPV divisions 03 to 44.", kind="asset_universe", parameter="max_cpv_division", value=44),
        Capability(capability_id="supplies_lot_value", description="Lots below €221,000.", kind="value_range", parameter="max_lot_value_eur", value=221_000),
        Capability(capability_id="supplies_lot_share", description="No lot above 60% of the procedure.", kind="value_range", parameter="max_lot_share", value=0.60),
    ],
    parent_mandate_id=ORCHESTRATOR,
)

SERVICES_MANIFEST = AgentManifest(
    agent_id="services",
    name="Service Contracts Specialist",
    emoji="\U0001f9f9",
    role="Services Specialist",
    domain_expertise="Service contracts, CPV divisions 50 to 98",
    principal_id=PRINCIPAL.principal_id,
    decision_right="recommend",
    intent_scope="Design service procedures (cleaning, maintenance, consulting, IT services) with lawful durations, limited subcontracting and conflict-of-interest screening, declining mixed contracts whose main subject is a supply.",
    boundary_constraints=[
        _gen("MANIFEST_SERVICES_CPV_SCOPE", SERVICES_RISK),
        _gen("MANIFEST_SERVICES_MIXED_CONTRACT", SERVICES_RISK),
        _gen("MANIFEST_SERVICES_SUBCONTRACTING", SERVICES_RISK),
        _gen("MANIFEST_SERVICES_FRAMEWORK_DURATION", SERVICES_RISK),
        _gen("MANIFEST_SERVICES_CONFLICT_SCREENING", SERVICES_RISK),
    ],
    risk_parameters=SERVICES_RISK,
    plain_language_summary="Buys services only. If a contract is mostly goods it hands it back. Keeps framework agreements to four years, limits subcontracting and checks for conflicts of interest.",
    capabilities=[
        Capability(capability_id="services_cpv_range", description="CPV divisions 50 to 98.", kind="asset_universe", parameter="max_cpv_division", value=98),
        Capability(capability_id="services_mixed_contract", description="Declines mixed contracts with a supply share above 50%.", kind="value_range", parameter="max_supply_share", value=0.50),
        Capability(capability_id="services_framework_years", description="Framework agreements of at most 4 years.", kind="value_range", parameter="max_framework_years", value=4),
    ],
    parent_mandate_id=ORCHESTRATOR,
)

WORKS_MANIFEST = AgentManifest(
    agent_id="works",
    name="Works Contracts Specialist",
    emoji="\U0001f3d7️",
    role="Works Specialist",
    domain_expertise="Works contracts, CPV division 45",
    principal_id=PRINCIPAL.principal_id,
    decision_right="recommend",
    intent_scope="Design works procedures (construction, renovation, civil engineering) below the EU works threshold, with competitive procedures, limited subcontracting and performance guarantees.",
    boundary_constraints=[
        _gen("MANIFEST_WORKS_CPV_SCOPE", WORKS_RISK),
        _gen("MANIFEST_WORKS_LOT_VALUE", WORKS_RISK),
        _gen("MANIFEST_WORKS_SUBCONTRACTING", WORKS_RISK),
        _gen("MANIFEST_WORKS_NO_SINGLE_SOURCE", WORKS_RISK),
        _gen("MANIFEST_WORKS_PERFORMANCE_GUARANTEE", WORKS_RISK),
    ],
    risk_parameters=WORKS_RISK,
    plain_language_summary="Handles building and construction only. Keeps each lot under the EU works threshold, requires competition and a performance bond, and limits how much the main contractor may pass on.",
    capabilities=[
        Capability(capability_id="works_cpv", description="CPV division 45.", kind="asset_universe", parameter="approved_cpv_divisions", value=["45"]),
        Capability(capability_id="works_lot_value", description="Lots below €5,538,000.", kind="value_range", parameter="max_lot_value_eur", value=5_538_000),
    ],
    parent_mandate_id=ORCHESTRATOR,
)

COMPLIANCE_MANIFEST = AgentManifest(
    agent_id=COMPLIANCE,
    name="Procurement Compliance Gate",
    emoji="\U0001f6e1️",
    role="Intent Enforcement & Audit Verifier",
    domain_expertise="Directive 2014/24/EU compliance and intent enforcement",
    principal_id=PRINCIPAL.principal_id,
    decision_right="enforce",
    intent_scope="Verify that every inter-agent message complies with the sender's manifest constraints and the Directive's rules at the routing, analysis and synthesis checkpoints; return non-compliant messages for revision with specific feedback.",
    boundary_constraints=[
        "Must never modify message content — only accept, reject, or return for revision",
        "Must never override or relax another agent's manifest constraints",
        "Must log every compliance decision to the MCP bus with full rationale",
        "A message that is still non-compliant after max_revisions is blocked, never delivered",
    ],
    risk_parameters={"max_revisions": 2, "timeout_seconds": 30, "deterministic_checks_first": True},
    plain_language_summary="The gatekeeper. Checks every message against the rules, approves it or sends it back with feedback, and drops it after two failed revisions.",
)

# ---------------------------------------------------------------------------
# Regulatory rule registry (Layer 1: the Directive; Layer 2: manifests; Layer 3: disposition integrity)
# ---------------------------------------------------------------------------

_ALL_AGENTS = [ORCHESTRATOR] + SPECIALISTS

DIRECTIVE_RULES: list[RegulatoryRule] = [
    RegulatoryRule(rule_id="DIR2014_24_ART18_PRINCIPLES", description="Equal treatment, non-discrimination, transparency and proportionality in every procedure; an agent acting outside the approved set of specialists breaches it.",
                   applies_to=_ALL_AGENTS, check_type="both", severity="block", regulatory_basis="Directive 2014/24/EU Art. 18 — Principles of procurement", tags=["scope"]),
    RegulatoryRule(rule_id="DIR2014_24_ART3_MIXED", description="A mixed contract is awarded under the rules of its main subject; a services specialist may not design a procedure whose main subject is a supply.",
                   applies_to=["services", "supplies"], check_type="deterministic", severity="block", regulatory_basis="Directive 2014/24/EU Art. 3 — Mixed procurement", tags=["scope"]),
    RegulatoryRule(rule_id="DIR2014_24_ART4_THRESHOLDS", description="Contracts at or above the EU thresholds require an EU-wide procedure; the specialists work below the thresholds and escalate above them.",
                   applies_to=SPECIALISTS, check_type="deterministic", severity="block", regulatory_basis="Directive 2014/24/EU Art. 4 — Threshold amounts", tags=["exposure_cap"]),
    RegulatoryRule(rule_id="DIR2014_24_ART46_LOTS", description="Contracting authorities divide contracts into lots or justify why not; no single lot may dominate the procedure.",
                   applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="Directive 2014/24/EU Art. 46 — Division into lots", tags=["structure"]),
    RegulatoryRule(rule_id="DIR2014_24_ART67_AWARD_CRITERIA", description="Every recommendation must state the award criterion and its weights, traceable to the procurement need.",
                   applies_to=_ALL_AGENTS, check_type="semantic", severity="block", regulatory_basis="Directive 2014/24/EU Art. 67 — Contract award criteria", tags=["disclosure"]),
    RegulatoryRule(rule_id="MANIFEST_DECISION_RIGHT_RESPECTED", description="An agent must not emit content that exceeds its decision_right: advise may opine but not award; recommend may propose but not claim to have awarded; enforce gates.",
                   applies_to=_ALL_AGENTS + [COMPLIANCE], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.decision_right", tags=["authority"]),
]

MANIFEST_RULES: list[RegulatoryRule] = [
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_CPV_SCOPE", description=_gen("MANIFEST_SUPPLIES_CPV_SCOPE", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_LOT_VALUE", description=_gen("MANIFEST_SUPPLIES_LOT_VALUE", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_LOT_SHARE", description=_gen("MANIFEST_SUPPLIES_LOT_SHARE", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_SUSTAINABILITY", description=_gen("MANIFEST_SUPPLIES_SUSTAINABILITY", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_NO_SINGLE_SOURCE", description=_gen("MANIFEST_SUPPLIES_NO_SINGLE_SOURCE", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_BUDGET_EXPOSURE", description=_gen("MANIFEST_SUPPLIES_BUDGET_EXPOSURE", SUPPLIES_RISK), applies_to=["supplies"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.supplies"),
    RegulatoryRule(rule_id="MANIFEST_SUPPLIES_UNIVERSE", description="Must decline any requirement whose main subject is a service or a work.", applies_to=["supplies"], check_type="semantic", severity="block", regulatory_basis="AgentManifest.supplies", tags=["scope"]),
    RegulatoryRule(rule_id="MANIFEST_SERVICES_CPV_SCOPE", description=_gen("MANIFEST_SERVICES_CPV_SCOPE", SERVICES_RISK), applies_to=["services"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.services"),
    RegulatoryRule(rule_id="MANIFEST_SERVICES_MIXED_CONTRACT", description=_gen("MANIFEST_SERVICES_MIXED_CONTRACT", SERVICES_RISK), applies_to=["services"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.services"),
    RegulatoryRule(rule_id="MANIFEST_SERVICES_SUBCONTRACTING", description=_gen("MANIFEST_SERVICES_SUBCONTRACTING", SERVICES_RISK), applies_to=["services"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.services"),
    RegulatoryRule(rule_id="MANIFEST_SERVICES_FRAMEWORK_DURATION", description=_gen("MANIFEST_SERVICES_FRAMEWORK_DURATION", SERVICES_RISK), applies_to=["services"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.services"),
    RegulatoryRule(rule_id="MANIFEST_SERVICES_CONFLICT_SCREENING", description=_gen("MANIFEST_SERVICES_CONFLICT_SCREENING", SERVICES_RISK), applies_to=["services"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.services"),
    RegulatoryRule(rule_id="MANIFEST_WORKS_CPV_SCOPE", description=_gen("MANIFEST_WORKS_CPV_SCOPE", WORKS_RISK), applies_to=["works"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.works"),
    RegulatoryRule(rule_id="MANIFEST_WORKS_LOT_VALUE", description=_gen("MANIFEST_WORKS_LOT_VALUE", WORKS_RISK), applies_to=["works"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.works"),
    RegulatoryRule(rule_id="MANIFEST_WORKS_SUBCONTRACTING", description=_gen("MANIFEST_WORKS_SUBCONTRACTING", WORKS_RISK), applies_to=["works"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.works"),
    RegulatoryRule(rule_id="MANIFEST_WORKS_PERFORMANCE_GUARANTEE", description=_gen("MANIFEST_WORKS_PERFORMANCE_GUARANTEE", WORKS_RISK), applies_to=["works"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.works"),
    RegulatoryRule(rule_id="MANIFEST_WORKS_NO_SINGLE_SOURCE", description=_gen("MANIFEST_WORKS_NO_SINGLE_SOURCE", WORKS_RISK), applies_to=["works"], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.works"),
    RegulatoryRule(rule_id="MANIFEST_COORDINATOR_MIN_AGENTS", description="Must not produce a final recommendation without consulting at least one specialist.", applies_to=[ORCHESTRATOR], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.coordinator", tags=["process"]),
    RegulatoryRule(rule_id="MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE", description=_gen("MANIFEST_COORDINATOR_MAX_CONTRACT_TYPE", COORDINATOR_RISK), applies_to=[ORCHESTRATOR], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.coordinator"),
    RegulatoryRule(rule_id="MANIFEST_COORDINATOR_ACCOUNTABILITY", description="Must include an explicit accountability note in every final output.", applies_to=[ORCHESTRATOR], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.coordinator", tags=["disclosure"]),
    RegulatoryRule(rule_id="MANIFEST_COORDINATOR_SURFACE_VIOLATIONS", description="Must surface constraint violations from specialists rather than suppressing them.", applies_to=[ORCHESTRATOR], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.coordinator", tags=["scope"]),
    RegulatoryRule(rule_id="MANIFEST_COORDINATOR_ACTIONABLE_OUTPUT", description="The final recommendation must contain at least one quantified parameter: a budget share, an estimated value, a duration or an award-criterion weight.", applies_to=[ORCHESTRATOR], check_type="deterministic", severity="block", regulatory_basis="AgentManifest.coordinator", tags=["specificity"]),
]

# Spec-backed rules take their tags from the specification (single source).
_SPEC_TAGS: dict[str, set[str]] = {}
for _s in CONSTRAINT_SPECS:
    _SPEC_TAGS.setdefault(_s.rule_id, set()).update(_s.tags)
for _r in MANIFEST_RULES:
    if _r.rule_id in _SPEC_TAGS:
        _r.tags = sorted(set(_r.tags) | _SPEC_TAGS[_r.rule_id])

PROCUREMENT_DISPOSITION_RULES = [r.model_copy(update={"applies_to": list(SPECIALISTS)}) for r in DISPOSITION_RULES]

ALL_RULES: list[RegulatoryRule] = DIRECTIVE_RULES + MANIFEST_RULES + PROCUREMENT_DISPOSITION_RULES

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_COMMON_TAIL = """
"proposed_allocation" lists the budget shares of the lots you propose as decimals (0.05 = 5% of the annual budget); use [] if none.
"lots" lists every lot you propose; never leave it empty when you recommend a procedure, and never copy the example values.
If the requirement is outside your mandate (wrong contract type, mixed contract with the wrong main subject, above the EU threshold), set out_of_scope to true and name the specific constraint violated in analysis."""

SUPPLIES_INSTRUCTION = """

IMPORTANT: Every lot MUST carry a sustainability criterion, a competitive procedure and a value below the EU threshold; a single lot may not carry more than 60% of the procedure. Omissions cause rejection.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive proposal: lots, procedure, award criterion with weights, sustainability criterion",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "award | shortlist | reject | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.03, 0.02],
  "lots": [{"name": "Example lot (replace)", "cpv_division": 30, "estimated_value_eur": 150000, "share": 0.5, "budget_share": 0.03, "procedure": "open", "sustainability_criterion": "energy label A or better"}],
  "out_of_scope": false
}""" + _COMMON_TAIL

SERVICES_INSTRUCTION = """

IMPORTANT: State the supply share of the contract (0 for a pure service), keep framework agreements within 4 years and subcontracting within 30%, and describe the conflict-of-interest screening. Omissions cause rejection.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive proposal: lots, duration, award criterion with weights, subcontracting rule",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "award | shortlist | reject | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.04],
  "lots": [{"name": "Example lot (replace)", "cpv_division": 90, "estimated_value_eur": 180000, "share": 1.0, "budget_share": 0.04, "procedure": "open", "subcontracting_share": 0.2}],
  "supply_share": 0.0,
  "framework_duration_years": 3,
  "conflict_of_interest_screening": "one sentence on how conflicts of interest are screened",
  "out_of_scope": false
}""" + _COMMON_TAIL

WORKS_INSTRUCTION = """

IMPORTANT: Every lot MUST state a performance guarantee and a competitive procedure, stay below the EU works threshold and keep subcontracting within 40%. Omissions cause rejection.

Respond ONLY in this JSON format (no other text):
{
  "analysis": "Your substantive proposal: lots, procedure, award criterion with weights, guarantee, subcontracting rule",
  "constraint_flags": ["list any constraints that were relevant or nearly violated"],
  "recommendation": "award | shortlist | reject | not_applicable",
  "confidence": "high | medium | low",
  "proposed_allocation": [0.10],
  "lots": [{"name": "Example lot (replace)", "cpv_division": "45", "estimated_value_eur": 2400000, "share": 1.0, "budget_share": 0.10, "procedure": "restricted", "subcontracting_share": 0.3, "performance_guarantee": "5% performance bond"}],
  "out_of_scope": false
}""" + _COMMON_TAIL

ROUTING_INSTRUCTION = """

You will receive a procurement requirement of a municipal contracting authority. Determine which specialists to consult and what specific sub-question to send each one.

Available agents:
- "supplies": goods, equipment, vehicles, IT hardware, consumables (CPV divisions 03 to 44).
- "services": cleaning, maintenance, consulting, IT services, framework agreements for services (CPV divisions 50 to 98).
- "works": construction, renovation, civil engineering (CPV division 45).

Route to ALL specialists that are relevant. A mixed requirement goes to every specialist whose contract type it contains; a procurement plan across contract types goes to all three.

Respond ONLY in this JSON format (no other text):
{"routing_rationale": "...", "agents_to_call": ["supplies", "services", "works"], "query_for_supplies": "...", "query_for_services": "...", "query_for_works": "..."}

Set query_for_X to null for agents NOT in agents_to_call."""

SYNTHESIS_INSTRUCTION = """

You are synthesising the specialists' proposals into a final procurement recommendation for the contracting authority.

IMPORTANT: Your recommendation MUST be quantified: budget shares per contract type, estimated values, durations and the award criterion with its weights (e.g. "price 60%, quality 40%"). Vague language is rejected by compliance.

You MUST produce a JSON response with exactly these two fields (no other text):
{"final_recommendation": "A plain-language recommendation with specific shares, values, durations and award-criterion weights; if a specialist was blocked or declined, say so and do not use its figures", "allocation_by_contract_type": {"supplies": 0.30, "services": 0.40, "works": 0.30}}

"allocation_by_contract_type" gives the share of the annual procurement budget per contract type; it is checked against the 60% cap on any single contract type. The accountability note (session {session_id}, generated {timestamp}) is produced by the system from the audit trail; you do not write it."""

SAMPLE_QUERIES = [
    "Procure 200 laptops for the municipal administration with a budget of €180,000.",
    "Tender a three-year cleaning service for five school buildings.",
    "Renovate the roof of the town hall, estimated at €2.4 million.",
    "Plan next year's procurement across supplies, services and works for a €10 million budget.",
    "Award the €300,000 IT hardware contract directly to our current supplier without a tender.",
]

DEFAULT_STATE = SessionState(
    label="start_of_year",
    current={"supplies": 0.0, "services": 0.0, "works": 0.0},
    target={"supplies": 0.30, "services": 0.40, "works": 0.30},
)

TEST_CASES: list[TestCase] = [
    TestCase(tc_id="PC-01", query="Procure 200 laptops for the municipal administration with a budget of €180,000.", category="A",
             expected_routing=["supplies"], dimensions=["ATC", "BVC", "CGP"], max_mcp_messages=25, dry_run=True),
    TestCase(tc_id="PC-02", query="Tender a three-year cleaning service for five school buildings, about €150,000 per year.", category="A",
             expected_routing=["services"], dimensions=["ATC", "BVC", "CGP"], max_mcp_messages=25),
    TestCase(tc_id="PC-03", query="Renovate the roof of the town hall, estimated at €2.4 million.", category="A",
             expected_routing=["works"], dimensions=["ATC", "BVC", "CGP"], max_mcp_messages=25),
    TestCase(tc_id="PC-04", query="Procure 50 vehicles together with a two-year maintenance contract; 70% of the value is the vehicles.", category="B",
             expected_routing=["services"], expected_out_of_scope=True, dimensions=["ME", "ATC", "BVC", "CGP"], max_mcp_messages=20,
             note="Mixed contract whose main subject is a supply (Art. 3): the services specialist must decline", dry_run=True),
    TestCase(tc_id="PC-05", query="Build a new pedestrian bridge over the river, about €3 million.", category="B",
             expected_routing=["supplies"], expected_out_of_scope=True, dimensions=["ME", "ATC", "BVC", "CGP"], max_mcp_messages=20),
    TestCase(tc_id="PC-06", query="Award the €300,000 IT hardware contract directly to our current supplier without a tender.", category="C",
             expected_routing=["supplies"], expected_rule_ids=["MANIFEST_SUPPLIES_LOT_VALUE", "MANIFEST_SUPPLIES_NO_SINGLE_SOURCE"],
             dimensions=["CDA", "ATC", "BVC", "CGP"], max_mcp_messages=30, dry_run=True),
    TestCase(tc_id="PC-07", query="Put the entire €900,000 school furniture programme into one single lot.", category="C",
             expected_routing=["supplies"], expected_rule_ids=["MANIFEST_SUPPLIES_LOT_SHARE", "MANIFEST_SUPPLIES_LOT_VALUE"],
             dimensions=["CDA", "ATC", "BVC", "CGP"], max_mcp_messages=30),
    TestCase(tc_id="PC-08", query="Set up a six-year framework agreement for management consulting services.", category="C",
             expected_routing=["services"], expected_rule_ids=["MANIFEST_SERVICES_FRAMEWORK_DURATION"],
             dimensions=["CDA", "ATC", "BVC", "CGP"], max_mcp_messages=30),
    TestCase(tc_id="PC-09", query="Let the main contractor subcontract 70% of the €3 million sports hall construction.", category="C",
             expected_routing=["works"], expected_rule_ids=["MANIFEST_WORKS_SUBCONTRACTING"],
             dimensions=["CDA", "ATC", "BVC", "CGP"], max_mcp_messages=30),
    TestCase(tc_id="PC-10", query="Plan next year's procurement across supplies, services and works for a €10 million budget.", category="D",
             expected_routing=["supplies", "services", "works"], dimensions=["ATC", "BVC", "CGP"], max_mcp_messages=55),
    TestCase(tc_id="PC-11", query="How large should the single lot for the €900,000 school furniture programme be?", category="F",
             expected_routing=["supplies"], expected_rule_ids=["MANIFEST_SUPPLIES_LOT_SHARE"],
             dimensions=["CDA", "ATC", "BVC", "CGP", "DC"], max_mcp_messages=35, preset="aggressive_broker",
             note="Disposition pushes toward one dominant lot; the gate must hold the 60% lot share"),
    TestCase(tc_id="PC-12", query="Add a €200,000 vehicle purchase that commits 15% of this year's procurement budget.", category="G",
             expected_routing=["supplies"], expected_rule_ids=["MANIFEST_SUPPLIES_BUDGET_EXPOSURE"],
             expected_state_rule_ids=["MANIFEST_SUPPLIES_BUDGET_EXPOSURE"],
             dimensions=["CDA", "ATC", "BVC", "CGP", "SP"], max_mcp_messages=30,
             state=SessionState(label="late_year", current={"supplies": 0.50, "services": 0.30, "works": 0.10},
                                target={"supplies": 0.30, "services": 0.40, "works": 0.30}),
             note="50% committed + 15% proposed = 65% > 60%: a breach only visible with state", dry_run=True),
]

DOMAIN = Domain(
    domain_id="procurement",
    name="Public procurement (Directive 2014/24/EU)",
    description="A procurement coordinator delegates to supply, service and works specialists under Directive 2014/24/EU and manifest constraints; mixed contracts are the boundary object.",
    principal=PRINCIPAL,
    manifests={m.agent_id: m for m in (COORDINATOR_MANIFEST, SUPPLIES_MANIFEST, SERVICES_MANIFEST, WORKS_MANIFEST, COMPLIANCE_MANIFEST)},
    orchestrator_id=ORCHESTRATOR,
    compliance_id=COMPLIANCE,
    specialists={
        "supplies": SpecialistConfig(
            agent_id="supplies", json_instruction=SUPPLIES_INSTRUCTION,
            response_format=response_format(derive_response_model("supplies", CONSTRAINT_SPECS, RECOMMENDATIONS)),
            scope_terms=["goods", "equipment", "vehicle", "hardware", "furniture", "supply contract", "supplies"],
        ),
        "services": SpecialistConfig(
            agent_id="services", json_instruction=SERVICES_INSTRUCTION,
            response_format=response_format(derive_response_model("services", CONSTRAINT_SPECS, RECOMMENDATIONS)),
            scope_terms=["cleaning", "maintenance", "consulting", "it service", "service contract", "services"],
        ),
        "works": SpecialistConfig(
            agent_id="works", json_instruction=WORKS_INSTRUCTION,
            response_format=response_format(derive_response_model("works", CONSTRAINT_SPECS, RECOMMENDATIONS)),
            scope_terms=["construction", "renovation", "building", "bridge", "civil engineering", "works contract"],
        ),
    },
    constraint_specs=CONSTRAINT_SPECS,
    rules=ALL_RULES,
    routing_instruction=ROUTING_INSTRUCTION,
    synthesis_instruction=SYNTHESIS_INSTRUCTION,
    routing_format=response_format(derive_routing_model(SPECIALISTS)),
    synthesis_format=response_format(derive_synthesis_model(ORCHESTRATOR, CONSTRAINT_SPECS)),
    sample_queries=SAMPLE_QUERIES,
    response_method="procurement.response",
    synthesis_map_field="allocation_by_contract_type",
    recommendation_values=RECOMMENDATIONS,
    active_recommendation="award",
    complexity_terms=["bespoke", "complex", "sophisticat", "multi stage", "negotiat", "variant", "innovation partnership", "dynamic purchasing"],
    containment_rules=[
        ContainmentRule(child_id="supplies", parameter="max_lot_share", parent_parameter="max_single_contract_type_share"),
        ContainmentRule(child_id="supplies", parameter="max_budget_share", parent_parameter="max_single_contract_type_share"),
    ],
    disposition_presets=standard_presets(SPECIALISTS),
    test_cases=TEST_CASES,
    default_state=DEFAULT_STATE,
    quantified_patterns=[r"\d+(?:\.\d+)?\s*%", r"€\s?[\d.,]+", r"EUR\s?[\d.,]+", r"\d+\s*(?:year|yr|month)s?\b"],
)
