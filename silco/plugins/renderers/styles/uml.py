from __future__ import annotations

from collections.abc import Iterable

from silco.core.config import RenderConfig
from silco.core.renderers.graphics import Element
from silco.core.kernel import SilcoKernel, kernel
from silco.core.renderers.style import SvgStyle

PLUGIN_CATEGORY = "styles"
PLUGIN_NAME = "uml"
PLUGIN_DESCRIPTION = "UML-aligned nodes and labels (<<stereotype>>) for UML-heavy diagrams."
PLUGIN_TAGS = ("builtin", "style", "svg", "uml")


def _stylesheet(config: RenderConfig) -> str:
    return f"""
.silco-bg {{ fill: #f8fafc; }}
.silco-title {{ font: 700 22px {config.font_family}; fill: #0f172a; }}
.silco-node {{ fill: #ffffff; stroke: #334155; stroke-width: 1.5; filter: drop-shadow(0 8px 14px rgb(15 23 42 / .12)); }}
.silco-label {{ font: 600 13px {config.font_family}; fill: #0f172a; text-anchor: middle; dominant-baseline: middle; }}
.silco-kind {{ font: 600 10px {config.font_family}; fill: #334155; text-anchor: middle; text-transform: none; }}
.silco-edge {{ stroke: #334155; stroke-width: 1.6; fill: none; marker-end: url(#uml-arrow); }}
.silco-edge-label {{ font: 600 11px {config.font_family}; fill: #0f172a; text-anchor: middle; paint-order: stroke; stroke: #f8fafc; stroke-width: 5; }}
.silco-group {{ fill: url(#uml-package); stroke: #0284c7; stroke-width: 1.2; }}
.silco-group-label {{ font: 700 12px {config.font_family}; fill: #0f172a; }}
.silco-uml-shape {{ stroke: #334155; fill: #e2e8f0; stroke-width: 1.25; }}
.silco-uml-icon {{ stroke: #334155; fill: #e2e8f0; stroke-width: 1.25; }}
.silco-uml-icon-line {{ stroke: #334155; stroke-width: 1.6; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
""".strip()


def _definitions(_: RenderConfig) -> tuple[Element, ...]:
    return (
        Element(
            "marker",
            {
                "id": "uml-arrow",
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
                "id": "uml-bidir-arrow",
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
            {"id": "uml-canvas", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#f8fafc"}),
                Element("stop", {"offset": "100%", "stop-color": "#eef2ff"}),
            ),
        ),
        Element(
            "linearGradient",
            {"id": "uml-package", "x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%"},
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
            "fill": "url(#uml-canvas)",
        },
    )


def _node(item, y_offset: float, config: RenderConfig) -> Element:
    del config
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
            "rx": 16 if node.kind in {"actor", "external"} else 12,
        },
    )
    children: list[Element] = [body]
    children.extend(_node_shape(node.kind, x, y, item.width, item.height))
    children.append(Element("text", {"class": "silco-kind", "x": x + item.width / 2, "y": y + 18}, text=f"<<{node.kind}>>"))
    children.append(Element("text", {"class": "silco-label", "x": x + item.width / 2, "y": y + 34}, text=node.display_label))
    return Element("g", children=tuple(children))


def _edge(edge, layout, y_offset: float, config: RenderConfig) -> Element:
    del config
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
    path = Element(
        "path",
        {
            "class": "silco-edge",
            "d": f"M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}",
            "marker-end": "url(#uml-arrow)",
            "marker-start": "url(#uml-bidir-arrow)" if edge.bidirectional else None,
        },
    )
    children = [path]
    if edge.display_label:
        children.append(Element("text", {"class": "silco-edge-label", "x": mx, "y": (sy + ty) / 2 - 8}, text=edge.display_label))
    return Element("g", children=tuple(children))


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


