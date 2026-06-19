from silco.core.diagram import Diagram, diagram
from silco.core.graphics import Canvas, Element
from silco.core.kernel import (
    PLUGIN_CATEGORIES,
    PluginCategory,
    PluginInfo,
    SilcoKernel,
    kernel,
)
from silco.core.layout import Layout
from silco.core.models import Edge, Flow, Group, Node, NodeKind
from silco.core.positioned_node import PositionedNode
from silco.core.render_config import RenderConfig

__all__ = [
    "Canvas",
    "Diagram",
    "Edge",
    "Element",
    "Flow",
    "Group",
    "Layout",
    "Node",
    "NodeKind",
    "PLUGIN_CATEGORIES",
    "PluginCategory",
    "PluginInfo",
    "PositionedNode",
    "RenderConfig",
    "SilcoKernel",
    "diagram",
    "kernel",
]

# Register built-in layouts/renderers on import.
# This keeps `Diagram.to_svg()` working out of the box.
from silco.core import renderers as _renderers  # noqa: F401, E402
