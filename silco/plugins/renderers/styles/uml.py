from __future__ import annotations

from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.diagrams_backend import DiagramStyle

PLUGIN_CATEGORY = "styles"
PLUGIN_NAME = "uml"
PLUGIN_DESCRIPTION = "Muted architecture style closer to grayscale UML documentation."
PLUGIN_TAGS = ("builtin", "style", "svg", "uml")

STYLE = DiagramStyle(
    name=PLUGIN_NAME,
    description=PLUGIN_DESCRIPTION,
    graph_attr={
        "bgcolor": "white",
        "splines": "polyline",
        "pad": "0.25",
    },
    node_attr={
        "fontname": "Helvetica",
    },
    edge_attr={
        "color": "#334155",
        "fontcolor": "#0f172a",
        "penwidth": "1.3",
    },
    boundary_attr={
        "style": "dashed",
        "pencolor": "#94a3b8",
        "fontcolor": "#0f172a",
    },
    node_kind_attr={
        "default": {"fillcolor": "#e2e8f0", "fontcolor": "#0f172a", "color": "#334155"},
        "actor": {"fillcolor": "#cbd5e1", "fontcolor": "#0f172a", "style": "rounded,filled", "color": "#334155"},
        "service": {"fillcolor": "#e5e7eb", "fontcolor": "#111827", "color": "#334155"},
        "component": {"fillcolor": "#d1d5db", "fontcolor": "#111827", "color": "#334155"},
        "database": {"fillcolor": "#dbeafe", "fontcolor": "#0f172a", "color": "#334155"},
        "queue": {"fillcolor": "#e5e7eb", "fontcolor": "#111827", "shape": "component", "color": "#334155"},
        "cache": {"fillcolor": "#dcfce7", "fontcolor": "#0f172a", "shape": "cylinder", "color": "#334155"},
        "storage": {"fillcolor": "#e0f2fe", "fontcolor": "#0f172a", "shape": "cylinder", "color": "#334155"},
        "external": {"fillcolor": "gray75", "fontcolor": "#111827", "color": "#475569"},
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
