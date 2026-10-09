"""The third domain (ROADMAP 3.3): every clinical norm with an exception behaves as specified, without a model.

Runnable without pytest:  python tests/test_clinical_domain.py
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if "openai" not in sys.modules:
    _openai = types.ModuleType("openai")

    class _StubOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    _openai.OpenAI = _StubOpenAI
    sys.modules["openai"] = _openai

from agents.compliance import _check_boundary_constraints  # noqa: E402
from agents.domain import SessionState, load_domain, set_domain  # noqa: E402
from agents.norms import MandateAmendment, admit  # noqa: E402

CLIN = load_domain("clinical")


def _verdict(agent, payload, state=None):
    set_domain(CLIN)
    try:
        return {r.rule_id: r for r in _check_boundary_constraints(agent, payload, state) if r.rule_id}
    finally:
        set_domain(load_domain("finance"))


def _abx(drug, indication, days, **extra):
    return dict({"analysis": "x", "orders": [{"name": "o", "drug": drug, "agent_type": "antibacterial", "indication": indication, "duration_days": days}]}, **extra)


def test_domain_is_clean_and_disclaimed():
    """Design checks and spec consistency are clean; every specialist scope carries the disclaimer."""
    from evaluation.design_checks import run_design_checks
    assert run_design_checks(CLIN) == []
    assert all("NOT CLINICAL GUIDANCE" in CLIN.manifest(a).intent_scope for a in CLIN.specialist_ids)


def test_restricted_antibiotic_needs_documented_approval():
    """Meropenem fails without approval, fails with the flag but no reference, passes with both."""
    assert _verdict("antimicrobial", _abx("meropenem", "ESBL bacteraemia", 10))["MANIFEST_ANTIMICROBIAL_RESTRICTED"].passed is False
    flag_only = _abx("meropenem", "ESBL bacteraemia", 10, id_approval_documented=True, id_approval_reference="")
    assert _verdict("antimicrobial", flag_only)["MANIFEST_ANTIMICROBIAL_RESTRICTED"].passed is False
    approved = _abx("meropenem", "ESBL bacteraemia", 10, id_approval_documented=True, id_approval_reference="ID-2026-114")
    r = _verdict("antimicrobial", approved)["MANIFEST_ANTIMICROBIAL_RESTRICTED"]
    assert r.passed and r.exceptions_applied[0]["exception_id"] == "EXC_ID_APPROVAL"


def test_long_course_exception_has_its_own_bound():
    """42 days for osteomyelitis passes under the long-course bound, 60 days does not, 21 days for cystitis does not."""
    assert _verdict("antimicrobial", _abx("rifampicin", "chronic osteomyelitis", 42))["MANIFEST_ANTIMICROBIAL_DURATION"].passed
    assert _verdict("antimicrobial", _abx("rifampicin", "chronic osteomyelitis", 60))["MANIFEST_ANTIMICROBIAL_DURATION"].passed is False
    assert _verdict("antimicrobial", _abx("nitrofurantoin", "cystitis", 21))["MANIFEST_ANTIMICROBIAL_DURATION"].passed is False


def test_opioid_ceiling_and_palliative_exception():
    """80 + 30 MME breaches the 90 ceiling; under a documented palliative plan the ceiling is defeated."""
    st = SessionState(label="on_80", current={"opioid_mme_per_day": 80.0})
    orders = [{"name": "o", "drug": "oxycodone", "route": "oral", "fraction_of_max_daily_dose": 0.3, "mme_per_day": 30}]
    r = _verdict("analgesia", {"analysis": "x", "orders": orders, "pain_assessment": "NRS 8"}, st)["MANIFEST_ANALGESIA_OPIOID_CEILING"]
    assert r.passed is False and "110" in r.detail
    pall = {"analysis": "x", "orders": orders, "pain_assessment": "NRS 8", "palliative_care_plan": True, "palliative_plan_reference": "PC-2026-07"}
    r = _verdict("analgesia", pall, st)["MANIFEST_ANALGESIA_OPIOID_CEILING"]
    assert r.passed and r.exceptions_applied[0]["exception_id"] == "EXC_PALLIATIVE"


def test_warfarin_only_for_a_mechanical_valve():
    """Warfarin is outside the formulary for atrial fibrillation and exempt for a mechanical valve."""
    af = {"analysis": "x", "orders": [{"name": "o", "drug": "warfarin", "indication": "atrial fibrillation", "fraction_of_max_daily_dose": 0.5}],
          "anticoagulant_count": 1, "bleeding_risk_assessment": "HAS-BLED 2"}
    assert _verdict("anticoagulation", af)["MANIFEST_ANTICOAGULATION_FORMULARY"].passed is False
    valve = dict(af, orders=[dict(af["orders"][0], indication="mechanical mitral valve")])
    r = _verdict("anticoagulation", valve)["MANIFEST_ANTICOAGULATION_FORMULARY"]
    assert r.passed and r.exceptions_applied[0]["exception_id"] == "EXC_WARFARIN_MECHANICAL_VALVE"


def test_committee_amendment():
    """The committee may raise the course limit to 21 days; a non-member may not; 50 days breaks the long-course bound's role."""
    ok, amended = admit(CLIN, MandateAmendment(amendment_id="AM-1", principal_id="medicines_committee", agent_id="antimicrobial",
                                               parameter="max_course_days", new_value=21, reason="study protocol"))
    assert ok.admitted and "No antibiotic course longer than 21 days" in amended.manifest("antimicrobial").boundary_constraints
    other, _ = admit(CLIN, MandateAmendment(amendment_id="AM-2", principal_id="anonymous", agent_id="antimicrobial",
                                            parameter="max_course_days", new_value=21, reason="x"))
    assert not other.admitted


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
