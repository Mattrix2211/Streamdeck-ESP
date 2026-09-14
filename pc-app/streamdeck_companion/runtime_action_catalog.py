"""Declarative catalog for actions currently supported by the companion app."""

from __future__ import annotations

from .core.actions import ActionDefinition
from .core.registry import ActionRegistry
from .core.triggers import Trigger


BUTTON_TRIGGERS = frozenset(
    {Trigger.PRESS, Trigger.DOUBLE_PRESS, Trigger.HOLD, Trigger.LONG_PRESS, Trigger.RELEASE}
)
ENCODER_TRIGGERS = frozenset(
    {Trigger.ROTATE_CW, Trigger.ROTATE_CCW, Trigger.PRESS, Trigger.HOLD, Trigger.RELEASE}
)
ALL_TRIGGERS = BUTTON_TRIGGERS | ENCODER_TRIGGERS


def build_runtime_action_registry() -> ActionRegistry:
    registry = ActionRegistry()
    for definition in runtime_action_definitions():
        registry.register(definition)
    return registry


def runtime_action_definitions() -> tuple[ActionDefinition, ...]:
    return (
        _definition("keys", "Raccourci clavier", "Windows", "hotkey", "Raccourci", BUTTON_TRIGGERS),
        _definition("launch", "Lancer une application", "Windows", "path", "Application", BUTTON_TRIGGERS),
        _definition("url", "Ouvrir un site web", "Windows", "url", "URL", BUTTON_TRIGGERS),
        _definition("media", "Musique / volume du PC", "Windows", "select", "Commande média", ALL_TRIGGERS),
        _definition("audio_output", "Changer de haut-parleur", "Windows", "select", "Sortie audio", ALL_TRIGGERS),
        _definition("app_volume", "Volume d'une application", "Windows", "select", "Application", ENCODER_TRIGGERS),
        _definition("app_mute", "Couper le son d'une application", "Windows", "select", "Application", ALL_TRIGGERS),
        _definition(
            "home_assistant",
            "Action Home Assistant",
            "Home Assistant",
            "home_assistant_service",
            "Service / entité",
            BUTTON_TRIGGERS,
        ),
        _definition(
            "ha_adjust",
            "Ajuster un appareil Home Assistant",
            "Home Assistant",
            "home_assistant_adjust",
            "Entité / pas",
            ENCODER_TRIGGERS,
        ),
        _definition(
            "navigation",
            "Navigation Streamdeck",
            "Streamdeck",
            "navigation",
            "Commande / cible",
            ALL_TRIGGERS,
        ),
    )


def _definition(
    action_id: str,
    name: str,
    category: str,
    field_type: str,
    label: str,
    triggers: frozenset[Trigger],
) -> ActionDefinition:
    return ActionDefinition(
        id=action_id,
        name=name,
        category=category,
        parameters={
            "target": {
                "type": field_type,
                "label": label,
                "required": True,
            }
        },
        supported_triggers=triggers,
        ui_config={
            "fields": (
                {
                    "name": "target",
                    "type": field_type,
                    "label": label,
                    "required": True,
                },
            )
        },
    )
