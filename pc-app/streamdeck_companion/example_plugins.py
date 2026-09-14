"""Reference plugin contributions used by docs/tests, not auto-loaded at runtime."""

from __future__ import annotations

from .core.actions import ActionDefinition
from .core.plugins import PluginContribution, PluginManifest, PluginPermission
from .core.widgets import WidgetDefinition, WidgetType


def system_plugin() -> tuple[PluginManifest, PluginContribution]:
    return (
        PluginManifest(
            id="system",
            name="System",
            version="1.0.0",
            permissions=frozenset({PluginPermission.PROCESS, PluginPermission.AUDIO}),
        ),
        PluginContribution(
            actions=(
                ActionDefinition(
                    id="system.launch",
                    name="Launch Application",
                    category="Windows",
                    parameters={"target": {"type": "text", "required": True}},
                ),
                ActionDefinition(id="system.volume", name="Set Volume", category="Windows"),
            ),
            widgets=(WidgetDefinition("system.volume.widget", WidgetType.GAUGE, state_key="audio:master-volume"),),
            settings={"preferred_audio_device": {"type": "text"}},
            assets={"icon": "assets/system.svg"},
        ),
    )


def home_assistant_plugin() -> tuple[PluginManifest, PluginContribution]:
    return (
        PluginManifest(
            id="home_assistant",
            name="Home Assistant",
            version="1.0.0",
            permissions=frozenset({PluginPermission.NETWORK, PluginPermission.HOME_ASSISTANT}),
        ),
        PluginContribution(
            actions=(
                ActionDefinition(id="home_assistant.toggle", name="Toggle Entity", category="Home Assistant"),
                ActionDefinition(id="home_assistant.service", name="Call Service", category="Home Assistant"),
            ),
            widgets=(
                WidgetDefinition("home_assistant.sensor", WidgetType.STATUS),
                WidgetDefinition("home_assistant.gauge", WidgetType.GAUGE),
            ),
            events=("home_assistant.state_changed",),
            settings={
                "url": {"type": "text", "required": True},
                "token": {"type": "secret", "required": True},
            },
            assets={"icon": "assets/home-assistant.svg"},
        ),
    )


def obs_plugin() -> tuple[PluginManifest, PluginContribution]:
    return (
        PluginManifest(
            id="obs",
            name="OBS Studio",
            version="1.0.0",
            permissions=frozenset({PluginPermission.NETWORK}),
        ),
        PluginContribution(
            actions=(
                ActionDefinition(id="obs.scene", name="Switch Scene", category="OBS"),
                ActionDefinition(id="obs.stream.toggle", name="Start / Stop Stream", category="OBS"),
                ActionDefinition(id="obs.record.toggle", name="Start / Stop Recording", category="OBS"),
            ),
            widgets=(WidgetDefinition("obs.status", WidgetType.STATUS, state_key="obs:stream"),),
            events=("obs.scene_changed", "obs.stream_state_changed"),
            settings={
                "host": {"type": "text", "default": "127.0.0.1"},
                "port": {"type": "number", "default": 4455},
                "password": {"type": "secret"},
            },
            assets={"icon": "assets/obs.svg"},
        ),
    )
