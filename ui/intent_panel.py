"""Agent intent manifest display component."""

import streamlit as st
import pandas as pd

from agents.manifests import AgentManifest, get_manifest


def render_intent_panel(agent_id: str) -> None:
    """Render the selected agent's AgentManifest in a styled container."""
    try:
        manifest = get_manifest(agent_id)
    except KeyError:
        st.warning(f"Unknown agent: {agent_id}")
        return

    with st.container(border=True):
        st.subheader(f"{manifest.emoji} {manifest.name}")
        st.caption(manifest.role)

        st.markdown(f"**Intent Scope:** {manifest.intent_scope}")

        st.markdown("**Boundary Constraints:**")
        for c in manifest.boundary_constraints:
            st.markdown(f"- {c}")

        st.markdown("**Risk Parameters:**")
        params_df = pd.DataFrame(
            [{"Parameter": k, "Value": str(v)} for k, v in manifest.risk_parameters.items()]
        )
        st.dataframe(params_df, use_container_width=True, hide_index=True)

        st.info(manifest.plain_language_summary)
