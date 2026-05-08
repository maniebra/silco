from silco.core.renderers.base.config import RenderConfig
from silco.core.renderers.base.diagram import Diagram, diagram
from silco.core.renderers.base.layout import Layout
from silco.core.renderers.base.positioned_node import PositionedNode
from silco.core.renderers.base.graphics import Canvas, Element
from silco.core.kernel import PLUGIN_CATEGORIES, PluginCategory, PluginInfo, SilcoKernel, kernel
from silco.core.models import Edge, Group, Node, NodeKind

__all__ = [
    "Canvas",
    "Diagram",
    "Edge",
    "Element",
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
