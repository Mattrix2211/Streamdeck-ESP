"""Core domain model for Streamdeck-ESP.

This package must stay independent from Flask, Windows, Home Assistant,
ESPHome and any concrete device or GUI implementation.
"""

from .actions import ActionCommand, ActionDefinition, ActionValidationError
from .engine import ActionEngine, MissingExecutorError
from .events import InputEvent, InputKind, TriggerBindings
from .navigation import Folder, GridRect, Page, Placement, Profile
from .registry import ActionRegistry, DuplicateActionError, UnknownActionError
from .state import StateStore, StateValue
from .triggers import ActionState, Trigger

__all__ = [
    "ActionCommand",
    "ActionDefinition",
    "ActionEngine",
    "ActionRegistry",
    "ActionState",
    "ActionValidationError",
    "DuplicateActionError",
    "Folder",
    "GridRect",
    "InputEvent",
    "InputKind",
    "MissingExecutorError",
    "Page",
    "Placement",
    "Profile",
    "StateStore",
    "StateValue",
    "Trigger",
    "TriggerBindings",
    "UnknownActionError",
]
