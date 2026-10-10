"""The web app's governance controls (ROADMAP 1.1, 1.3, 2.2), driven headlessly with a stubbed model.

Runnable without pytest:  python tests/test_app_governance.py
"""

import json
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")


def _stub():
    import agents.compliance as comp
    import agents.orchestrator as orch
    import agents.specialist as spec
    import mcp.logger as lg

    def specialist(system, user, model=None, response_format=None, timeout=None):
        return json.dumps({"analysis": "Oxycodone.", "constraint_flags": [], "recommendation": "recommend", "confidence": "medium",
                           "proposed_allocation": [], "out_of_scope": False,
                           "orders": [{"name": "Oxycodone", "drug": "oxycodone", "route": "oral", "fraction_of_max_daily_dose": 0.3, "mme_per_day": 30}],
                           "pain_assessment": "NRS 8/10", "palliative_care_plan": False, "palliative_plan_reference": ""})

    def orchestrator(system, user, model=None, response_format=None, timeout=None):
        if "agents_to_call" in system:
            return json.dumps({"routing_rationale": "pain", "agents_to_call": ["analgesia"], "query_for_analgesia": "add oxycodone"})
        return json.dumps({"final_recommendation": "Add oral oxycodone 30 MME/day; the clinician decides.", "new_order_count": 1})

    saved = (spec.chat, orch.chat, comp.chat, lg._logger_instance)
    spec.chat, orch.chat, comp.chat = specialist, orchestrator, (lambda *a, **k: json.dumps({"results": []}))
    lg._logger_instance = lg.MCPLogger(tempfile.mkdtemp() + "/app.db")
    return saved


def _restore(saved):
    import agents.compliance as comp
    import agents.orchestrator as orch
    import agents.specialist as spec
    import mcp.logger as lg
    from agents.domain import load_domain, set_domain
    spec.chat, orch.chat, comp.chat, lg._logger_instance = saved
    set_domain(load_domain("finance"))


def test_state_and_owner_amendment_reach_the_gate():
    """On 80 MME/day a 30 MME order breaches the 90 ceiling; the committee's amendment to 120 admits it, in the app."""
    from streamlit.testing.v1 import AppTest
    saved = _stub()
    try:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.run()
        at.selectbox(key="domain_select").select("clinical").run()
        at.number_input(key="gov_cur_clinical_opioid_mme_per_day").set_value(80.0).run()
        at.selectbox(key="gov_am_agent").select("analgesia").run()
        at.selectbox(key="gov_am_param").select("max_opioid_mme_per_day").run()
        at.number_input(key="gov_am_value").set_value(120.0).run()
        at.button(key="gov_am_add").click().run()
        at.text_area(key="query_input").input("On 80 MME/day, add oxycodone.").run()
        next(b for b in at.button if b.label == "Run Analysis").click().run()
        assert not at.exception, [e.value for e in at.exception]
        r = at.session_state["last_result"]
        assert r.state_snapshot["label"] == "custom" and r.state_snapshot["current"]["opioid_mme_per_day"] == 80.0
        assert r.amendments[0]["admitted"] and r.amendments[0]["amendment"]["principal_id"] == "medicines_committee"
        assert r.forced_blocks == []
        assert any(t.label == "Governance" for t in at.tabs)
    finally:
        _restore(saved)


def test_without_amendment_the_ceiling_blocks():
    """The same order without the amendment is blocked on the opioid ceiling."""
    from streamlit.testing.v1 import AppTest
    saved = _stub()
    try:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.run()
        at.selectbox(key="domain_select").select("clinical").run()
        at.number_input(key="gov_cur_clinical_opioid_mme_per_day").set_value(80.0).run()
        at.text_area(key="query_input").input("On 80 MME/day, add oxycodone.").run()
        next(b for b in at.button if b.label == "Run Analysis").click().run()
        assert not at.exception
        assert at.session_state["last_result"].forced_blocks == ["analgesia"]
    finally:
        _restore(saved)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
