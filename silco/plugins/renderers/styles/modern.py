from __future__ import annotations

from collections.abc import Iterable

from silco.core.config import RenderConfig
from silco.core.renderers.graphics import Element
from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.style import SvgStyle

PLUGIN_CATEGORY = "styles"
PLUGIN_NAME = "modern"
PLUGIN_DESCRIPTION = "Modern rounded-card style with soft depth and gradients."
PLUGIN_TAGS = ("builtin", "style", "svg")


def _stylesheet(config: RenderConfig) -> str:
    return f"""
.silco-bg {{ fill: #f8fafc; }}
.silco-title {{ font: 700 22px {config.font_family}; fill: #0f172a; }}
.silco-node {{ fill: #ffffff; stroke: #334155; stroke-width: 1.5; filter: drop-shadow(0 8px 14px rgb(15 23 42 / .12)); }}
.silco-label {{ font: 600 13px {config.font_family}; fill: #0f172a; text-anchor: middle; dominant-baseline: middle; }}
.silco-kind {{ font: 600 10px {config.font_family}; fill: #334155; text-anchor: middle; text-transform: uppercase; }}
.silco-edge {{ stroke: #334155; stroke-width: 1.7; fill: none; marker-end: url(#modern-arrow); }}
.silco-edge-label {{ font: 600 11px {config.font_family}; fill: #334155; text-anchor: middle; paint-order: stroke; stroke: #f8fafc; stroke-width: 5; }}
.silco-group {{ fill: url(#modern-package); stroke: #0284c7; stroke-width: 1.2; }}
.silco-group-label {{ font: 700 12px {config.font_family}; fill: #0f172a; }}
""".strip()


def _definitions(_: RenderConfig) -> tuple[Element, ...]:
    return (
        Element(
            "marker",
            {
                "id": "modern-arrow",
                "viewBox": "0 0 10 10",
                "refX": 10,
                "refY": 5,
                "markerWidth": 8,
                "markerHeight": 8,
                "orient": "auto",
                "markerUnits": "strokeWidth",
            },
            children=(Element("path", {"d": "M 0 0 L 10 5 L 0 10 L 2 5 Z", "fill": "#334155"}),),
        ),
        Element(
            "marker",
            {
                "id": "modern-bidir-arrow",
                "viewBox": "0 0 10 10",
                "refX": 9,
                "refY": 5,
                "markerWidth": 7,
                "markerHeight": 7,
                "orient": "auto-start-reverse",
            },
            children=(Element("path", {"d": "M 0 0 L 10 5 L 0 10 z", "fill": "#475569"}),),
        ),
        Element(
            "linearGradient",
            {"id": "modern-canvas", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#f8fafc"}),
                Element("stop", {"offset": "100%", "stop-color": "#eef2ff"}),
            ),
        ),
        Element(
            "linearGradient",
            {"id": "modern-package", "x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#e0f2fe", "stop-opacity": "0.92"}),
                Element("stop", {"offset": "100%", "stop-color": "#e2e8f0", "stop-opacity": "0.82"}),
            ),
        ),
    )


def _background(width: float, height: float, _: RenderConfig) -> Element:
    return Element(
        "rect",
        {
            "class": "silco-bg",
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "fill": "url(#modern-canvas)",
        },
    )


def _node(item, y_offset: float, config: RenderConfig) -> Element:
    node = item.node
    x = item.x
    y = item.y + y_offset
    body = Element(
        "rect",
        {
            "class": "silco-node",
            "x": x,
            "y": y,
            "width": item.width,
            "height": item.height,
            "rx": 12,
        },
    )
    kind = Element("text", {"class": "silco-kind", "x": x + item.width / 2, "y": y + 18}, text=node.kind)
    label = Element("text", {"class": "silco-label", "x": x + item.width / 2, "y": y + 40}, text=node.display_label)
    icon = _node_icon(node.kind, x, y, item.width, item.height)
    children = [body, kind, label]
    if icon is not None:
        children.append(icon)
    return Element("g", children=tuple(children))


