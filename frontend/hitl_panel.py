"""Approve an action (human-in-the-loop) — collapsed by default."""

from __future__ import annotations

import streamlit as st

from api_client import clear_cache, post_json
from theme import display_name

EXEC_TOKEN = "AEGIS-EXEC-DEMO"

_ACTION_PLAIN = {
    "load_shed": "Reduce load",
    "reroute": "Reroute power",
    "deenergize": "Shut down equipment",
    "restore_load": "Restore load",
    "reenergize": "Re-energize",
}


def _options_for_state(op: str) -> dict[str, str]:
    if op == "deenergized":
        return {"Re-energize": "reenergize"}
    if op == "load_reduced":
        return {
            "Restore load": "restore_load",
            "Shut down equipment": "deenergize",
            "Reroute power": "reroute",
        }
    return {
        "Reduce load": "load_shed",
        "Reroute power": "reroute",
        "Acknowledge attention check": "cross_check",
        "Shut down equipment": "deenergize",
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
    rem = int(body.get("remaining_conflict_count") or 0)
    sites = body.get("remaining_conflict_sites") or []
    op = body.get("operational_state") or "-"

    st.markdown(
        f"""
        <div class="aegis-card">
          <h4>What happened</h4>
          <div style="margin-bottom:0.55rem;line-height:1.45">{summary}</div>
          <div style="font-size:0.85rem;color:#9eb6d0;line-height:1.55">
            <div><b>Site:</b> {site}</div>
            <div><b>Action:</b> {action}</div>
            <div><b>Load:</b> {load_line}</div>
            <div><b>Control state:</b> {op}</div>
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
        st.success("No sites need a decision on the map.")


def render_hitl_panel(
    *,
    selected: dict,
    brief: dict | None,
    agent: dict | None,
    name_by_id: dict[str, str] | None = None,
) -> None:
    structured = (brief or {}).get("structured") or {}
    agent_plan = None
    if agent and agent.get("status") == "completed":
        agent_plan = agent

    cost = float(selected.get("replacement_cost") or 0)
    site = display_name(selected.get("name"), selected.get("id", ""))
    op = str(selected.get("operational_state") or "normal")
    downs = (
        structured.get("downstream_ids")
        or (agent_plan or {}).get("impact_nodes")
        or selected.get("downstream_ids")
        or []
    )
    near_names = []
    for did in downs[:3]:
        near_names.append(
            display_name((name_by_id or {}).get(did), str(did))
        )
    near = ", ".join(near_names) if near_names else "nearby dependent sites"

    with st.expander("Record a decision", expanded=False):
        st.caption(
            "Prefer the quick buttons under the map when you can. "
            "Use this form when you need a written reason on the record."
        )
        st.markdown(
            f"""
            <div class="aegis-card">
              <h4>What you are deciding</h4>
              <div>
                About <b>USD {cost:,.0f}</b> of equipment at <b>{site}</b>
                vs risk of power loss at <b>{near}</b>.
              </div>
              <div style="margin-top:0.4rem;color:#9eb6d0;font-size:0.85rem">
                Control state: <b>{op.replace('_', ' ')}</b>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        level_map = _options_for_state(op)
        level_label = st.radio("Choose an action", list(level_map.keys()), index=0)
        action = level_map[level_label]

        if action == "cross_check":
            st.write(
                "This only confirms you reviewed the attention warning. "
                "It does not send a field command. Pick Reduce load, Reroute, "
                "or Shut down to act."
            )
            if st.button("Acknowledge attention check"):
                st.success("Check acknowledged. Choose an action above when ready.")
        else:
            reason = st.text_area("Reason (required)", height=80, key="reason_box")
            confirm = st.checkbox("I confirm this decision", value=False)
            token = "AEGIS-OPS"
            override = False
            with st.expander("Authorization (demo)", expanded=False):
                override = st.checkbox(
                    "I disagree with the suggested action (record override)",
                    value=False,
                    help="Marks that a human chose a different action than suggested.",
                )
                if action in {"deenergize", "reenergize"}:
                    token = st.text_input(
                        "Authorization token",
                        value=EXEC_TOKEN,
                        help="Demo token is pre-filled. Real systems would use SSO.",
                    )
                else:
                    st.caption("Ops-level actions use the standard demo token.")

            if st.button(
                "Submit action",
                type="primary",
                help="Writes an audit record. Prefer map quick actions for demos.",
            ):
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
        _render_approval_card(st.session_state.last_audit)
