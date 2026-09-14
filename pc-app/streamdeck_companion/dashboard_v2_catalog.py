"""Serializable V2 action catalog for the existing Flask dashboard."""

from __future__ import annotations

from typing import Any

from .core.action_library import ActionLibrary
from .core.property_inspector import PropertyInspector
from .runtime_action_catalog import build_runtime_action_registry


def build_dashboard_action_catalog() -> dict[str, Any]:
    """Return Action Library + Property Inspector metadata for the current UI.

    The existing dashboard can consume this progressively while keeping its
    legacy constants as a fallback during migration.
    """
    registry = build_runtime_action_registry()
    library = ActionLibrary(registry)
    inspector = PropertyInspector(registry)

    actions = []
    for definition in registry.list():
        schema = inspector.schema(definition.id)
        raw_inputs = definition.ui_config.get("inputs", ())
        inputs = tuple(str(value) for value in raw_inputs) if isinstance(raw_inputs, (list, tuple)) else ()
        actions.append(
            {
                "id": definition.id,
                "name": definition.name,
                "category": definition.category,
                "description": definition.description,
                "triggers": tuple(sorted(trigger.value for trigger in definition.supported_triggers)),
                "inputs": inputs,
                "fields": tuple(
                    {
                        "key": field.key,
                        "label": field.label,
                        "type": field.field_type.value,
                        "required": field.required,
                        "default": field.default,
                        "options": field.options,
                        "options_source": field.options_source,
                    }
                    for field in schema.fields
                ),
            }
        )

    return {
        "categories": library.categories(),
        "actions": tuple(actions),
    }
