"""Registry wiring for collaborative workflow orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..registry import AstroRegistry

__all__ = ["register_orchestration_module", "load_multi_agent_plan", "MULTI_AGENT_PLAN_PATH"]

MULTI_AGENT_PLAN_PATH = Path(__file__).with_name("multi_agent_workflow.json")


def load_multi_agent_plan() -> dict[str, Any]:
    """Return the parsed multi-agent workflow description."""

    data = json.loads(MULTI_AGENT_PLAN_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):  # pragma: no cover - defensive guard
        raise TypeError("Multi-agent workflow payload must be a mapping")
    return data


def register_orchestration_module(registry: AstroRegistry) -> None:
    """Register orchestration workflows, including the multi-agent pipeline."""

    plan = load_multi_agent_plan()
    module = registry.register_module(
        "orchestration",
        metadata={
            "description": "Operational workflows coordinating multi-agent astrology tasks.",
            "data_inputs": ["csv", "json", "sqlite"],
            "integrity_note": (
                "Every workflow references Solar Fire exports, Swiss Ephemeris assets,"
                " and documented reporting specs to keep results data-backed."
            ),
        },
    )

    multi_agent = module.register_submodule(
        "multi_agent",
        metadata={
            "description": "Cooperative agents spanning ingest, ephemeris verification, and reporting.",
            "plan_file": "astroengine/modules/orchestration/multi_agent_workflow.json",
        },
    )

    workflows = multi_agent.register_channel(
        "workflows",
        metadata={
            "description": "Multi-agent playbooks sourced from verified dataset contracts.",
        },
    )

    workflows.register_subchannel(
        plan.get("id", "multi_agent_plan"),
        metadata={
            "description": plan.get("description", ""),
            "version": plan.get("version", "unknown"),
            "agent_count": len(plan.get("agents", [])),
        },
        payload=plan,
    )
