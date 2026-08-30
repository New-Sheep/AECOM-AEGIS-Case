"""Ask AEGIS — bottom-right floating dock (answer-first, confirm-optional)."""

from __future__ import annotations

import uuid

import streamlit as st

from api_client import clear_cache, post_json
from theme import display_name

EXEC_TOKEN = "AEGIS-EXEC-DEMO"

_TOOL_CHIPS = [
    ("Explain warning", "Explain this warning"),
    ("Who is affected?", "Who is affected?"),
    ("Who loses power?", "Who loses power if this site goes down?"),
    ("How is money calculated?", "How is money calculated?"),
    ("Region outlook", "Region outlook"),
    ("Sites needing attention", "Which sites need attention?"),
    ("Site priority list", "Site priority list: red and orange sites from most critical to least"),
    ("What should I do?", "What should I do?"),
]

_ACTION_LEVEL = {
    "reduce_load": "load_shed",
    "shutdown": "deenergize",
    "reroute": "reroute",
    "restore_load": "restore_load",
    "reenergize": "reenergize",
}


def _conversation_id() -> str:
    key = "ask_conversation_id"
    if key not in st.session_state:
        st.session_state[key] = str(uuid.uuid4())
    return str(st.session_state[key])


def _send_chat(asset_id: str, message: str, *, live_ai: bool) -> None:
    hist_key = f"ask_history_{asset_id}"
    history = st.session_state.setdefault(hist_key, [])
    mode = "live" if live_ai else "fake"
    ok, body, _ = post_json(
        "/api/v1/assistant/chat/",
        {
            "asset_id": asset_id,
            "message": message,
            "mode": mode,
            "history": history[-6:],
            "conversation_id": _conversation_id(),
        },
    )
    if not ok:
        st.session_state["ask_error"] = body.get("detail") or str(body)
        return
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": body.get("reply") or ""})
    st.session_state[hist_key] = history[-24:]
    st.session_state["ask_pending_tool"] = {
        "asset_id": asset_id,
        "pending_actions": body.get("pending_actions") or [],
        "tool_calls": body.get("tool_calls") or [],
        "tool_results": body.get("tool_results") or {},
    }
    st.session_state.pop("ask_error", None)


def _jump_to_site(target_id: str) -> None:
    tid = (target_id or "").strip()
    if not tid:
        return
    st.session_state.selected_id = tid
    st.session_state.pop("_synced_site_id", None)
    st.session_state.pop("site_pick_main", None)
    st.rerun()


def _truncate_label(name: str, limit: int = 28) -> str:
    n = (name or "").strip()
    if len(n) <= limit:
        return n
    return n[: limit - 1] + "…"


def _render_priority_jump_buttons() -> None:
    """Open buttons for sites returned by list_priority_sites."""
    pending = st.session_state.get("ask_pending_tool") or {}
    results = pending.get("tool_results") or {}
    payload = results.get("list_priority_sites") or {}
    sites = payload.get("sites") or []
    if not sites:
        return

    groups: dict[str, list[dict]] = {
        "High": [],
        "Needs attention": [],
        "Watch": [],
    }
    for s in sites:
        if not isinstance(s, dict):
            continue
        band = str(s.get("band") or "")
        if band in groups:
            groups[band].append(s)

    caps = {"High": 5, "Needs attention": 5, "Watch": 3}
    titles = {
        "High": "Open high risk",
        "Needs attention": "Open decision needed",
        "Watch": "Open watch",
    }

    any_shown = False
    for band in ("High", "Needs attention", "Watch"):
        rows = groups[band][: caps[band]]
        if not rows:
            continue
        if not any_shown:
            st.markdown("**Open a listed site**")
            any_shown = True
        st.caption(titles[band])
        cols = st.columns(2)
        for i, s in enumerate(rows):
            aid = str(s.get("asset_id") or "")
            label = _truncate_label(str(s.get("name") or aid))
            with cols[i % 2]:
                if st.button(
                    label,
                    key=f"ask_jump_{band}_{aid}_{i}",
                    width="stretch",
                    help=f"Select {s.get('name') or aid} on the map",
                ):
                    _jump_to_site(aid)


