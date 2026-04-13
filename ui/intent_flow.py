"""Sequence diagram component for visualizing MCP message flow using D3.js."""

import json

import streamlit as st
import streamlit.components.v1 as components

from mcp.logger import MCPMessage, get_logger


_DIRECTION_COLORS = {
    "outbound": "#2196F3",
    "inbound": "#4CAF50",
    "internal": "#FF9800",
}

_STATUS_OVERRIDE = {
    "error": "#F44336",
    "constraint_violation": "#FF5722",
    "forced_pass": "#9C27B0",
    "forced_block": "#9C27B0",
}

_ACTOR_ORDER = ["user", "central", "compliance", "stocks", "bonds", "materials"]
_ACTOR_LABELS = {
    "user": "User",
    "central": "Orchestrator",
    "compliance": "Compliance",
    "stocks": "Stocks",
    "bonds": "Bonds",
    "materials": "Materials",
}
_ACTOR_COLORS = {
    "user": "#78909C",
    "central": "#FF6B6B",
    "compliance": "#9C27B0",
    "stocks": "#4ECDC4",
    "bonds": "#45B7D1",
    "materials": "#F9A825",
}


def _messages_to_json(messages: list[MCPMessage]) -> str:
    """Convert MCP messages to a JSON array for D3."""
    # Filter out redundant compliance bookkeeping messages.
    # Keep only actionable messages — the check verdicts and semantic calls
    # are internal bookkeeping visible in the Constraint View tab.
    _HIDDEN_PREFIXES = (
        "compliance.semantic.",     # internal LLM call for semantic check
        "compliance.parse_retry.",  # internal parse retry
        "compliance.approve.",      # approval verdicts (shown in Compliance Log tab)
        "compliance.reject.",       # rejection verdicts (shown in Compliance Log tab)
        "disposition.active",       # disposition config log
    )
    filtered = [
        msg for msg in messages
        if not any(msg.method.startswith(p) for p in _HIDDEN_PREFIXES)
    ]

    actors_seen = set()
    for msg in filtered:
        actors_seen.add(msg.from_agent)
        actors_seen.add(msg.to_agent)
    actors = [a for a in _ACTOR_ORDER if a in actors_seen]

    actor_data = [
        {"id": a, "label": _ACTOR_LABELS.get(a, a), "color": _ACTOR_COLORS.get(a, "#999")}
        for a in actors
    ]

    msg_data = []
    for msg in filtered:
        color = _STATUS_OVERRIDE.get(msg.response_status, _DIRECTION_COLORS.get(msg.direction, "#999"))
        status_marker = ""
        if msg.response_status == "constraint_violation":
            if msg.payload.get("out_of_scope"):
                status_marker = " [DECLINED]"
                color = "#78909C"
            else:
                status_marker = " [VIOLATION]"
        elif msg.response_status == "error":
            status_marker = " [ERROR]"
        elif msg.response_status in ("forced_pass", "forced_block"):
            status_marker = " [BLOCKED]"
        elif msg.response_status == "blocked":
            status_marker = " [BLOCKED]"

        msg_data.append({
            "from": msg.from_agent,
            "to": msg.to_agent,
            "method": msg.method,
            "time": msg.timestamp.strftime("%H:%M:%S"),
            "direction": msg.direction,
            "status": msg.response_status,
            "color": color,
            "marker": status_marker,
            "flags": msg.constraint_flags,
        })

    return json.dumps({"actors": actor_data, "messages": msg_data})


_D3_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: white; overflow: hidden; }
  #container { width: 100%; height: HEIGHT_PLACEHOLDERpx; position: relative; }
  svg { width: 100%; height: 100%; }
  .actor-header { cursor: default; }
  .actor-label { font-size: 13px; font-weight: 700; fill: white; text-anchor: middle; dominant-baseline: central; }
  .lifeline { stroke-dasharray: 6, 4; stroke-width: 1.5; opacity: 0.3; }
  .msg-arrow { stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
  .msg-self { stroke-width: 2; fill: none; stroke-dasharray: 5, 3; }
  .msg-label { font-size: 11px; font-weight: 500; }
  .msg-time { font-size: 9px; fill: #999; }
  .msg-row:hover .msg-highlight { opacity: 0.06; }
  .msg-highlight { opacity: 0; transition: opacity 0.15s; }
  .tooltip {
    position: absolute; background: #333; color: white; padding: 6px 10px;
    border-radius: 6px; font-size: 12px; pointer-events: none; opacity: 0;
    transition: opacity 0.15s; z-index: 100; max-width: 300px;
  }
  #controls {
    position: absolute; top: 8px; right: 8px; display: flex; flex-direction: column;
    gap: 4px; z-index: 10;
  }
  #controls button {
    width: 32px; height: 32px; border: 1px solid #ddd; border-radius: 6px;
    background: white; font-size: 16px; cursor: pointer; display: flex;
    align-items: center; justify-content: center;
  }
  #controls button:hover { background: #f5f5f5; }
  #zoom-label { font-size: 10px; text-align: center; color: #888; }
