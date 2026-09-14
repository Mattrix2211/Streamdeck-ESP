"""Runtime plugin loader kept outside the framework-independent Core."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from types import ModuleType

from .core.plugins import PluginContribution, PluginManifest, PluginRegistry, RegisteredPlugin


PluginImporter = Callable[[str], ModuleType]


class PluginLoadError(RuntimeError):
    pass


class PluginLoader:
    """Load trusted Python plugin modules and register their contributions.

    The Core only knows PluginManifest/PluginContribution. Module discovery and
    Python imports are runtime responsibilities and intentionally live here.
    A plugin module must expose a callable ``build_plugin()`` returning
    ``(PluginManifest, PluginContribution)``.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        *,
        importer: PluginImporter = import_module,
    ) -> None:
        self.registry = registry
        self._importer = importer
        self._modules: dict[str, ModuleType] = {}

    def load(self, module_name: str) -> RegisteredPlugin:
        if not module_name or module_name.startswith("."):
            raise PluginLoadError("plugin module name must be absolute and non-empty")
        try:
            module = self._importer(module_name)
        except Exception as exc:
            raise PluginLoadError(f"cannot import plugin module {module_name!r}") from exc

        builder = getattr(module, "build_plugin", None)
        if not callable(builder):
            raise PluginLoadError(f"plugin module {module_name!r} must expose build_plugin()")

        try:
            built = builder()
        except Exception as exc:
            raise PluginLoadError(f"plugin builder failed for {module_name!r}") from exc

        if not isinstance(built, tuple) or len(built) != 2:
            raise PluginLoadError("build_plugin() must return (PluginManifest, PluginContribution)")
        manifest, contribution = built
        if not isinstance(manifest, PluginManifest) or not isinstance(contribution, PluginContribution):
            raise PluginLoadError("build_plugin() returned invalid plugin objects")

        try:
            registered = self.registry.register(manifest, contribution)
        except Exception as exc:
            raise PluginLoadError(f"plugin registration failed for {manifest.id!r}") from exc
        self._modules[manifest.id] = module
        return registered

    def unload(self, plugin_id: str) -> None:
        self.registry.unregister(plugin_id)
        self._modules.pop(plugin_id, None)

    def loaded_module(self, plugin_id: str) -> ModuleType | None:
        return self._modules.get(plugin_id)
