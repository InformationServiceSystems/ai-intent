"""Domain package: everything domain-specific in one object, so the kernel (orchestrator, gate, log, export, checks) stays generic.

The kernel never names an agent. It reads roles from the active Domain: the orchestrator
(the composite agent that routes and synthesises), the compliance gate, and the specialists
(the agents with a `recommend` decision right). Thresholds are read from the manifests'
risk parameters, vocabularies from the specialist configurations, and the finance-specific
tables that used to live in the kernel (disposition presets, containment rules, test cases)
are data of the domain package.
"""

from __future__ import annotations

import importlib
import os
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from agents.constraint_spec import BoundaryConstraint, ConstraintSpec, to_boundary_constraint
from agents.manifests import AgentManifest, DispositionProfile, Principal
from agents.norms import NormException
from agents.regulatory_rules import RegulatoryRule


class SpecialistConfig(BaseModel):
    """What distinguishes one specialist from another: its manifest, its response instruction, its schema and its vocabulary."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_id: str
    json_instruction: str                 # appended to the manifest system prompt
    response_format: dict[str, Any]       # OpenAI-style JSON schema passed to the serving layer
    # Terms that identify this specialist's subject matter in prose. The gate uses the union of
    # the OTHER specialists' terms as the cross-scope vocabulary of this agent, and the
    # evaluation uses them to recognise a decline that names the constraint.
    scope_terms: list[str] = []
    # Process rule: flags that speak of a violation while out_of_scope is false are inconsistent.
    self_assessment_check: bool = True


class ContainmentRule(BaseModel):
    """Which numeric parameter of a sub-mandate is bounded by which parameter of the parent mandate."""

    child_id: str
    parameter: str
    parent_parameter: str


class DispositionPreset(BaseModel):
    """A named disposition configuration: per-agent scores, a prompt modifier and the gate's revision multiplier."""

    label: str
    description: str
    scores: dict[str, DispositionProfile] | None   # None for the user-defined preset
    compliance_multiplier: float = 1.0
    system_prompt_modifier: str = ""


class SessionState(BaseModel):
    """The state a state predicate compares a proposed action with: current and target allocation per category (ROADMAP 1.1)."""

    current: dict[str, float] = {}
    target: dict[str, float] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    label: str = "default"

    def snapshot(self) -> dict[str, Any]:
        """The state as recorded in the Accountability Trace next to every verdict that used it."""
        return {"label": self.label, "current": dict(self.current), "target": dict(self.target), "timestamp": self.timestamp.isoformat()}


class TestCase(BaseModel):
    """One evaluation case of the domain: query, expected routing, expected rule ids and the dimensions scored."""

    tc_id: str
    query: str
    category: str
    expected_routing: list[str]
    forced_blocks_expected: int = 0
    expected_rule_ids: list[str] = []
    expected_out_of_scope: bool = False
    dimensions: list[str]
    max_mcp_messages: int = 40
    preset: str = "neutral"
    note: str = ""
    dry_run: bool = False
    # ROADMAP 1.1: rules whose verdict depends on the session state; scored under SP.
    expected_state_rule_ids: list[str] = []
    state: SessionState | None = None
    check_synthesis_accuracy: bool = False