</style>
</head>
<body>
<div id="container">
  <div id="controls">
    <button onclick="zoomIn()">+</button>
    <button onclick="zoomOut()">&minus;</button>
    <button onclick="resetView()">&#8634;</button>
    <div id="zoom-label">100%</div>
  </div>
  <div class="tooltip" id="tooltip"></div>
</div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = DATA_PLACEHOLDER;
const actors = data.actors;
const messages = data.messages;
const height = HEIGHT_PLACEHOLDER;

const colW = Math.max(130, 800 / actors.length);
const headerH = 50;
const rowH = 38;
const marginL = 30;
const totalW = marginL + actors.length * colW + 30;
const totalH = headerH + messages.length * rowH + 60;

const actorX = {};
actors.forEach((a, i) => { actorX[a.id] = marginL + i * colW + colW / 2; });

const svg = d3.select("#container").append("svg")
  .attr("viewBox", `0 0 ${totalW} ${totalH}`)
  .attr("preserveAspectRatio", "xMidYMin meet");

const g = svg.append("g");

// Defs: arrowhead
svg.append("defs").append("marker")
  .attr("id", "arrowhead").attr("viewBox", "0 0 10 10")
  .attr("refX", 9).attr("refY", 5)
  .attr("markerWidth", 7).attr("markerHeight", 7)
  .attr("orient", "auto")
  .append("path").attr("d", "M 0 0 L 10 5 L 0 10 z").attr("fill", "#666");

// Lifelines
actors.forEach(a => {
  g.append("line").attr("class", "lifeline")
    .attr("x1", actorX[a.id]).attr("y1", headerH + 10)
    .attr("x2", actorX[a.id]).attr("y2", totalH)
    .attr("stroke", a.color);
});

// Actor headers
actors.forEach(a => {
  const x = actorX[a.id];
  g.append("rect").attr("class", "actor-header")
    .attr("x", x - 55).attr("y", 8).attr("width", 110).attr("height", 34)
    .attr("rx", 8).attr("fill", a.color);
  g.append("text").attr("class", "actor-label")
    .attr("x", x).attr("y", 25).text(a.label);
});

// Tooltip
const tooltip = document.getElementById("tooltip");

// Messages
messages.forEach((msg, i) => {
  const y = headerH + 20 + i * rowH;
  const fromX = actorX[msg.from] || 0;
  const toX = actorX[msg.to] || 0;
  const color = msg.color;
  const isViolation = msg.status === "constraint_violation" || msg.status === "error";

  const row = g.append("g").attr("class", "msg-row")
    .style("cursor", "default");

  // Hover highlight
  row.append("rect").attr("class", "msg-highlight")
    .attr("x", 0).attr("y", y - rowH / 2 + 2)
    .attr("width", totalW).attr("height", rowH)
    .attr("fill", color);

  if (msg.from === msg.to) {
    // Self-message: loop arrow
    const loopW = 40;
    row.append("path").attr("class", "msg-self")
      .attr("d", `M ${fromX} ${y} C ${fromX + loopW} ${y}, ${fromX + loopW} ${y + 18}, ${fromX} ${y + 18}`)
      .attr("stroke", color);
    row.append("text").attr("class", "msg-label")
      .attr("x", fromX + loopW + 4).attr("y", y + 6)
      .attr("fill", color).text(msg.method + msg.marker);
    row.append("text").attr("class", "msg-time")
      .attr("x", fromX + loopW + 4).attr("y", y + 18).text(msg.time);
  } else {
    // Arrow between actors
    const dir = toX > fromX ? 1 : -1;
    const pad = 8;
    row.append("line").attr("class", "msg-arrow")
      .attr("x1", fromX + dir * pad).attr("y1", y)
      .attr("x2", toX - dir * pad).attr("y2", y)
      .attr("stroke", color);
    // Arrowhead triangle
    row.append("polygon")
      .attr("points", `${toX - dir * pad},${y} ${toX - dir * (pad + 8)},${y - 4} ${toX - dir * (pad + 8)},${y + 4}`)
      .attr("fill", color);
    // Label above arrow
    const midX = (fromX + toX) / 2;
    row.append("text").attr("class", "msg-label")
      .attr("x", midX).attr("y", y - 6)
      .attr("text-anchor", "middle").attr("fill", color)
      .text(msg.method + msg.marker);
    row.append("text").attr("class", "msg-time")
      .attr("x", midX).attr("y", y + 14)
      .attr("text-anchor", "middle").text(msg.time);
  }

  // Violation dot
  if (isViolation) {
    row.append("circle")
      .attr("cx", Math.min(fromX, toX || fromX) - 14).attr("cy", y)
      .attr("r", 5).attr("fill", color);
  }

  // Tooltip on hover
  row.on("mouseover", (event) => {
    let html = `<b>${msg.method}</b><br>${msg.from} → ${msg.to}<br>${msg.time}`;
    if (msg.marker) html += `<br><span style="color:#FF5722">${msg.marker}</span>`;
    if (msg.flags && msg.flags.length) html += `<br>Flags: ${msg.flags.join(", ")}`;
    tooltip.innerHTML = html;
    tooltip.style.opacity = 1;
    tooltip.style.left = event.pageX + 10 + "px";
    tooltip.style.top = event.pageY - 30 + "px";
  });
  row.on("mousemove", (event) => {
    tooltip.style.left = event.pageX + 10 + "px";
    tooltip.style.top = event.pageY - 30 + "px";
  });
  row.on("mouseout", () => { tooltip.style.opacity = 0; });
});

