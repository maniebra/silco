from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib import metadata
from types import ModuleType
from typing import Any, Literal

PluginCategory = Literal["shapes", "renderers", "layouts", "presenters"]
PluginType = PluginCategory
PLUGIN_CATEGORIES: tuple[PluginCategory, ...] = ("shapes", "renderers", "layouts", "presenters")
_CATEGORY_ALIASES = {
    "shape": "shapes",
    "shapes": "shapes",
    "renderer": "renderers",
    "renderers": "renderers",
    "layout": "layouts",
    "layouts": "layouts",
    "presenter": "presenters",
    "presenters": "presenters",
    "representation": "presenters",
    "representations": "presenters",
}


@dataclass(frozen=True)
class PluginInfo:
    """Metadata describing a registered plugin."""

    category: PluginCategory
    name: str
    plugin: Any
    description: str | None = None
    module: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    auto_discovered: bool = False


class SilcoKernel:
    """Registry and discovery hub for core and optional plugins."""

    def __init__(self) -> None:
        self.plugins: dict[PluginCategory, dict[str, Any]] = {category: {} for category in PLUGIN_CATEGORIES}
        self._plugin_info: dict[PluginCategory, dict[str, PluginInfo]] = {category: {} for category in PLUGIN_CATEGORIES}
        self._discovered_modules: set[str] = set()
        self._discovered_entry_points: set[str] = set()

    def register(
        self,
        plugin_type: str,
        name: str,
        plugin: Any,
        *,
        description: str | None = None,
        module: str | None = None,
        tags: Iterable[str] = (),
        auto_discovered: bool = False,
    ) -> Any:
        category = self.normalize_category(plugin_type)
        if not name.strip():
            raise ValueError("plugin name cannot be empty")
        plugin_name = name.strip()
        self.plugins[category][plugin_name] = plugin
        self._plugin_info[category][plugin_name] = PluginInfo(
            category=category,
            name=plugin_name,
            plugin=plugin,
            description=description,
            module=module or getattr(plugin, "__module__", None),
            tags=tuple(tags),
            auto_discovered=auto_discovered,
        )
        return plugin

    def decorator(
        self,
        plugin_type: str,
        name: str,
        *,
        description: str | None = None,
        tags: Iterable[str] = (),
    ) -> Callable[[Any], Any]:
        def register_plugin(plugin: Any) -> Any:
            return self.register(plugin_type, name, plugin, description=description, tags=tags)

        return register_plugin

    def get(self, plugin_type: str, name: str, default: Any = None) -> Any:
        category = self.normalize_category(plugin_type)
        if default is None:
            return self.plugins[category][name]
        return self.plugins[category].get(name, default)

    def info(self, plugin_type: str, name: str) -> PluginInfo:
        category = self.normalize_category(plugin_type)
        return self._plugin_info[category][name]

    def list(self, plugin_type: str | None = None) -> dict[PluginCategory, tuple[PluginInfo, ...]] | tuple[PluginInfo, ...]:
        if plugin_type is not None:
            category = self.normalize_category(plugin_type)
            return tuple(self._plugin_info[category].values())
        return {category: tuple(self._plugin_info[category].values()) for category in PLUGIN_CATEGORIES}

    def names(self, plugin_type: str) -> tuple[str, ...]:
        category = self.normalize_category(plugin_type)
        return tuple(self.plugins[category])

    def categories(self) -> tuple[PluginCategory, ...]:
        return PLUGIN_CATEGORIES

    def normalize_category(self, plugin_type: str) -> PluginCategory:
        try:
            return _CATEGORY_ALIASES[plugin_type]
        except KeyError as exc:
            valid = ", ".join(PLUGIN_CATEGORIES)
            raise ValueError(f"Unknown plugin category: {plugin_type}. Expected one of: {valid}") from exc

    def discover(
        self,
        *,
        namespace: str = "silco.plugins",
        entry_point_group: str = "silco.plugins",
    ) -> tuple[PluginInfo, ...]:
        """Import plugin modules and entry points, returning newly registered plugins."""

        before = self._snapshot()
        self.discover_namespace(namespace)
        self.discover_entry_points(entry_point_group)
        return self._new_plugins_since(before)

    def discover_namespace(self, namespace: str = "silco.plugins") -> tuple[ModuleType, ...]:
        package = importlib.import_module(namespace)
        modules: list[ModuleType] = []
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            return tuple(modules)
        for module_info in pkgutil.iter_modules(package_path, f"{namespace}."):
            if module_info.name in self._discovered_modules:
                continue
            module = importlib.import_module(module_info.name)
            self._discovered_modules.add(module_info.name)
            self._register_from_module(module)
            modules.append(module)
        return tuple(modules)

    def discover_entry_points(self, group: str = "silco.plugins") -> tuple[Any, ...]:
        loaded: list[Any] = []
        entry_points = metadata.entry_points()
        if hasattr(entry_points, "select"):
            selected = entry_points.select(group=group)
        else:  # pragma: no cover - compatibility with old importlib.metadata
            selected = entry_points.get(group, ())
        for entry_point in selected:
            key = f"{entry_point.group}:{entry_point.name}"
            if key in self._discovered_entry_points:
                continue
            plugin = entry_point.load()
            self._discovered_entry_points.add(key)
            self._register_loaded_plugin(entry_point.name, plugin)
            loaded.append(plugin)
        return tuple(loaded)

    def _register_from_module(self, module: ModuleType) -> None:
        register = getattr(module, "register_plugins", None)
        if callable(register):
            register(self)

    def _register_loaded_plugin(self, name: str, plugin: Any) -> None:
        if inspect.ismodule(plugin):
            self._register_from_module(plugin)
            return
        register = getattr(plugin, "register_plugins", None)
        if callable(register):
            register(self)
            return
        category = getattr(plugin, "silco_plugin_category", None)
        plugin_name = getattr(plugin, "silco_plugin_name", name)
        if category is None and callable(plugin):
            plugin(self)
            return
        if category is None:
            raise ValueError(f"Discovered plugin {name!r} does not declare a Silco category")
        self.register(
            category,
            plugin_name,
            plugin,
            description=getattr(plugin, "silco_plugin_description", None),
            tags=getattr(plugin, "silco_plugin_tags", ()),
            auto_discovered=True,
        )

    def _snapshot(self) -> set[tuple[PluginCategory, str]]:
        return {(category, name) for category, plugins in self.plugins.items() for name in plugins}

    def _new_plugins_since(self, snapshot: set[tuple[PluginCategory, str]]) -> tuple[PluginInfo, ...]:
        new_plugins: list[PluginInfo] = []
        for category, infos in self._plugin_info.items():
            for name, info in infos.items():
                if (category, name) not in snapshot:
                    new_plugins.append(info)
        return tuple(new_plugins)


kernel = SilcoKernel()