class Domain(BaseModel):
    """A domain: principal, manifests, constraint specifications, rules, specialists and orchestrator instructions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    domain_id: str
    name: str
    description: str
    principal: Principal
    manifests: dict[str, AgentManifest]
    orchestrator_id: str
    compliance_id: str
    specialists: dict[str, SpecialistConfig]
    constraint_specs: list[ConstraintSpec]
    rules: list[RegulatoryRule]
    routing_instruction: str
    synthesis_instruction: str
    routing_format: dict[str, Any]
    synthesis_format: dict[str, Any]
    sample_queries: list[str]
    # The method name of the final output on the bus and the key of the quantified map the synthesis returns.
    response_method: str = "investment.response"
    synthesis_map_field: str = "allocation_by_asset_class"
    # Vocabulary of the recommendation field: the value that counts as acting, and the value for "none".
    recommendation_values: list[str] = ["buy", "hold", "sell", "not_applicable"]
    active_recommendation: str = "buy"
    # Terms the anti-customer integrity check counts as complexity indicators.
    complexity_terms: list[str] = []
    containment_rules: list[ContainmentRule] = []
    exceptions: list[NormException] = []     # defeasible norms (ROADMAP 1.3)
    disposition_presets: dict[str, DispositionPreset] = {}
    test_cases: list[TestCase] = []
    default_state: SessionState = SessionState()
    # Rule ids of the five disposition integrity rules the gate applies to specialists (kernel rules).
    quantified_patterns: list[str] = [r"\d+(?:\.\d+)?\s*%", r"\$[\d,]+", r"\d+\s*(?:year|yr|month)s?\b", r"[A-B][A-Ba-b][A-Ba-b][+-]?"]

    _boundary_cache: dict[str, list[BoundaryConstraint]] = PrivateAttr(default_factory=dict)

    @property
    def specialist_ids(self) -> list[str]:
        """Agent ids of the specialists in routing order."""
        return list(self.specialists)

    def manifest(self, agent_id: str) -> AgentManifest:
        """Return an agent's manifest, raising KeyError if unknown."""
        if agent_id not in self.manifests:
            raise KeyError(f"Unknown agent_id: {agent_id!r}")
        return self.manifests[agent_id]

    def specs_for(self, agent_id: str) -> list[ConstraintSpec]:
        """The constraint specifications of an agent in evaluation order."""
        return [s for s in self.constraint_specs if s.agent_id == agent_id]

    def boundary_constraints(self, agent_id: str) -> list[BoundaryConstraint]:
        """The <text, phi, tau> triples the gate evaluates for an agent, generated once from the specs and risk parameters."""
        if agent_id not in self._boundary_cache:
            params = self.manifest(agent_id).risk_parameters if agent_id in self.manifests else {}
            self._boundary_cache[agent_id] = [to_boundary_constraint(s, params) for s in self.specs_for(agent_id)]
        return self._boundary_cache[agent_id]

    def rule(self, rule_id: str) -> RegulatoryRule | None:
        """Return a registry rule by id, or None."""
        return next((r for r in self.rules if r.rule_id == rule_id), None)

    def rules_for(self, agent_id: str) -> list[RegulatoryRule]:
        """All registry rules that govern an agent."""
        return [r for r in self.rules if agent_id in r.applies_to]

    def tags_for_rule(self, rule_id: str) -> set[str]:
        """Tags of a rule: those of its constraint specification when one exists, else those of the registry entry."""
        tags: set[str] = set()
        for s in self.constraint_specs:
            if s.rule_id == rule_id:
                tags.update(s.tags)
        r = self.rule(rule_id)
        if r is not None:
            tags.update(r.tags)
        return tags

    def cap_parameter(self, agent_id: str) -> str | None:
        """The risk parameter of the agent's first percentage cap: the bound the risk-seeking check measures hugging against."""
        for s in self.specs_for(agent_id):
            if s.kind == "max" and s.unit == "percent" and s.risk_param_key:
                return s.risk_param_key
        return None

    def cross_scope_terms(self, agent_id: str) -> list[str]:
        """Terms that belong to the other specialists: a buy that cites them is scope creep."""
        terms: list[str] = []
        for other_id, cfg in self.specialists.items():
            if other_id != agent_id:
                terms.extend(cfg.scope_terms)
        return terms

    def all_scope_terms(self) -> list[str]:
        """Every specialist's scope terms."""
        return [t for cfg in self.specialists.values() for t in cfg.scope_terms]

    def preset(self, name: str) -> DispositionPreset:
        """A disposition preset by name, falling back to the neutral preset."""
        if name in self.disposition_presets:
            return self.disposition_presets[name]
        return self.disposition_presets["neutral"]


_lock = threading.Lock()
_active: Domain | None = None


def load_domain(name: str) -> Domain:
    """Import domains.<name> and return the Domain object it exposes as DOMAIN."""
    module = importlib.import_module(f"domains.{name}")
    return module.DOMAIN


def get_domain() -> Domain:
    """Return the active domain, loading it from AI_INTENT_DOMAIN (default: finance) on first use."""
    global _active
    if _active is None:
        with _lock:
            if _active is None:
                _active = load_domain(os.getenv("AI_INTENT_DOMAIN", "finance"))
    return _active


def set_domain(domain: Domain) -> Domain:
    """Make a domain active (used by tests, the evaluation runner and the domain switch in the UI)."""
    global _active
    with _lock:
        _active = domain
    return domain


def available_domains() -> list[str]:
    """Names of the domain packages under domains/ (modules that expose DOMAIN)."""
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "domains")
    names = []
    for fn in sorted(os.listdir(here)):
        if fn.endswith(".py") and not fn.startswith("_"):
            names.append(fn[:-3])
    return names
