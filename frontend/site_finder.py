"""Pure site filter/sort helpers (unit-testable, no Streamlit)."""

from __future__ import annotations

from typing import Any, Callable

BAND_ORDER = {
    "High": 0,
    "Needs attention": 1,
    "Watch": 2,
    "Low": 3,
}

FILTER_LABELS = {
    "All": None,
    "High risk": "High",
    "Decision needed": "Needs attention",
    "Watch": "Watch",
    "Low": "Low",
}


def risk_of(asset: dict[str, Any]) -> float:
    try:
        return float(asset.get("current_risk") or asset.get("risk_score") or 0)
    except (TypeError, ValueError):
        return 0.0


def band_for(
    asset: dict[str, Any],
    *,
    label_fn: Callable[[float, bool], str] | None = None,
) -> str:
    from theme import risk_band_label  # local import keeps helper importable in tests

    fn = label_fn or risk_band_label
    return fn(risk_of(asset), bool(asset.get("conflict_flag")))


def filter_sites(
    assets: list[dict[str, Any]],
    *,
    query: str = "",
    show_band: str = "All",
    order_mode: str = "Priority",
    name_fn: Callable[[dict[str, Any]], str] | None = None,
    keep_id: str | None = None,
    inject_keep_when_searching: bool = False,
) -> list[dict[str, Any]]:
    """
    Filter + sort assets for the Find site UI.

    When ``query`` is non-empty, do **not** fall back to the full list on zero
    matches, and do not inject ``keep_id`` unless ``inject_keep_when_searching``.
    """
    from theme import display_name

    def _name(a: dict[str, Any]) -> str:
        if name_fn:
            return name_fn(a)
        return display_name(a.get("name"), a.get("id") or "")

    q = (query or "").strip().lower()
    want = FILTER_LABELS.get(show_band, None)

    filtered: list[dict[str, Any]] = []
    for a in assets:
        band = band_for(a)
        if want and band != want:
            continue
        hay = f"{_name(a)} {a.get('id') or ''}".lower()
        if q and q not in hay:
            continue
        filtered.append(a)

    if order_mode == "Name A–Z":
        filtered.sort(key=lambda a: _name(a).lower())
    elif order_mode == "Severity high→low":
        filtered.sort(key=lambda a: -risk_of(a))
    else:
        filtered.sort(key=lambda a: (BAND_ORDER.get(band_for(a), 9), -risk_of(a)))

    searching = bool(q)
    if (
        keep_id
        and (inject_keep_when_searching or not searching)
        and not any(a.get("id") == keep_id for a in filtered)
    ):
        keep = next((a for a in assets if a.get("id") == keep_id), None)
        if keep is not None:
            filtered = [keep] + filtered

    return filtered