def _node_icon(kind: str, x: float, y: float, width: float, height: float) -> Element | None:
    if kind == "actor":
        center = x + width / 2
        return Element(
            "line",
            {
                "x1": center,
                "y1": y + 22,
                "x2": center,
                "y2": y + 34,
                "stroke": "#334155",
                "stroke-width": "1.8",
            },
        )
    if kind == "database":
        return Element(
            "ellipse",
            {
                "cx": x + width / 2,
                "cy": y + height - 10,
                "rx": max((width - 28) / 2, 6),
                "ry": 6,
                "fill": "#dbeafe",
                "stroke": "#334155",
                "stroke-width": "1.2",
            },
        )
    if kind == "queue":
        return Element(
            "path",
            {
                "d": (
                    f"M {x + 12:.1f} {y + 16:.1f} "
                    f"L {x + width - 12:.1f} {y + 16:.1f} "
                    f"L {x + width - 4:.1f} {y + height / 2:.1f} "
                    f"L {x + width - 12:.1f} {y + height - 16:.1f} "
                    f"L {x + 12:.1f} {y + height - 16:.1f} Z"
                ),
                "fill": "none",
                "stroke": "#334155",
                "stroke-width": "1.4",
            },
        )
    if kind == "external":
        return Element(
            "rect",
            {
                "x": x + 9,
                "y": y + 14,
                "width": width - 18,
                "height": height - 24,
                "rx": 8,
                "fill": "none",
                "stroke": "#334155",
                "stroke-width": "1",
                "stroke-dasharray": "4 4",
            },
        )
    return None


def _edge(edge, layout, y_offset: float, config: RenderConfig) -> Element:
    source = layout.nodes[edge.source]
    target = layout.nodes[edge.target]
    sx = source.x + source.width
    sy = source.y + y_offset + source.height / 2
    tx = target.x
    ty = target.y + y_offset + target.height / 2
    if target.x < source.x:
        sx = source.x
        tx = target.x + target.width
    mx = (sx + tx) / 2
    line = Element(
        "path",
        {
            "class": "silco-edge",
            "d": f"M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}",
            "marker-start": "url(#modern-bidir-arrow)" if edge.bidirectional else None,
            "marker-end": "url(#modern-arrow)",
        },
    )
    children = [line]
    if edge.display_label:
        children.append(
            Element(
                "text",
                {"class": "silco-edge-label", "x": mx, "y": (sy + ty) / 2 - 8},
                text=edge.display_label,
            )
        )
    return Element("g", children=tuple(children))


def _group_path(x: float, y: float, width: float, height: float) -> str:
    tab_width = 72
    tab_height = 22
    return (
        f"M {x:.1f} {y + tab_height:.1f} "
        f"L {x + 14:.1f} {y:.1f} "
        f"H {x + 14 + tab_width:.1f} "
        f"V {y + tab_height:.1f} "
        f"H {x + width:.1f} "
        f"V {y + height:.1f} "
        f"H {x:.1f} "
        f"Z"
    )


def _groups(diagram, layout, y_offset: float, config: RenderConfig) -> Iterable[Element]:
    del config
    for group_id, group in diagram.groups.items():
        members = [layout.nodes[node.id] for node in diagram.nodes.values() if node.group == group_id and node.id in layout.nodes]
        if not members:
            continue
        x1 = min(item.x for item in members) - 16
        y1 = min(item.y for item in members) + y_offset - 26
        x2 = max(item.x + item.width for item in members) + 16
        y2 = max(item.y + item.height for item in members) + y_offset + 16
        yield Element(
            "g",
            children=(
                Element("path", {"class": "silco-group", "d": _group_path(x1, y1, x2 - x1, y2 - y1)}),
                Element("text", {"class": "silco-group-label", "x": x1 + 20, "y": y1 + 14}, text=group.display_label),
            ),
        )


STYLE = SvgStyle(
    name=PLUGIN_NAME,
    description=PLUGIN_DESCRIPTION,
    stylesheet=_stylesheet,
    definitions=_definitions,
    render_node=_node,
    render_edge=_edge,
    render_group=_groups,
    render_background=_background,
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
