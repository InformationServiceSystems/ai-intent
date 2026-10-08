"""Domain package: everything domain-specific in one object, so the kernel (orchestrator, gate, log, export, checks) stays generic."""

from __future__ import annotations

import importlib
import os
import threading
from typing import Any

from pydantic import BaseModel, ConfigDict

from agents.constraint_spec import ConstraintSpec
from agents.manifests import AgentManifest, Principal
from agents.regulatory_rules import RegulatoryRule


class SpecialistConfig(BaseModel):
    """What distinguishes one specialist from another: its manifest, its response instruction and its response schema."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_id: str
    json_instruction: str                 # appended to the manifest system prompt
    response_format: dict[str, Any]       # OpenAI-style JSON schema passed to the serving layer


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

    @property
    def specialist_ids(self) -> list[str]:
        """Agent ids of the specialists in routing order."""
        return list(self.specialists)

    def manifest(self, agent_id: str) -> AgentManifest:
        """Return an agent's manifest, raising KeyError if unknown."""
        return self.manifests[agent_id]


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
    """Make a domain active (used by tests and by a future domain switch in the UI)."""
    global _active
    with _lock:
        _active = domain
    return domain
