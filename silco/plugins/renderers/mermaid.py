from __future__ import annotations

from typing import Any

from silco.core.renderers.base.diagram import Diagram
from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.svg_common import render_mermaid

PLUGIN_CATEGORY = "renderers"
PLUGIN_NAME = "mermaid"
PLUGIN_DESCRIPTION = "Mermaid flowchart text renderer."
PLUGIN_TAGS = ("builtin", "renderer", "text")


def mermaid_renderer(diagram: Diagram, **_: Any) -> str:
    return render_mermaid(diagram)


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        mermaid_renderer,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


register_plugins(kernel)
