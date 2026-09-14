"""Progressive V2 runtime wrapper around the historical DeviceClient.

The existing DeviceClient remains the hardware/ESPHome implementation while
this subclass injects V2 event, state and navigation concepts around it. Special
UI behavior and existing firmware commands stay in the historical class.
"""

from __future__ import annotations

from typing import Any

from . import actions as action_runner
from . import profile_pages
from .core.legacy import to_legacy
from .core.navigator import NavigationError, Navigator
from .device_client import ACTION_EVENT_ENTITY, ENCODER_EVENT_ENTITIES, DeviceClient
from .device_event_runtime import resolve_esphome_action
from .multi_action_runtime import MultiActionRuntime
from .navigation_legacy import profile_from_legacy
from .runtime_state import STATE_STORE
from .state_adapters import update_device_connection
from .v2_runtime_actions import execute_navigation_target, register_multi_action, register_navigation_action


class V2DeviceClient(DeviceClient):
    """DeviceClient using V2 adapters without changing the ESPHome transport."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._navigator: Navigator | None = None
        self._navigator_source_key: tuple[object, ...] | None = None
        self._multi_action_runtime = MultiActionRuntime(lambda: self.config, self._dispatch_multi_action_command)
        register_navigation_action(self)
        register_multi_action(self._multi_action_runtime)

    @property
    def connected(self) -> bool:
        return getattr(self, "_v2_connected", False)

    @connected.setter
    def connected(self, value: bool) -> None:
        connected = bool(value)
        self._v2_connected = connected
        update_device_connection(STATE_STORE, connected)

    def _base_active_profile(self) -> dict:
        return super()._active_profile()

    def _ensure_navigator(self, profile: dict) -> Navigator:
        core_profile = profile_from_legacy(profile)
        source_key = (
            id(profile),
            core_profile.id,
            core_profile.home_page_id,
            tuple(page.id for page in core_profile.pages),
            tuple((folder.id, folder.page_id, folder.parent_id) for folder in core_profile.folders),
        )
        if self._navigator is None:
            self._navigator = Navigator(core_profile)
            self._navigator_source_key = source_key
        elif self._navigator_source_key != source_key:
            self._navigator.reset_profile(core_profile)
            self._navigator_source_key = source_key
        return self._navigator

    def _active_legacy_page_id(self, profile: dict | None = None) -> str:
        base_profile = profile or self._base_active_profile()
        navigator = self._ensure_navigator(base_profile)
        return str(navigator.current_page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def _active_profile(self) -> dict:
        """Return a legacy-compatible view whose root slots are the active page."""
        base_profile = self._base_active_profile()
        page_id = self._active_legacy_page_id(base_profile)
        home_id = str(base_profile.get("home_page_id") or profile_pages.HOME_PAGE_ID)
        if page_id == home_id:
            return base_profile
        view = dict(base_profile)
        view["slots"] = profile_pages.page_slots(base_profile, page_id)
        view["_v2_active_page_id"] = page_id
        return view

    @property
    def active_page_id(self) -> str:
        return self._active_legacy_page_id()

    def navigate(self, command: str, target: str | None = None) -> str:
        """Navigate pages through the pure Core Navigator and refresh the screen."""
        base_profile = self._base_active_profile()
        navigator = self._ensure_navigator(base_profile)
        normalized = command.strip().lower().replace("-", "_")

        if normalized == "next":
            page = navigator.next()
        elif normalized == "previous":
            page = navigator.previous()
        elif normalized == "home":
            page = navigator.home()
        elif normalized == "back":
            page = navigator.back()
        elif normalized in {"go_to", "goto"}:
            if not target:
                raise NavigationError("go_to requires a target page id")
            page = navigator.go_to(self._core_page_id(navigator, target))
        else:
            raise NavigationError(f"unknown navigation command: {command!r}")

        self._refresh_after_navigation()
        return str(page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def open_folder(self, folder_id: str) -> str:
        """Open a nested folder through the same Navigator used by page actions."""
        navigator = self._ensure_navigator(self._base_active_profile())
        page = navigator.open_folder(folder_id)
        self._refresh_after_navigation()
        return str(page.metadata.get("legacy_page_id") or profile_pages.HOME_PAGE_ID)

    def _refresh_after_navigation(self) -> None:
        if self.connected:
            self.push_config()

    def _dispatch_multi_action_command(self, command):
        legacy = to_legacy(command)
        if command.action_id == "home_assistant":
            return self._run_home_assistant_action(legacy)
        if command.action_id == "ha_adjust":
            return self._run_ha_adjust(legacy)
        if command.action_id == "navigation":
            target = str(command.parameters.get("target") or "")
            return self._run_threadsafe(lambda: execute_navigation_target(self, target), 5.0)
        if command.action_id == "multi_action":
            raise ValueError("nested multi actions are not supported yet")
        return action_runner.run(legacy)

    async def run_forever(self) -> None:
        try:
            await super().run_forever()
        finally:
            self._multi_action_runtime.shutdown(wait=False)

    @staticmethod
    def _core_page_id(navigator: Navigator, legacy_page_id: str) -> str:
        for page in navigator.profile.pages:
            if page.metadata.get("legacy_page_id") == legacy_page_id:
                return page.id
        raise NavigationError(f"unknown page: {legacy_page_id!r}")

    def _resolve_action(self, entity_name: str, event_type: str) -> dict | None:
        """Resolve current config through ESPHome -> Core -> active V2 page."""
        profile = self._base_active_profile()
        return resolve_esphome_action(
            profile,
            entity_name,
            event_type,
            action_entity_name=ACTION_EVENT_ENTITY,
            encoder_entity_names=ENCODER_EVENT_ENTITIES,
            page_id=self._active_legacy_page_id(profile),
        )
