"""Agent network visualization using HTML/CSS/SVG via streamlit components; the nodes are the active domain's agents."""

import streamlit as st
import streamlit.components.v1 as components

from agents.domain import get_domain

_PALETTE = ["#4ECDC4", "#45B7D1", "#F9A825", "#8BC34A", "#BA68C8", "#FF8A65"]
_ORCHESTRATOR_COLOR = "#FF6B6B"
_COMPLIANCE_COLOR = "#9C27B0"
_DIMMED = "#CCCCCC"


def render_agent_graph(
    agents_consulted: list[str] | None = None,
    violations: list[str] | None = None,
    compliance_status: str | None = None,
) -> None:
    """Render the agent network as an HTML/SVG diagram: orchestrator and gate on top, every specialist below, a gate dot on every edge."""
    domain = get_domain()
    oid, cid = domain.orchestrator_id, domain.compliance_id
    specialists = domain.specialist_ids
    colors = {oid: _ORCHESTRATOR_COLOR, cid: _COMPLIANCE_COLOR}
    for i, sid in enumerate(specialists):
        colors[sid] = _PALETTE[i % len(_PALETTE)]

    has_result = agents_consulted is not None
    consulted = set(agents_consulted or [])
    violated = set(violations or [])

    if has_result and compliance_status == "forced_block":
        comp_color = "#FF5722"
    elif has_result and compliance_status == "revision_requested":
        comp_color = "#FF9800"
    elif has_result:
        comp_color = "#4CAF50"
    else:
        comp_color = _COMPLIANCE_COLOR

    def _node_colors(agent_id: str) -> tuple[str, str, float]:
        """Return (bg, text_color, opacity)."""
        if has_result and agent_id not in consulted and agent_id not in (oid, cid):
            return _DIMMED, "#999", 0.4
        if has_result and agent_id in violated:
            return "#FF5722", "white", 1.0
        return colors.get(agent_id, "#999"), "white", 1.0

    def gate_color(agent_id: str) -> str:
        """Return gate dot color."""
        if has_result and agent_id not in consulted:
            return _DIMMED
        if has_result and agent_id in violated:
            return "#FF5722"
        return comp_color

    width = max(600, 200 * len(specialists))
    c_bg, c_fg, _ = _node_colors(oid)
    orchestrator = domain.manifest(oid)
    compliance = domain.manifest(cid)

    parts = [
        f'<rect x="{width/2 - 180:.0f}" y="10" width="280" height="50" rx="12" fill="{c_bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>',
        f'<text x="{width/2 - 40:.0f}" y="42" text-anchor="middle" fill="{c_fg}" font-size="16" font-weight="700">{orchestrator.emoji} {orchestrator.name}</text>',
        f'<rect x="{width - 170}" y="10" width="160" height="50" rx="12" fill="{comp_color}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>',
        f'<text x="{width - 90}" y="42" text-anchor="middle" fill="white" font-size="16" font-weight="700">{compliance.emoji} Compliance</text>',
    ]
    cx, cy = width / 2 - 40, 60
    slot = width / len(specialists)
    for i, sid in enumerate(specialists):
        m = domain.manifest(sid)
        x = slot * i + slot / 2
        bg, fg, op = _node_colors(sid)
        gx, gy = (cx + x) / 2, 140
        parts.append(f'<line x1="{cx:.0f}" y1="{cy}" x2="{x:.0f}" y2="220" stroke="#888" stroke-width="2"/>')
        parts.append(f'<polygon points="{x:.0f},220 {x-7:.0f},208 {x+7:.0f},208" fill="#888"/>')
        parts.append(f'<circle cx="{gx:.0f}" cy="{gy}" r="7" fill="{gate_color(sid)}"/>')
        parts.append(f'<line x1="{width - 90}" y1="60" x2="{gx:.0f}" y2="{gy}" stroke="{comp_color}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.5"/>')
        parts.append(
            f'<g opacity="{op}"><rect x="{x - slot/2 + 10:.0f}" y="225" width="{slot - 20:.0f}" height="50" rx="12" fill="{bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>'
            f'<text x="{x:.0f}" y="257" text-anchor="middle" fill="{fg}" font-size="15" font-weight="600">{m.emoji} {m.name}</text></g>'
        )

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<svg viewBox="0 0 {width} 340" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
{chr(10).join(parts)}
</svg>
</body></html>"""

    components.html(html, height=300, scrolling=False)

    st.caption("Click an agent to inspect its manifest:")
    all_agents = [orchestrator] + [domain.manifest(sid) for sid in specialists] + [compliance]
    cols = st.columns(len(all_agents))
    for i, m in enumerate(all_agents):
        with cols[i]:
            if st.button(f"{m.emoji}", key=f"select_{m.agent_id}", help=m.name):
                st.session_state["selected_agent"] = m.agent_id