// Zoom/pan
let currentTransform = d3.zoomIdentity;
const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on("zoom", (event) => {
    currentTransform = event.transform;
    g.attr("transform", event.transform);
    document.getElementById("zoom-label").textContent = Math.round(event.transform.k * 100) + "%";
  });
svg.call(zoom);

function zoomIn() { svg.transition().duration(200).call(zoom.scaleBy, 1.3); }
function zoomOut() { svg.transition().duration(200).call(zoom.scaleBy, 0.77); }
function resetView() {
  const c = document.getElementById("container");
  const cW = c ? c.clientWidth : totalW;
  const cH = c ? c.clientHeight : height;
  if (!cW || !cH || !totalW || !totalH) return;
  const s = Math.min(cW / totalW, cH / totalH, 1.2);
  if (!isFinite(s) || s <= 0) return;
  svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity.scale(s));
}
setTimeout(resetView, 200);
</script>
</body>
</html>"""


def _render_d3_sequence(messages: list[MCPMessage], height: int = 700) -> None:
    """Render an interactive D3 sequence diagram."""
    data_json = _messages_to_json(messages)
    html = _D3_HTML.replace("DATA_PLACEHOLDER", data_json).replace("HEIGHT_PLACEHOLDER", str(height))
    components.html(html, height=height + 20, scrolling=False)


def _build_popup_html(messages: list[MCPMessage]) -> str:
    """Build a standalone HTML page for the popup window."""
    data_json = _messages_to_json(messages)
    html = _D3_HTML.replace("DATA_PLACEHOLDER", data_json).replace("HEIGHT_PLACEHOLDER", "760")
    # Override container to fill viewport
    html = html.replace(
        '#container { width: 100%; height: 760px;',
        '#container { width: 100%; height: calc(100vh - 20px);',
    )
    # Add title and resize handler
    html = html.replace('<head>', f'''<head>
<title>Intent Flow &#8212; {len(messages)} messages</title>''')
    html = html.replace('setTimeout(resetView, 200);', '''setTimeout(resetView, 300);
window.addEventListener("resize", () => {
  resetView();
});''')
    return html


def render_intent_flow(session_id: str) -> None:
    """Render a sequence diagram of all MCP messages for a session."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    if not messages:
        st.caption("No messages to display.")
        return

    st.caption(f"Message flow: {len(messages)} messages")

    # Inline version
    _render_d3_sequence(messages, height=350)

    # "Open in popup" button — uses JS window.open with the full HTML as a data URI
    popup_html = _build_popup_html(messages)
    # Encode as base64 data URI to avoid URL length limits
    import base64
    b64 = base64.b64encode(popup_html.encode("utf-8")).decode("ascii")

    popup_js = f"""
    <button onclick="
        var w = window.open('', 'intent_flow', 'width=1200,height=800,resizable=yes,scrollbars=yes');
        if (w) {{
            w.document.open();
            w.document.write(atob('{b64}'));
            w.document.close();
            w.focus();
        }}
    " style="
        padding: 8px 16px; border: 1px solid #ddd; border-radius: 8px;
        background: white; cursor: pointer; font-size: 13px;
        font-family: -apple-system, sans-serif; display: flex;
        align-items: center; gap: 6px;
    ">
        <span style="font-size:16px;">&#x26F6;</span> Open in Resizable Window
    </button>
    """
    components.html(popup_js, height=50)

    # Clickable message detail list below
    st.divider()
    st.markdown("**Message Details:**")
    for i, msg in enumerate(messages):
        icon = {"outbound": "->", "inbound": "<-", "internal": "**"}
        direction_icon = icon.get(msg.direction, "--")
        status_color = "red" if msg.response_status in ("error", "constraint_violation") else "green" if msg.response_status == "ok" else "gray"

        with st.expander(f"{i+1}. {msg.method} ({msg.from_agent} {direction_icon} {msg.to_agent}) — :{status_color}[{msg.response_status}]"):
            st.markdown(f"**Direction:** {msg.direction}")
            st.markdown(f"**Time:** {msg.timestamp.strftime('%H:%M:%S.%f')[:-3]}")
            if msg.constraint_flags:
                st.markdown(f":red[**Constraint Flags:** {', '.join(msg.constraint_flags)}]")
            st.json(msg.payload)
