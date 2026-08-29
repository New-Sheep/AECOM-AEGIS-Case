"""HITL Action Center panel."""

from __future__ import annotations

import streamlit as st

from api_client import clear_cache, post_json

EXEC_TOKEN = "AEGIS-EXEC-DEMO"

LEVEL_MAP = {
    "L1 — Load shed (~20%, suggest-only)": "load_shed",
    "L2 — Reroute (expert review)": "reroute",
    "L3 — Cross-check gate (Old Guard ∩ XGB)": "cross_check",
    "L4 — De-energize (executive auth)": "deenergize",
}


def render_hitl_panel(*, selected: dict, brief: dict | None, agent: dict | None) -> None:
    st.markdown("### HITL Action Center")
    structured = (brief or {}).get("structured") or {}
    agent_plan = None
    if agent and agent.get("status") == "completed":
        agent_plan = agent

    cost = float(selected.get("replacement_cost") or 0)
    downs = (
        structured.get("downstream_ids")
        or (agent_plan or {}).get("impact_nodes")
        or selected.get("downstream_ids")
        or []
    )
    trade = structured.get("trade_off") or (
        f"Protecting CapEx ~${cost:,.0f} vs lifeline outage of "
        f"{', '.join(downs) if downs else 'none'}."
    )
    st.markdown(
        f"""
        <div class="aegis-card">
          <h4>Trade-off</h4>
          <div>{trade}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    level_label = st.radio("Graduated response", list(LEVEL_MAP.keys()), index=0)
    action = LEVEL_MAP[level_label]

    if action == "cross_check":
        st.write(
            "**L3 Cross-check (gate only):** ValidationService already computed "
            f"`conflict_flag={selected.get('conflict_flag')}`. "
            "No OT POST — acknowledge and choose L1/L2/L4 to act."
        )
        if st.button("Acknowledge L3 gate"):
            st.success("L3 reviewed — proceed to L1/L2/L4 with reason.")
    else:
        reason = st.text_area("Reason (mandatory)", height=80, key="reason_box")
        override = st.checkbox(
            "Human override / retrain flag (disagree with AI suggestion)",
            value=False,
        )
        token = st.text_input(
            "Authorization token",
            value=EXEC_TOKEN if action == "deenergize" else "AEGIS-OPS",
        )
        confirm = st.checkbox("I confirm this trade-off decision", value=False)

        if st.button("Submit HITL action", type="primary"):
            if not reason.strip():
                st.error("Reason is required.")
            elif not confirm:
                st.error("Confirm the trade-off checkbox first.")
            else:
                ok, body, _ = post_json(
                    "/api/v1/control/shutdown/",
                    {
                        "asset_id": selected["id"],
                        "action_level": action,
                        "authorization_token": token,
                        "reason_text": reason.strip(),
                        "user_id": "demo-ic",
                        "human_override": override,
                    },
                )
                if ok:
                    st.session_state.last_audit = body
                    st.success(
                        f"Audit #{body.get('audit_id')} · {body.get('outcome')}"
                    )
                    clear_cache()
                else:
                    st.error(body.get("detail") or body)

    if st.session_state.get("last_audit"):
        st.markdown("**Last audit ack**")
        st.json(st.session_state.last_audit)
