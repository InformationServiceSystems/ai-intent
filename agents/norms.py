"""Defeasible norms and session-mutable Mandates (ROADMAP 1.3).

Two extensions of the ER 2026 model, which has no exception structure and immutable Mandates:

1. **Norm exceptions.** A `NormException` is a registered, stronger norm that defeats a boundary
   constraint for the items it covers: it either exempts them or subjects them to its own bound.
   Exceptions of one constraint are ordered by priority; the first that applies to an item wins
   (lexicographic priority). Every application is recorded on the rule result, so the trace shows
   which norm was defeated by which exception for which item.

2. **Mandate amendments.** A `MandateAmendment` is a governance event by which the Principal changes
   one risk parameter of a Mandate it owns, at session start or before the synthesis. An amendment is
   admitted only if the Principal owns the Mandate, the amended Mandate stays contained in its parent,
   and the design-time checks (ROADMAP 2.2) report nothing new. Admitted amendments produce a
   session-scoped copy of the domain; the registered Mandates are never mutated, so invariant 5
   ("Manifests are immutable at runtime") holds for the registry while the session's Mandate changes
   through an auditable event.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from typing import Any, Iterator, Literal

from pydantic import BaseModel, Field


class NormException(BaseModel):
    """A stronger norm that defeats one boundary constraint for the items it covers."""

    exception_id: str                       # registered rule id, e.g. "EXC_STOCKS_INDEX_FUND"
    defeats: str                            # rule id of the defeated boundary constraint
    description: str
    regulatory_basis: str
    priority: int = 1                       # higher first
    # Applicability: an item is covered if item[when_key] contains one of when_values (case-insensitive),
    # or, for payload-level exceptions, if payload[when_field] is truthy.
    when_key: str | None = None
    when_values: list[str] = []
    when_field: str | None = None
    requires_field: str | None = None       # a justification the payload must state for the exception to apply
    effect: Literal["exempt", "bound"] = "exempt"
    bound_param_key: str | None = None      # for effect "bound": the risk parameter holding the exception's bound


class ExceptionApplication(BaseModel):
    """One exception applied to one item (or to the payload) during an evaluation."""

    exception_id: str
    defeats: str
    item: str
    effect: str
    bound: Any = None


def applies(exc: NormException, item: dict[str, Any] | None, payload: dict[str, Any]) -> bool:
    """Whether an exception covers an item (or, without item key, the payload)."""
    if exc.requires_field and not str(payload.get(exc.requires_field) or "").strip():
        return False
    if exc.when_field is not None:
        return bool(payload.get(exc.when_field))
    if exc.when_key is None or item is None:
        return False
    value = str(item.get(exc.when_key, "")).lower()
    return any(v.lower() in value for v in exc.when_values)


def first_applicable(exceptions: list[NormException], item: dict[str, Any] | None, payload: dict[str, Any]) -> NormException | None:
    """The highest-priority exception that covers the item (lexicographic priority)."""
    for exc in sorted(exceptions, key=lambda e: -e.priority):
        if applies(exc, item, payload):
            return exc
    return None


# ---------------------------------------------------------------------------
# Mandate amendments
# ---------------------------------------------------------------------------

class MandateAmendment(BaseModel):
    """A Principal's change of one risk parameter of one Mandate, as a governance event."""

    amendment_id: str
    principal_id: str
    agent_id: str
    parameter: str
    new_value: Any
    reason: str
    phase: Literal["start", "before_synthesis"] = "start"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AmendmentDecision(BaseModel):
    """The outcome of admitting an amendment, logged as governance.amend or governance.amend.rejected."""

    amendment: MandateAmendment
    admitted: bool
    old_value: Any = None
    reasons: list[str] = []


def admit(domain, amendment: MandateAmendment):
    """Check an amendment against ownership, containment and the design-time checks; return (decision, amended domain or None)."""
    from agents.delegation import check_mandate_containment
    from evaluation.design_checks import run_design_checks

    reasons: list[str] = []
    if amendment.agent_id not in domain.manifests:
        return AmendmentDecision(amendment=amendment, admitted=False, reasons=[f"unknown Mandate {amendment.agent_id!r}"]), None
    manifest = domain.manifest(amendment.agent_id)
    owner = manifest.principal_id or domain.principal.principal_id
    owned = amendment.agent_id in (domain.principal.owned_mandate_ids or []) and domain.principal.principal_id == amendment.principal_id
    if amendment.principal_id != owner and not owned:
        reasons.append(f"principal {amendment.principal_id!r} does not own Mandate {amendment.agent_id!r}")
    if amendment.parameter not in manifest.risk_parameters:
        reasons.append(f"Mandate {amendment.agent_id!r} has no parameter {amendment.parameter!r}")
    old = manifest.risk_parameters.get(amendment.parameter)
    if reasons:
        return AmendmentDecision(amendment=amendment, admitted=False, old_value=old, reasons=reasons), None

    amended = amended_domain(domain, [amendment])
    child = amended.manifest(amendment.agent_id)
    if child.parent_mandate_id:
        parent = amended.manifest(child.parent_mandate_id)
        for c in check_mandate_containment(parent, child):
            if not c.contained:
                reasons.append(f"containment: {c.parameter}={c.child_value} exceeds parent {c.parent_parameter}={c.parent_value}")
    for sub_id in child.sub_mandate_ids:
        for c in check_mandate_containment(child, amended.manifest(sub_id)):
            if not c.contained:
                reasons.append(f"containment: sub-mandate {sub_id} {c.parameter}={c.child_value} exceeds {c.parent_parameter}={c.parent_value}")
    before = {(f.check, f.subject, f.detail) for f in run_design_checks(domain)}
    after = [f for f in run_design_checks(amended) if (f.check, f.subject, f.detail) not in before]
    reasons += [f"design check {f.check}: {f.subject} {f.detail}" for f in after]
    decision = AmendmentDecision(amendment=amendment, admitted=not reasons, old_value=old, reasons=reasons)
    return decision, (amended if not reasons else None)


def amended_domain(domain, amendments: list[MandateAmendment]):
    """A deep copy of the domain with the amendments applied and constraint texts regenerated from the specs."""
    from agents.constraint_spec import render_text

    d = domain.model_copy(deep=True)
    for a in amendments:
        d.manifests[a.agent_id].risk_parameters[a.parameter] = a.new_value
    for agent_id, manifest in d.manifests.items():
        texts = list(manifest.boundary_constraints)
        for spec in d.specs_for(agent_id):
            old_text = render_text(spec, domain.manifest(agent_id).risk_parameters)
            new_text = render_text(spec, manifest.risk_parameters)
            texts = [new_text if t == old_text else t for t in texts]
        manifest.boundary_constraints = texts
    d._boundary_cache = {}
    return d


@contextlib.contextmanager
def session_domain(domain) -> Iterator[None]:
    """Make a session-scoped domain active for the duration of a block, then restore the previous one."""
    from agents import domain as domain_module

    previous = domain_module._active
    domain_module.set_domain(domain)
    try:
        yield
    finally:
        domain_module._active = previous
