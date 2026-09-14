"""V2 dashboard API helpers independent from the legacy Flask view logic."""

from __future__ import annotations

from typing import Any

from .dashboard_action_choices import action_choices, choice_ids, choice_labels
from .dashboard_v2_catalog import build_dashboard_action_catalog


DASHBOARD_ACTION_CATALOG = build_dashboard_action_catalog()


def dashboard_action_context() -> dict[str, Any]:
    """Return template-compatible action choices derived from the V2 registry."""
    return {
        "action_types": choice_ids(DASHBOARD_ACTION_CATALOG, "button"),
        "encoder_action_types": choice_ids(DASHBOARD_ACTION_CATALOG, "encoder"),
        "action_type_labels": choice_labels(DASHBOARD_ACTION_CATALOG),
    }


def dashboard_action_catalog_payload() -> dict[str, Any]:
    """Return a JSON-serializable V2 catalog for the dynamic Property Inspector."""
    return {
        "categories": tuple(DASHBOARD_ACTION_CATALOG.get("categories") or ()),
        "actions": tuple(DASHBOARD_ACTION_CATALOG.get("actions") or ()),
        "choices": {
            "button": action_choices(DASHBOARD_ACTION_CATALOG, "button"),
            "encoder": action_choices(DASHBOARD_ACTION_CATALOG, "encoder"),
        },
    }
