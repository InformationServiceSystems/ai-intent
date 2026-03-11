"""MCP log stream component for displaying inter-agent messages."""

import json

import streamlit as st

from mcp.logger import get_logger


_DIRECTION_COLORS = {
    "outbound": "\U0001f535",   # blue
    "inbound": "\U0001f7e2",    # green
    "internal": "\U0001f7e0",   # amber
}

_STATUS_COLORS = {
    "error": "\U0001f534",           # red
    "constraint_violation": "\U0001f7e0",  # orange
}


def render_mcp_stream(session_id: str) -> None:
    """Render the MCP message log for a given session as styled cards."""
    logger = get_logger()
    messages = logger.get_session(session_id)

    if not messages:
        st.caption("No messages yet for this session.")
        return

    st.caption(f"{len(messages)} messages")

    for msg in messages:
        # Pick icon based on status first, then direction
        icon = _STATUS_COLORS.get(msg.response_status, _DIRECTION_COLORS.get(msg.direction, "\u26aa"))

        header = f"{icon} **{msg.method}** | {msg.from_agent} \u2192 {msg.to_agent} | `{msg.response_status}`"
        ts = msg.timestamp.strftime("%H:%M:%S.%f")[:-3]

        with st.container(border=True):
            st.markdown(f"{header}")
            st.caption(ts)

            if msg.constraint_flags:
                st.markdown(f":red[Flags: {', '.join(msg.constraint_flags)}]")

            with st.expander("Payload"):
                st.json(msg.payload)
