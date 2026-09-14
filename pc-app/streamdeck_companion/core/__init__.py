"""Core domain model for Streamdeck-ESP.

This package must stay independent from Flask, Windows, Home Assistant,
ESPHome and any concrete device or GUI implementation.
"""

from .actions import ActionCommand, ActionDefinition, ActionValidationError
from .registry import ActionRegistry, DuplicateActionError, UnknownActionError
from .triggers import ActionState, Trigger

__all__ = [
    "ActionCommand",
    "ActionDefinition",
    "ActionRegistry",
    "ActionState",
    "ActionValidationError",
    "DuplicateActionError",
    "Trigger",
    "UnknownActionError",
]
