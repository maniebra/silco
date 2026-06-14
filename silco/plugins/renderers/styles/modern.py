from __future__ import annotations

from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.diagrams_backend import DiagramStyle

PLUGIN_CATEGORY = "styles"
PLUGIN_NAME = "modern"
PLUGIN_DESCRIPTION = "C4-oriented system design style with strong blue primary containers."
PLUGIN_TAGS = ("builtin", "style", "svg", "c4")

STYLE = DiagramStyle(
    name=PLUGIN_NAME,
    description=PLUGIN_DESCRIPTION,
    graph_attr={
        "bgcolor": "white",
        "splines": "spline",
        "pad": "0.35",
    },
    node_attr={
        "fontname": "Helvetica",
    },
    edge_attr={
        "color": "#5b6470",
        "fontcolor": "#374151",
        "penwidth": "1.6",
    },
    boundary_attr={
        "style": "rounded,dashed",
        "pencolor": "#7da8d6",
        "fontcolor": "#0f172a",
    },
    node_kind_attr={
        "default": {"fillcolor": "dodgerblue3", "fontcolor": "white"},
        "actor": {"fillcolor": "dodgerblue4", "style": "rounded,filled"},
        "service": {"fillcolor": "#1168bd"},
        "component": {"fillcolor": "#0b4884"},
        "database": {"fillcolor": "#438dd5"},
        "queue": {"fillcolor": "#5b8def", "shape": "component"},
        "cache": {"fillcolor": "#4d9f8c", "shape": "cylinder"},
        "storage": {"fillcolor": "#3b82a6", "shape": "cylinder"},
        "external": {"fillcolor": "gray60"},
    },
    curvestyle="curved",
)


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        STYLE,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


register_plugins(kernel)