def _confirm_action(asset_id: str, pending: dict) -> None:
    name = str(pending.get("name") or "")
    action = _ACTION_LEVEL.get(name) or pending.get("action_level")
    if not action:
        st.error("Unknown action.")
        return
    token = (
        EXEC_TOKEN
        if action in {"deenergize", "reenergize"}
        else "AEGIS-OPS"
    )
    label = pending.get("label") or name
    ok, body, _ = post_json(
        "/api/v1/control/shutdown/",
        {
            "asset_id": asset_id,
            "action_level": action,
            "authorization_token": token,
            "reason_text": f"Ask AEGIS confirmed: {label}",
            "user_id": "demo-ic",
            "human_override": False,
        },
    )
    if ok:
        st.session_state.last_audit = body
        st.session_state.brief_cache = {}
        st.session_state["ask_pending_tool"] = None
        clear_cache()
        hist_key = f"ask_history_{asset_id}"
        history = st.session_state.setdefault(hist_key, [])
        history.append(
            {
                "role": "assistant",
                "content": body.get("human_summary") or f"Done: {label}.",
            }
        )
        st.session_state[hist_key] = history
        st.success(body.get("human_summary") or "Action recorded.")
        st.rerun()
    else:
        st.error(body.get("detail") or body)


def _latest_turns(asset_id: str) -> tuple[str | None, str | None]:
    history = st.session_state.get(f"ask_history_{asset_id}") or []
    user_q = None
    reply = None
    for turn in reversed(history):
        role = turn.get("role")
        if role == "assistant" and reply is None:
            reply = str(turn.get("content") or "")
        elif role == "user" and user_q is None and reply is not None:
            user_q = str(turn.get("content") or "")
            break
    return user_q, reply


def _render_recent_history(asset_id: str) -> None:
    history = st.session_state.get(f"ask_history_{asset_id}") or []
    if len(history) <= 2:
        return
    with st.expander("Earlier messages", expanded=False):
        older = history[:-2] if len(history) >= 2 else history
        pairs: list[tuple[dict, dict | None]] = []
        i = 0
        while i < len(older):
            turn = older[i]
            if (
                turn.get("role") == "user"
                and i + 1 < len(older)
                and older[i + 1].get("role") == "assistant"
            ):
                pairs.append((turn, older[i + 1]))
                i += 2
            else:
                pairs.append((turn, None))
                i += 1
        for user_turn, asst_turn in pairs[-3:]:
            st.markdown(f"**You:** {user_turn.get('content') or ''}")
            if asst_turn:
                st.markdown(f"**AEGIS:** {asst_turn.get('content') or ''}")


