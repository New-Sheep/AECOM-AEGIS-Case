"""Manual approval banner when a status check pauses for unusual readings."""

from __future__ import annotations

import streamlit as st

from api_client import clear_cache, post_json


def render_agent_banner(agent: dict | None) -> None:
    if not agent or agent.get("status") != "interrupted":
        return
    st.error(
        "**Unusual sensor readings. Your approval is required** before the check continues."
    )
    audit_reason = st.text_input("Your note (optional)", key="agent_audit_reason")
    c_a, c_r = st.columns(2)
    with c_a:
        if st.button("Approve and continue", type="primary"):
            ok, body, _ = post_json(
                "/api/v1/agent/resume/",
                {
                    "thread_id": agent["thread_id"],
                    "decision": "approved",
                    "reason_text": audit_reason
                    or "Operator approved continue after unusual readings",
                },
            )
            if ok:
                st.session_state.agent_state = body
                clear_cache()
                st.rerun()
            else:
                st.error(body.get("detail") or body)
    with c_r:
        if st.button("Reject and hold"):
            ok, body, _ = post_json(
                "/api/v1/agent/resume/",
                {
                    "thread_id": agent["thread_id"],
                    "decision": "rejected",
                    "reason_text": audit_reason or "Operator held: do not continue",
                },
            )
            if ok:
                st.session_state.agent_state = body
                st.rerun()
            else:
                st.error(body.get("detail") or body)
