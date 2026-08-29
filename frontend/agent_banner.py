"""Manual Audit / Anomaly Shield banner."""

from __future__ import annotations

import streamlit as st

from api_client import clear_cache, post_json


def render_agent_banner(agent: dict | None) -> None:
    if not agent or agent.get("status") != "interrupted":
        return
    st.error(
        "**Anomaly Shield — Manual Audit required** before the AI pipeline continues.  \n"
        f"thread=`{agent.get('thread_id')}` · anomaly_score=`{agent.get('anomaly_score')}`"
    )
    audit_reason = st.text_input("Manual audit reason", key="agent_audit_reason")
    c_a, c_r = st.columns(2)
    with c_a:
        if st.button("Approve — continue pipeline", type="primary"):
            ok, body, _ = post_json(
                "/api/v1/agent/resume/",
                {
                    "thread_id": agent["thread_id"],
                    "decision": "approved",
                    "reason_text": audit_reason
                    or "Operator approved anomaly continue",
                },
            )
            if ok:
                st.session_state.agent_state = body
                clear_cache()
                st.rerun()
            else:
                st.error(body.get("detail") or body)
    with c_r:
        if st.button("Reject — halt AI pipeline"):
            ok, body, _ = post_json(
                "/api/v1/agent/resume/",
                {
                    "thread_id": agent["thread_id"],
                    "decision": "rejected",
                    "reason_text": audit_reason or "Operator rejected — hold",
                },
            )
            if ok:
                st.session_state.agent_state = body
                st.rerun()
            else:
                st.error(body.get("detail") or body)
