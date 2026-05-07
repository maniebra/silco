from __future__ import annotations

from typing import Any

from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.svg import svg_renderer as render_svg

PLUGIN_CATEGORY = "renderers"
PLUGIN_NAME = "svg"
PLUGIN_DESCRIPTION = "Builtin SVG renderer with configurable style plugin support."
PLUGIN_TAGS = ("builtin", "renderer", "vector")


def svg_renderer(diagram: Any, **options: Any) -> str:
    return render_svg(diagram, **options)


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        svg_renderer,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


register_plugins(kernel)