def _drawer_body(*, asset_id: str, site: str, live_ai: bool) -> None:
    st.caption(f"Site: **{site}**")
    st.caption("Answers first. Commands need an explicit confirm — never auto-trips.")

    user_q, reply = _latest_turns(asset_id)
    if reply:
        st.markdown('<div class="aegis-ask-answer">', unsafe_allow_html=True)
        if user_q:
            st.caption(f"You asked: {user_q}")
        st.markdown(reply)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("Ask a quick prompt or type a question below.")

    _render_priority_jump_buttons()

    _render_recent_history(asset_id)

    pending_wrap = st.session_state.get("ask_pending_tool") or {}
    if pending_wrap.get("asset_id") == asset_id:
        tools = pending_wrap.get("tool_calls") or []
        if tools:
            chips = ", ".join(
                str(t.get("name") or t) for t in tools if isinstance(t, dict)
            )
            if chips:
                st.caption(f"Tools used: {chips}")
        actions = pending_wrap.get("pending_actions") or []
        if actions:
            st.markdown("**Optional next step**")
            st.caption(
                "Choose one action to confirm, or dismiss. Nothing runs until you confirm."
            )
            labels = [
                str(a.get("label") or a.get("name") or f"Action {i}")
                for i, a in enumerate(actions)
            ]
            choice = st.radio(
                "Action",
                options=labels,
                index=0,
                key=f"ask_action_radio_{asset_id}",
                label_visibility="collapsed",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "Confirm selected",
                    key=f"ask_confirm_one_{asset_id}",
                    type="primary",
                    width="stretch",
                ):
                    idx = labels.index(choice) if choice in labels else 0
                    _confirm_action(asset_id, actions[idx])
            with c2:
                if st.button(
                    "Dismiss",
                    key=f"ask_dismiss_{asset_id}",
                    width="stretch",
                ):
                    st.session_state["ask_pending_tool"] = None
                    st.rerun()

    st.markdown("**Quick prompts**")
    cols = st.columns(2)
    for i, (label, prompt) in enumerate(_TOOL_CHIPS):
        with cols[i % 2]:
            if st.button(
                label,
                key=f"ask_tool_{asset_id}_{i}",
                width="stretch",
            ):
                _send_chat(asset_id, prompt, live_ai=live_ai)
                st.rerun()

    msg_key = f"ask_msg_{asset_id}"
    clear_flag = f"ask_clear_msg_{asset_id}"
    if st.session_state.pop(clear_flag, False):
        st.session_state.pop(msg_key, None)

    typed = st.text_input(
        "Message",
        key=msg_key,
        placeholder="Ask about this site...",
        label_visibility="collapsed",
    )
    if st.button("Send", key=f"ask_send_{asset_id}", width="stretch"):
        msg = (typed or st.session_state.get(msg_key) or "").strip()
        if msg:
            _send_chat(asset_id, msg, live_ai=live_ai)
            st.session_state[clear_flag] = True
            st.rerun()

    if st.session_state.get("ask_error"):
        st.error(st.session_state["ask_error"])


def render_ask_widget(
    *,
    selected: dict,
    live_ai: bool = False,
    name_by_id: dict[str, str] | None = None,
) -> None:
    """Bottom-right floating Ask AEGIS dock on the main page (not sidebar)."""
    _ = name_by_id
    asset_id = selected.get("id") or ""
    site = display_name(selected.get("name"), asset_id)

    if "ask_open" not in st.session_state:
        st.session_state["ask_open"] = False

    with st.container():
        collapsed = not st.session_state.get("ask_open", False)
        marker_cls = (
            "aegis-ask-float-root aegis-ask-collapsed"
            if collapsed
            else "aegis-ask-float-root"
        )
        st.markdown(
            f'<div class="{marker_cls}" id="aegis-ask-float-root"></div>',
            unsafe_allow_html=True,
        )
        if collapsed:
            st.markdown(
                """
                <div class="aegis-ask-pill-label">
                  <div class="aegis-ask-title">Ask AEGIS</div>
                  <div class="aegis-ask-sub">Crisis Q&amp;A · tap to open</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Open Ask AEGIS",
                key="ask_open_btn",
                type="primary",
                width="stretch",
                help="Ask grounded questions about this site, the region, or money at risk.",
            ):
                st.session_state["ask_open"] = True
                st.rerun()
            return

        hdr_l, hdr_r = st.columns([5, 1])
        with hdr_l:
            st.markdown(
                """
                <div class="aegis-ask-shell">
                  <div class="aegis-ask-title">Ask AEGIS</div>
                  <div class="aegis-ask-sub">Crisis Q&amp;A · grounded tools · confirm before any command</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with hdr_r:
            if st.button(
                "−",
                key=f"ask_minimize_{asset_id}",
                help="Minimize Ask AEGIS",
            ):
                st.session_state["ask_open"] = False
                st.rerun()

        _drawer_body(asset_id=asset_id, site=site, live_ai=live_ai)


def render_assistant_panel(*, selected: dict, live_ai: bool = False) -> None:
    render_ask_widget(selected=selected, live_ai=live_ai)
