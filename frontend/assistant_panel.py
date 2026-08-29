"""Ask AEGIS: guided operator assistant (newest answers first)."""

from __future__ import annotations

import streamlit as st

from api_client import post_json
from theme import display_name

_STARTERS = [
    "Explain this warning",
    "What should I do?",
    "Why is flood water a problem?",
    "Why is wind high?",
]


def render_assistant_panel(*, selected: dict, live_ai: bool = False) -> None:
    asset_id = selected.get("id") or ""
    site = display_name(selected.get("name"), asset_id)
    hist_key = f"ask_history_{asset_id}"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    st.caption(
        f"Ask about {site}: why a reading looks high, what the warning means, "
        "or which action to take. Confirm any command under Site actions or Approve. "
        "This chat never trips breakers."
    )

    chips = st.columns(len(_STARTERS))
    chosen = None
    for i, label in enumerate(_STARTERS):
        if chips[i].button(label, key=f"ask_chip_{asset_id}_{i}"):
            chosen = label

    prompt = st.chat_input("Ask AEGIS about this site...")
    message = chosen or prompt

    if message:
        mode = "live" if live_ai else "fake"
        ok, body, _ = post_json(
            "/api/v1/assistant/chat/",
            {
                "asset_id": asset_id,
                "message": message,
                "mode": mode,
                "history": st.session_state[hist_key][-6:],
            },
        )
        if ok:
            st.session_state[hist_key].append({"role": "user", "content": message})
            st.session_state[hist_key].append(
                {"role": "assistant", "content": body.get("reply") or ""}
            )
            if body.get("proposed_action_label"):
                st.session_state["ask_proposed"] = {
                    "action": body.get("proposed_action"),
                    "label": body.get("proposed_action_label"),
                    "asset_id": asset_id,
                }
        else:
            st.error(body.get("detail") or body)

    history = st.session_state[hist_key]
    # Newest Q&A pair first
    pairs: list[tuple[dict, dict | None]] = []
    i = 0
    while i < len(history):
        turn = history[i]
        if turn.get("role") == "user" and i + 1 < len(history) and history[i + 1].get("role") == "assistant":
            pairs.append((turn, history[i + 1]))
            i += 2
        else:
            pairs.append((turn, None))
            i += 1
    for user_turn, asst_turn in reversed(pairs[-6:]):
        with st.chat_message(user_turn.get("role") or "user"):
            st.markdown(user_turn.get("content") or "")
        if asst_turn:
            with st.chat_message("assistant"):
                st.markdown(asst_turn.get("content") or "")

    proposed = st.session_state.get("ask_proposed")
    if proposed and proposed.get("asset_id") == asset_id and proposed.get("label"):
        st.info(
            f"Suggested next step: **{proposed['label']}**. "
            "Use Site actions under the map, or Approve an action below."
        )
