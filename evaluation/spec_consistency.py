"""Specification-predicate consistency: text, predicate and manifest of every boundary constraint are generated from one spec; this check is the regression guard."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.manifests import get_manifest  # noqa: E402
from agents.regulatory_rules import BOUNDARY_CONSTRAINT_INDEX, BoundaryConstraint  # noqa: E402


class Finding(BaseModel):
    """One inconsistency between the parts of a boundary constraint."""

    check: str
    rule_id: str
    agent_id: str
    detail: str


_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*years?")
_WORD = re.compile(r"[a-z][a-z'\-]+")


def _bound(bc: BoundaryConstraint) -> float | None:
    """Return the numeric bound the predicate evaluates against, from the agent's manifest."""
    key = bc.predicate.risk_param_key
    if not key:
        return None
    value = get_manifest(bc.agent_id).risk_parameters.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def check_text_matches_bound(bc: BoundaryConstraint) -> list[Finding]:
    """C1: a threshold constraint's text must state the same number the predicate enforces."""
    if bc.predicate.kind == "min_threshold":
        bound = _bound(bc)
        if bound is None or f"{bound / 1e9:g} billion" not in bc.text:
            return [Finding(check="C1_BOUND", rule_id=bc.rule_id, agent_id=bc.agent_id,
                            detail=f"text does not state the floor of {bound} (expected '{(bound or 0) / 1e9:g} billion')")]
        return []
    if bc.predicate.kind != "max_threshold":
        return []
    bound = _bound(bc)
    if bound is None:
        return [Finding(check="C1_BOUND", rule_id=bc.rule_id, agent_id=bc.agent_id,
                        detail=f"predicate refers to risk parameter {bc.predicate.risk_param_key!r} which the manifest does not define numerically")]
    if bc.predicate.extract == "percent":
        stated = [float(x) for x in _PERCENT.findall(bc.text)]
        expected = round(bound * 100, 6)
    else:
        stated = [float(x) for x in _YEARS.findall(bc.text)]
        expected = bound
    if not stated:
        return [Finding(check="C1_BOUND", rule_id=bc.rule_id, agent_id=bc.agent_id,
                        detail=f"text states no number but the predicate enforces {expected}")]
    if expected not in stated:
        return [Finding(check="C1_BOUND", rule_id=bc.rule_id, agent_id=bc.agent_id,
                        detail=f"text states {stated} but the predicate enforces {expected} (risk parameter {bc.predicate.risk_param_key})")]
    return []


def _alternatives(pattern: str) -> list[str]:
    """Reduce a regex of alternatives to plain lowercase stems for matching against the text."""
    cleaned = re.sub(r"\\b", "", pattern)
    cleaned = cleaned.replace("[- ]?", "-").replace("\\s*", " ").replace("s*", "s")
    cleaned = re.sub(r"\(\?:|[()\\^$?]", "", cleaned)
    return [a.strip().lower() for a in cleaned.split("|") if a.strip()]


def check_text_names_terms(bc: BoundaryConstraint) -> list[Finding]:
    """C2: a term-based constraint's text must name at least one of the terms the predicate looks for."""
    text = bc.text.lower()
    if bc.predicate.kind == "in_set" and bc.predicate.set_param_key:
        allowed = get_manifest(bc.agent_id).risk_parameters.get(bc.predicate.set_param_key, [])
        missing = [a for a in allowed if str(a).lower() not in text]
        if missing:
            return [Finding(check="C2_TERMS", rule_id=bc.rule_id, agent_id=bc.agent_id,
                            detail=f"text does not name the allowed set members {missing}")]
    if bc.predicate.kind in ("forbidden_term", "in_set", "min_threshold") and bc.predicate.term_pattern:
        alts = _alternatives(bc.predicate.term_pattern)
        if not any(a[:5] in text for a in alts):
            return [Finding(check="C2_TERMS", rule_id=bc.rule_id, agent_id=bc.agent_id,
                            detail=f"text names none of the forbidden terms {alts[:6]}")]
    if bc.predicate.kind == "required_term" and bc.predicate.synonyms:
        if not any(s.lower()[:5] in text for s in bc.predicate.synonyms):
            return [Finding(check="C2_TERMS", rule_id=bc.rule_id, agent_id=bc.agent_id,
                            detail=f"text names none of the required disclosure terms {bc.predicate.synonyms[:6]}")]
    return []


def check_registry_matches_manifest(agent_id: str) -> list[Finding]:
    """C3: the text the gate cites must be the text the agent was given in its manifest."""
    manifest_texts = get_manifest(agent_id).boundary_constraints
    findings = []
    for bc in BOUNDARY_CONSTRAINT_INDEX.get(agent_id, []):
        if bc.text in manifest_texts:
            continue
        if any(m.startswith(bc.text) or bc.text in m for m in manifest_texts):
            findings.append(Finding(check="C3_MANIFEST", rule_id=bc.rule_id, agent_id=agent_id,
                                    detail=f"registry text is a fragment of a manifest constraint: {bc.text!r}"))
        else:
            findings.append(Finding(check="C3_MANIFEST", rule_id=bc.rule_id, agent_id=agent_id,
                                    detail=f"registry text does not occur in the manifest: {bc.text!r}"))
    return findings


def check_manifest_coverage(agent_id: str) -> list[Finding]:
    """C4: a manifest constraint that states a number or a prohibition should have a predicate."""
    covered = " ".join(bc.text.lower() for bc in BOUNDARY_CONSTRAINT_INDEX.get(agent_id, []))
    findings = []
    for text in get_manifest(agent_id).boundary_constraints:
        has_number = bool(_PERCENT.search(text) or _YEARS.search(text) or re.search(r"\$\d", text))
        prohibition = text.lower().startswith("no ") or " must not " in text.lower() or "only" in text.lower()
        words = set(_WORD.findall(text.lower()))
        overlap = len(words & set(_WORD.findall(covered))) / max(1, len(words))
        if (has_number or prohibition) and overlap < 0.5:
            findings.append(Finding(check="C4_COVERAGE", rule_id="-", agent_id=agent_id,
                                    detail=f"manifest constraint has no predicate: {text!r}"))
    return findings


def run_all() -> list[Finding]:
    """Run C1 to C4 over every agent and constraint."""
    findings: list[Finding] = []
    for agent_id, constraints in BOUNDARY_CONSTRAINT_INDEX.items():
        for bc in constraints:
            findings += check_text_matches_bound(bc)
            findings += check_text_names_terms(bc)
        findings += check_registry_matches_manifest(agent_id)
        findings += check_manifest_coverage(agent_id)
    return findings


def main() -> int:
    """Print the findings and exit non-zero if any C1 or C2 inconsistency exists."""
    findings = run_all()
    total = sum(len(v) for v in BOUNDARY_CONSTRAINT_INDEX.values())
    print(f"{total} boundary constraints checked, {len(findings)} findings")
    for f in findings:
        print(f"  [{f.check}] {f.agent_id} {f.rule_id}: {f.detail}")
    hard = [f for f in findings if f.check in ("C1_BOUND", "C2_TERMS")]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