def _node_shape(kind: str, x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    if kind == "actor":
        return _actor_shape(x, y, width, height)
    if kind == "database":
        return _database_shape(x, y, width, height)
    if kind == "queue":
        return _queue_shape(x, y, width, height)
    if kind == "cache":
        return _cache_shape(x, y, width, height)
    if kind == "storage":
        return _storage_shape(x, y, width, height)
    if kind == "external":
        return _external_shape(x, y, width, height)
    return _component_shape(x, y, width, height)


def _actor_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    center_x = x + width * 0.5
    top = y + 14
    return (
        Element("circle", {"class": "silco-uml-icon", "cx": center_x, "cy": top + 6, "r": 6}),
        Element("line", {"class": "silco-uml-icon-line", "x1": center_x, "y1": top + 12, "x2": center_x, "y2": top + 28}),
        Element(
            "path",
            {
                "class": "silco-uml-icon-line",
                "d": f"M {center_x - 16:.1f} {top + 18:.1f} L {center_x:.1f} {top + 25:.1f} L {center_x + 16:.1f} {top + 18:.1f}",
            },
        ),
        Element(
            "path",
            {
                "class": "silco-uml-icon-line",
                "d": f"M {center_x - 12:.1f} {top + 28:.1f} L {center_x:.1f} {top + 42:.1f} L {center_x + 12:.1f} {top + 28:.1f}",
            },
        ),
    )


def _component_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    top = y + 20
    mid = y + height * 0.5
    return (
        Element(
            "path",
            {
                "class": "silco-uml-shape",
                "d": f"M {x + 14:.1f} {top:.1f} H {x + width - 14:.1f} V {mid:.1f} H {x + width - 7:.1f} V {mid + 16:.1f} H {x + width - 14:.1f} V {y + height - 18:.1f} H {x + 14:.1f} Z",
            },
        ),
        Element("rect", {"class": "silco-uml-icon", "x": x + 8, "y": y + 22, "width": 10, "height": 12, "rx": 2}),
        Element("rect", {"class": "silco-uml-icon", "x": x + width - 18, "y": y + 22, "width": 10, "height": 12, "rx": 2}),
    )


def _database_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    rx = max((width - 28) / 2, 8)
    top = y + 18
    body = y + 18
    return (
        Element(
            "ellipse",
            {
                "class": "silco-uml-shape",
                "cx": x + width / 2,
                "cy": top,
                "rx": rx,
                "ry": 7,
                "fill": "#dcfce7",
                "stroke": "#334155",
            },
        ),
        Element(
            "rect",
            {"class": "silco-uml-shape", "x": x + 14, "y": body, "width": width - 28, "height": height - 28, "rx": rx / 5},
        ),
        Element(
            "ellipse",
            {
                "class": "silco-uml-shape",
                "cx": x + width / 2,
                "cy": y + height - 10,
                "rx": rx,
                "ry": 7,
                "fill": "#dcfce7",
                "stroke": "#334155",
            },
        ),
        Element(
            "ellipse",
            {
                "class": "silco-uml-shape",
                "cx": x + width / 2,
                "cy": y + height - 24,
                "rx": rx,
                "ry": 7,
                "fill": "none",
            },
        ),
    )


def _queue_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    p = (
        x + 12,
        y + 18,
        x + width - 16,
        y + 18,
        x + width - 4,
        y + height / 2,
        x + width - 16,
        y + height - 18,
        x + 12,
        y + height - 18,
        x + 24,
        y + height / 2,
    )
    d = (
        f"M {p[0]:.1f} {p[1]:.1f} L {p[2]:.1f} {p[3]:.1f} L {p[4]:.1f} {p[5]:.1f} L {p[6]:.1f} {p[7]:.1f} L {p[8]:.1f} {p[9]:.1f} L {p[10]:.1f} {p[11]:.1f} Z"
    )
    return (Element("path", {"class": "silco-uml-icon", "d": d}),)


def _cache_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    return (
        Element(
            "rect",
            {
                "class": "silco-uml-icon",
                "x": x + 10,
                "y": y + 12,
                "width": width - 20,
                "height": height - 18,
                "rx": 5,
            },
        ),
        Element("line", {"class": "silco-uml-icon-line", "x1": x + 16, "y1": y + 22, "x2": x + width - 16, "y2": y + 22}),
        Element("line", {"class": "silco-uml-icon-line", "x1": x + 16, "y1": y + 36, "x2": x + width - 16, "y2": y + 36}),
    )


def _storage_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    return (
        Element(
            "path",
            {
                "class": "silco-uml-icon",
                "d": f"M {x + 12:.1f} {y + 20:.1f} H {x + width - 12:.1f} V {y + 24:.1f} H {x + width - 16:.1f} V {y + 50:.1f} H {x + 12:.1f} V {y + 46:.1f} H {x + 16:.1f} V {y + 24:.1f} Z",
            },
        ),
        Element("rect", {"class": "silco-uml-icon-line", "x": x + 12, "y": y + 28, "width": width - 24, "height": 14, "rx": 3}),
        Element("rect", {"class": "silco-uml-icon-line", "x": x + 12, "y": y + 44, "width": width - 24, "height": 8, "rx": 3}),
    )


def _external_shape(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    return (
        Element(
            "rect",
            {
                "class": "silco-uml-shape",
                "x": x + 8,
                "y": y + 16,
                "width": width - 16,
                "height": height - 26,
                "rx": 8,
                "stroke-dasharray": "6 4",
                "fill": "none",
            },
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
