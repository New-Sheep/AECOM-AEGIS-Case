"""Approve an action (human-in-the-loop)."""

from __future__ import annotations

import streamlit as st

from api_client import clear_cache, post_json
from theme import display_name

EXEC_TOKEN = "AEGIS-EXEC-DEMO"

LEVEL_MAP = {
    "Reduce load (L1)": "load_shed",
    "Reroute power (L2)": "reroute",
    "Acknowledge attention check (L3)": "cross_check",
    "Shut down equipment (L4)": "deenergize",
}

_ACTION_PLAIN = {
    "load_shed": "Reduce load",
    "reroute": "Reroute power",
    "deenergize": "Shut down equipment",
}


def _render_approval_card(body: dict) -> None:
    action = _ACTION_PLAIN.get(
        str(body.get("action_level") or ""),
        str(body.get("action_level") or "-"),
    )
    site = display_name(body.get("asset_name"), body.get("asset_id") or "-")
    summary = body.get("human_summary") or body.get("outcome") or "Recorded."
    lb, la = body.get("load_before"), body.get("load_after")
    load_line = "-"
    if lb is not None and la is not None:
        load_line = f"{float(lb):.2f} -> {float(la):.2f}"
    override = "Yes" if body.get("human_override") else "No"
    rem = int(body.get("remaining_conflict_count") or 0)
    sites = body.get("remaining_conflict_sites") or []

    st.markdown(
        f"""
        <div class="aegis-card">
          <h4>What happened</h4>
          <div style="margin-bottom:0.55rem;line-height:1.45">{summary}</div>
          <div style="font-size:0.85rem;color:#9eb6d0;line-height:1.55">
            <div><b>Site:</b> {site}</div>
            <div><b>Action:</b> {action}</div>
            <div><b>Load:</b> {load_line}</div>
            <div><b>Override recorded:</b> {override}</div>
            <div><b>Record #:</b> {body.get("audit_id", "-")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if rem > 0:
        names = ", ".join(display_name(s) for s in sites[:3]) if sites else "flagged sites"
        extra = f" and {rem - 3} more" if rem > 3 else ""
        verb = "needs" if rem == 1 else "need"
        st.warning(
            f"{rem} site{'s' if rem != 1 else ''} still {verb} a decision "
            f"({names}{extra})."
        )
    elif body.get("conflict_cleared"):
        st.success("No sites need attention on the map.")


def render_hitl_panel(*, selected: dict, brief: dict | None, agent: dict | None) -> None:
    st.markdown("### Approve an action")
    structured = (brief or {}).get("structured") or {}
    agent_plan = None
    if agent and agent.get("status") == "completed":
        agent_plan = agent

    cost = float(selected.get("replacement_cost") or 0)
    site = display_name(selected.get("name"), selected.get("id", ""))
    downs = (
        structured.get("downstream_ids")
        or (agent_plan or {}).get("impact_nodes")
        or selected.get("downstream_ids")
        or []
    )
    st.markdown(
        f"""
        <div class="aegis-card">
          <h4>What you are deciding</h4>
          <div>
            About <b>${cost:,.0f}</b> to replace <b>{site}</b> vs interrupting power to
            connected sites{(' (' + ', '.join(downs[:4]) + ')') if downs else ''}.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    level_label = st.radio("Choose an action", list(LEVEL_MAP.keys()), index=0)
    action = LEVEL_MAP[level_label]

    if action == "cross_check":
        st.write(
            "This step only confirms you reviewed the attention warning "
            f"(active={bool(selected.get('conflict_flag'))}). "
            "It does not send a field command. Pick Reduce load, Reroute, or Shut down to act."
        )
        if st.button("Acknowledge attention check"):
            st.success("Check acknowledged. Choose an action above when ready.")
    else:
        reason = st.text_area("Reason (required)", height=80, key="reason_box")
        override = st.checkbox(
            "I disagree with the suggested action (record override)",
            value=False,
        )
        if action == "deenergize":
            token = st.text_input(
                "Executive authorization token",
                value=EXEC_TOKEN,
                help="Demo token for shutdown: AEGIS-EXEC-DEMO",
            )
        else:
            token = "AEGIS-OPS"
        confirm = st.checkbox("I confirm this decision", value=False)

        if st.button("Submit action", type="primary"):
            if not reason.strip():
                st.error("Please enter a reason.")
            elif not confirm:
                st.error("Please confirm the decision first.")
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
                    st.session_state.brief_cache = {}
                    clear_cache()
                    st.success(body.get("human_summary") or "Action recorded.")
                    st.rerun()
                else:
                    st.error(body.get("detail") or body)

    if st.session_state.get("last_audit"):
        with st.expander("Last approval record", expanded=True):
            _render_approval_card(st.session_state.last_audit)
