"""UFO-C delegation constructs: commitments, claims and delegation relators binding Principal, Orchestrator and sub-agents."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agents.manifests import AgentManifest, get_manifest, get_principal
from agents.regulatory_rules import get_rules_for_agent


class Commitment(BaseModel):
    """Social mode that inheres in the committed party and externally depends on the beneficiary (UFO-C)."""

    commitment_id: str
    committed_party: str        # agent_id of the party that commits
    beneficiary: str            # principal_id or agent_id entitled to the commitment
    mandate_id: str             # the Mandate whose constraints give the commitment its content
    content: str
    rule_ids: list[str]         # rule identifiers that operationalise the commitment


class Claim(BaseModel):
    """Counterpart of a Commitment: the beneficiary's entitlement against the committed party (UFO-C)."""

    claim_id: str
    holder: str
    against: str
    mandate_id: str
    commitment_id: str
    content: str


class Delegation(BaseModel):
    """Relator that mediates delegator and delegatee and is constituted by a commitment and a claim (UFO-C)."""

    delegation_id: str
    delegator: str              # principal_id or agent_id
    delegatee: str              # agent_id
    mandate_id: str
    parent_delegation_id: str | None
    commitment: Commitment
    claim: Claim


class ContainmentCheck(BaseModel):
    """Result of comparing one parameter of a sub-mandate with the governing parameter of its parent."""

    parent_id: str
    child_id: str
    parameter: str
    parent_parameter: str
    parent_value: Any
    child_value: Any
    contained: bool
    note: str


# Which numeric parameter of a sub-mandate is bounded by which parameter of the parent.
# A sub-mandate may never grant more than the parent mandate holds.
CONTAINMENT_MAP: dict[tuple[str, str], str] = {
    ("stocks", "max_single_position"): "max_single_asset_class",
    ("materials", "max_total_allocation"): "max_single_asset_class",
}


def _make_delegation(delegator: str, manifest: AgentManifest, parent_delegation_id: str | None) -> Delegation:
    """Construct the delegation relator, commitment and claim for one delegator-delegatee pair."""
    rule_ids = [rule.rule_id for rule in get_rules_for_agent(manifest.agent_id)]
    commitment_id = f"commitment:{manifest.agent_id}->{delegator}"
    commitment = Commitment(
        commitment_id=commitment_id,
        committed_party=manifest.agent_id,
        beneficiary=delegator,
        mandate_id=manifest.agent_id,
        content=(
            f"Act only within the intent scope of mandate '{manifest.agent_id}' and "
            f"never violate its boundary constraints"
        ),
        rule_ids=rule_ids,
    )
    claim = Claim(
        claim_id=f"claim:{delegator}->{manifest.agent_id}",
        holder=delegator,
        against=manifest.agent_id,
        mandate_id=manifest.agent_id,
        commitment_id=commitment_id,
        content=(
            f"Entitled to outputs of '{manifest.agent_id}' that satisfy its mandate, "
            f"and to a verdict naming every breach"
        ),
    )
    return Delegation(
        delegation_id=f"delegation:{delegator}->{manifest.agent_id}",
        delegator=delegator,
        delegatee=manifest.agent_id,
        mandate_id=manifest.agent_id,
        parent_delegation_id=parent_delegation_id,
        commitment=commitment,
        claim=claim,
    )


def build_delegation_chain(principal_id: str = "anonymous", root_agent_id: str = "central") -> list[Delegation]:
    """Build the delegation chain Principal -> root agent -> sub-agents from the manifest registry."""
    principal = get_principal(principal_id)
    root = get_manifest(root_agent_id)
    root_delegation = _make_delegation(principal.principal_id, root, parent_delegation_id=None)
    chain = [root_delegation]
    for sub_id in root.sub_mandate_ids:
        sub = get_manifest(sub_id)
        chain.append(_make_delegation(root.agent_id, sub, parent_delegation_id=root_delegation.delegation_id))
    return chain


def check_mandate_containment(parent: AgentManifest, child: AgentManifest) -> list[ContainmentCheck]:
    """Check that a sub-mandate is structurally and numerically contained in its parent mandate."""
    checks: list[ContainmentCheck] = [
        ContainmentCheck(
            parent_id=parent.agent_id,
            child_id=child.agent_id,
            parameter="parent_mandate_id",
            parent_parameter="agent_id",
            parent_value=parent.agent_id,
            child_value=child.parent_mandate_id,
            contained=child.parent_mandate_id == parent.agent_id,
            note="Sub-mandate must name the parent mandate it decomposes",
        ),
        ContainmentCheck(
            parent_id=parent.agent_id,
            child_id=child.agent_id,
            parameter="principal_id",
            parent_parameter="principal_id",
            parent_value=parent.principal_id,
            child_value=child.principal_id,
            contained=child.principal_id == parent.principal_id,
            note="Parent and sub-mandate must be owned by the same Principal",
        ),
    ]
    for (agent_id, parameter), parent_parameter in CONTAINMENT_MAP.items():
        if agent_id != child.agent_id:
            continue
        child_value = child.risk_parameters.get(parameter)
        parent_value = parent.risk_parameters.get(parent_parameter)
        if child_value is None or parent_value is None:
            continue
        checks.append(ContainmentCheck(
            parent_id=parent.agent_id,
            child_id=child.agent_id,
            parameter=parameter,
            parent_parameter=parent_parameter,
            parent_value=parent_value,
            child_value=child_value,
            contained=float(child_value) <= float(parent_value),
            note="A sub-mandate may not grant a larger allocation than the parent mandate permits",
        ))
    return checks


def check_chain_containment(chain: list[Delegation]) -> list[ContainmentCheck]:
    """Run containment checks for every delegation in the chain whose delegator is itself an agent."""
    agent_ids = {d.delegatee for d in chain}
    results: list[ContainmentCheck] = []
    for delegation in chain:
        if delegation.delegator not in agent_ids:
            continue  # delegator is the Principal; no parent mandate to compare with
        parent = get_manifest(delegation.delegator)
        child = get_manifest(delegation.delegatee)
        results.extend(check_mandate_containment(parent, child))
    return results


def resolve_accountability(agent_id: str, chain: list[Delegation]) -> list[Delegation]:
    """Return the delegations from the agent's own delegation up to the Principal, nearest first."""
    by_id = {d.delegation_id: d for d in chain}
    current = next((d for d in chain if d.delegatee == agent_id), None)
    path: list[Delegation] = []
    while current is not None:
        path.append(current)
        current = by_id.get(current.parent_delegation_id) if current.parent_delegation_id else None
    return path


def accountability_record(agent_id: str, chain: list[Delegation], violated_rules: list[str]) -> dict[str, Any]:
    """Describe which commitment an agent breached and to whom it is answerable, for the audit log."""
    path = resolve_accountability(agent_id, chain)
    if not path:
        return {"agent": agent_id, "chain": [], "answerable_to": [], "violated_rules": violated_rules}
    own = path[0]
    return {
        "agent": agent_id,
        "breached_commitment": own.commitment.commitment_id,
        "claim_held_by": own.claim.holder,
        "answerable_to": [d.delegator for d in path],
        "principal": path[-1].delegator,
        "chain": [
            {"delegation_id": d.delegation_id, "delegator": d.delegator, "delegatee": d.delegatee}
            for d in path
        ],
        "violated_rules": violated_rules,
        "rules_in_commitment": [r for r in violated_rules if r in own.commitment.rule_ids],
    }
