"""Agent network visualization using HTML/CSS/SVG via streamlit components."""

import streamlit as st
import streamlit.components.v1 as components

from agents.manifests import (
    CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST,
    MATERIALS_MANIFEST, COMPLIANCE_MANIFEST,
)

_SUB_AGENTS = [STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST]
_COLORS = {
    "central": "#FF6B6B",
    "compliance": "#9C27B0",
    "stocks": "#4ECDC4",
    "bonds": "#45B7D1",
    "materials": "#F9A825",
}
_DIMMED = "#CCCCCC"


def render_agent_graph(
    agents_consulted: list[str] | None = None,
    violations: list[str] | None = None,
    compliance_status: str | None = None,
) -> None:
    """Render the agent network as an HTML/SVG diagram."""
    has_result = agents_consulted is not None
    consulted = set(agents_consulted or [])
    violated = set(violations or [])

    # Compliance node color
    if has_result and compliance_status == "forced_block":
        comp_color = "#FF5722"
    elif has_result and compliance_status == "revision_requested":
        comp_color = "#FF9800"
    elif has_result:
        comp_color = "#4CAF50"
    else:
        comp_color = _COLORS["compliance"]

    def _node_colors(agent_id: str) -> tuple[str, str, float]:
        """Return (bg, text_color, opacity)."""
        if has_result and agent_id not in consulted and agent_id not in ("central", "compliance"):
            return _DIMMED, "#999", 0.4
        if has_result and agent_id in violated:
            return "#FF5722", "white", 1.0
        return _COLORS.get(agent_id, "#999"), "white", 1.0

    c_bg, c_fg, _ = _node_colors("central")
    s_bg, s_fg, s_op = _node_colors("stocks")
    b_bg, b_fg, b_op = _node_colors("bonds")
    m_bg, m_fg, m_op = _node_colors("materials")

    def gate_color(agent_id: str) -> str:
        """Return gate dot color."""
        if has_result and agent_id not in consulted:
            return _DIMMED
        if has_result and agent_id in violated:
            return "#FF5722"
        return comp_color

    sg = gate_color("stocks")
    bg = gate_color("bonds")
    mg = gate_color("materials")

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<svg viewBox="0 0 600 340" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">

  <!-- Central Orchestrator -->
  <rect x="120" y="10" width="280" height="50" rx="12" fill="{c_bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>
  <text x="260" y="42" text-anchor="middle" fill="{c_fg}" font-size="16" font-weight="700">{CENTRAL_MANIFEST.emoji} Central Investment Orchestrator</text>

  <!-- Compliance Gate -->
  <rect x="430" y="10" width="160" height="50" rx="12" fill="{comp_color}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>
  <text x="510" y="42" text-anchor="middle" fill="white" font-size="16" font-weight="700">{COMPLIANCE_MANIFEST.emoji} Compliance</text>

  <!-- Edges: Central to sub-agents -->
  <line x1="200" y1="60" x2="105" y2="220" stroke="#888" stroke-width="2"/>
  <line x1="260" y1="60" x2="305" y2="220" stroke="#888" stroke-width="2"/>
  <line x1="340" y1="60" x2="505" y2="220" stroke="#888" stroke-width="2"/>

  <!-- Arrows at the end of edges -->
  <polygon points="105,220 98,208 112,208" fill="#888"/>
  <polygon points="305,220 298,208 312,208" fill="#888"/>
  <polygon points="505,220 498,208 512,208" fill="#888"/>

  <!-- Gate dots (midpoint of each edge) -->
  <circle cx="150" cy="140" r="7" fill="{sg}"/>
  <circle cx="283" cy="140" r="7" fill="{bg}"/>
  <circle cx="423" cy="140" r="7" fill="{mg}"/>

  <!-- Compliance dashed lines to gate dots -->
  <line x1="510" y1="60" x2="150" y2="140" stroke="{comp_color}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.5"/>
  <line x1="510" y1="60" x2="283" y2="140" stroke="{comp_color}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.5"/>
  <line x1="510" y1="60" x2="423" y2="140" stroke="{comp_color}" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.5"/>

  <!-- Stock Broker Agent -->
  <g opacity="{s_op}">
    <rect x="10" y="225" width="190" height="50" rx="12" fill="{s_bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>
    <text x="105" y="257" text-anchor="middle" fill="{s_fg}" font-size="15" font-weight="600">{STOCKS_MANIFEST.emoji} Stock Broker Agent</text>
  </g>

  <!-- Bond Agent -->
  <g opacity="{b_op}">
    <rect x="210" y="225" width="190" height="50" rx="12" fill="{b_bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>
    <text x="305" y="257" text-anchor="middle" fill="{b_fg}" font-size="15" font-weight="600">{BONDS_MANIFEST.emoji} Bond Agent</text>
  </g>

  <!-- Raw Materials Agent -->
  <g opacity="{m_op}">
    <rect x="410" y="225" width="190" height="50" rx="12" fill="{m_bg}" stroke="rgba(0,0,0,0.1)" stroke-width="2"/>
    <text x="505" y="257" text-anchor="middle" fill="{m_fg}" font-size="15" font-weight="600">{MATERIALS_MANIFEST.emoji} Raw Materials</text>
  </g>

</svg>
</body></html>"""

    components.html(html, height=300, scrolling=False)

    # Agent selection buttons below the graph
    st.caption("Click an agent to inspect its manifest:")
    cols = st.columns(5)
    all_agents = [CENTRAL_MANIFEST, STOCKS_MANIFEST, BONDS_MANIFEST, MATERIALS_MANIFEST, COMPLIANCE_MANIFEST]
    for i, m in enumerate(all_agents):
        with cols[i]:
            if st.button(f"{m.emoji}", key=f"select_{m.agent_id}", help=m.name):
                st.session_state["selected_agent"] = m.agent_id
