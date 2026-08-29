"""NVIDIA NIM / FAKE_LLM action brief client (Sprint 3) — JSON → Pydantic → Markdown."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from api.services.brief_schema import (
    ActionBrief,
    JudgeVerdict,
    deterministic_validate,
    fake_action_brief,
    render_brief_markdown,
)

# Repo root .env (backend/api/services -> ../../../)
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")

NVIDIA_BASE = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
EXEC_TOKEN = "AEGIS-EXEC-DEMO"

_BRIEF_JSON_SCHEMA_HINT = (
    "{"
    '"asset_id":"str","risk":0.0,"confidence":0.0,"conflict_flag":false,'
    '"conflict_warning":"str|null","drivers":["str"],'
    '"cited_sensors":{"load":0.0,"oil_temp":0.0,"voltage":0.0},'
    '"cited_weather":{"wind_speed":0.0,"flood_surge_level":0.0},'
    '"downstream_ids":["str"],"trade_off":"str",'
    '"recommended_action":"load_shed|reroute|deenergize","summary":"str"'
    "}"
)


def use_fake_llm() -> bool:
    fake = os.getenv("FAKE_LLM", "1").strip().lower()
    if fake in {"1", "true", "yes"}:
        return True
    key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    return not key


def suggest_action_level(facts: dict[str, Any]) -> str:
    """Heuristic AI recommendation for ShadowLog / AuditLog."""
    risk = float(facts.get("risk") or 0.0)
    conflict = bool(facts.get("conflict_flag"))
    if conflict or risk > 0.7:
        return "deenergize"
    if risk > 0.5:
        return "reroute"
    if risk > 0.3:
        return "load_shed"
    return "load_shed"


def fake_brief_markdown(facts: dict[str, Any]) -> str:
    """Backward-compatible FAKE markdown (structured → render)."""
    brief = fake_action_brief(facts)
    return render_brief_markdown(brief, provider="fake")


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    # Reasoning models may prepend chatter — take outermost object
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        return t[start : end + 1]
    return t


def _nvidia_chat(system: str, user: str, *, max_tokens: int = 1200) -> str:
    key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    resp = requests.post(
        f"{NVIDIA_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "model": NVIDIA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        },
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _parse_action_brief(raw: str) -> ActionBrief:
    return ActionBrief.model_validate_json(_strip_json_fences(raw))


def _nvidia_action_brief(facts: dict[str, Any]) -> ActionBrief:
    system = (
        "You are AEGIS, a utility incident-command briefing assistant. "
        "Respond with ONLY a single JSON object (no markdown fences, no prose) "
        f"matching this shape: {_BRIEF_JSON_SCHEMA_HINT}. "
        "Use ONLY the Facts JSON — never invent sensor or weather values. "
        "Copy numeric values from facts into cited_sensors / cited_weather. "
        "If conflict_flag is true, set conflict_warning to a clear WARNING and "
        "recommended_action must be deenergize. "
        "trade_off must contrast replacement_cost CapEx vs lifeline outage "
        "(downstream_ids)."
    )
    user = "Facts JSON:\n" + json.dumps(facts, indent=2)
    raw = _nvidia_chat(system, user)
    return _parse_action_brief(raw)


def generate_action_brief_structured(
    facts: dict[str, Any],
) -> tuple[ActionBrief, str, list[str]]:
    """
    Return (brief, provider, grounding_issues).

    On schema/NIM failure or grounding failure, falls back to FAKE ActionBrief.
    Grounding issues from a successful NIM parse are returned even when we keep
    the brief if issues empty; if issues non-empty we replace with FAKE.
    """
    if use_fake_llm():
        brief = fake_action_brief(facts)
        issues = deterministic_validate(brief, facts)
        return brief, "fake", issues

    try:
        brief = _nvidia_action_brief(facts)
        issues = deterministic_validate(brief, facts)
        if issues:
            fallback = fake_action_brief(facts)
            return fallback, "fake", issues
        return brief, "nvidia", []
    except (ValidationError, json.JSONDecodeError, KeyError, requests.RequestException) as exc:
        fallback = fake_action_brief(facts)
        return fallback, "fake", [f"nvidia_or_parse_failed: {exc}"]
    except Exception as exc:  # noqa: BLE001
        fallback = fake_action_brief(facts)
        return fallback, "fake", [f"nvidia_or_parse_failed: {exc}"]


def generate_action_brief(facts: dict[str, Any]) -> tuple[str, str]:
    """Return (markdown, provider). Public API unchanged for views/agent."""
    brief, provider, issues = generate_action_brief_structured(facts)
    md = render_brief_markdown(brief, provider=provider)
    if issues and provider == "fake":
        md += (
            "\n\n_Note: structured brief validation/NIM issue "
            f"(`{'; '.join(issues[:3])}`); served FAKE brief._\n"
        )
    return md, provider


def judge_brief(facts: dict[str, Any], brief: ActionBrief | str) -> JudgeVerdict:
    """
    LLM-as-judge for faithfulness. FAKE_LLM → heuristic from deterministic_validate.
    """
    if isinstance(brief, str):
        try:
            structured = _parse_action_brief(brief)
        except Exception:  # noqa: BLE001
            # Treat as markdown-only: build fake for compare + score via issues on facts alone
            structured = fake_action_brief(facts)
            # Prefer checking markdown mentions
            issues = deterministic_validate(structured, facts)
            if str(facts.get("asset_id", "")) not in brief:
                issues.append("markdown missing asset_id")
            if bool(facts.get("conflict_flag")) and "ConflictFlag" not in brief and "WARNING" not in brief:
                issues.append("markdown missing ConflictFlag language")
            faithful = len(issues) == 0
            return JudgeVerdict(
                faithful=faithful,
                score=1.0 if faithful else 0.0,
                issues=issues,
                rationale="heuristic markdown judge (could not parse JSON brief)",
            )
    else:
        structured = brief

    det = deterministic_validate(structured, facts)

    if use_fake_llm():
        faithful = len(det) == 0
        return JudgeVerdict(
            faithful=faithful,
            score=1.0 if faithful else max(0.0, 1.0 - 0.25 * len(det)),
            issues=det,
            rationale="heuristic judge (FAKE_LLM=1)",
        )

    system = (
        "You are a strict QA judge for utility incident briefs. "
        "Return ONLY JSON: "
        '{"faithful":bool,"score":0.0,"issues":["str"],"rationale":"str"}. '
        "score in [0,1]. Mark faithful=false if any sensor/weather/risk numbers "
        "are invented or conflict_flag ignored. Prefer short issues list."
    )
    user = json.dumps(
        {
            "facts": facts,
            "brief": structured.model_dump(),
            "deterministic_issues": det,
        },
        indent=2,
    )
    try:
        raw = _nvidia_chat(system, user, max_tokens=500)
        verdict = JudgeVerdict.model_validate_json(_strip_json_fences(raw))
        # Merge deterministic issues if judge omitted them
        if det:
            merged = list(dict.fromkeys([*verdict.issues, *det]))
            verdict = verdict.model_copy(
                update={
                    "issues": merged,
                    "faithful": verdict.faithful and len(det) == 0,
                    "score": min(verdict.score, 0.5) if det else verdict.score,
                }
            )
        return verdict
    except Exception as exc:  # noqa: BLE001
        faithful = len(det) == 0
        return JudgeVerdict(
            faithful=faithful,
            score=1.0 if faithful else 0.4,
            issues=[*det, f"judge_fallback: {exc}"],
            rationale="judge call failed; used deterministic checks",
        )
