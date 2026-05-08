
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from collections.abc import Iterable

from silco.core.kernel import kernel
from silco.core.models.edge import Edge
from silco.core.renderers.base.diagram import Diagram, group_bounds
from silco.core.renderers.base.config import RenderConfig
from silco.core.renderers.base.graphics import Canvas, Element
from silco.core.renderers.base.positioned_node import PositionedNode
from silco.core.renderers.style import SvgStyle

if TYPE_CHECKING:
    from silco.core.renderers.base.layout import Layout


def svg_renderer(diagram: Diagram, **options: Any) -> str:
    config = RenderConfig(direction=diagram.direction, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    layout_name = options.get("layout", "dag")
    layout = diagram.layout(layout_name, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    title_height = 44 if diagram.title and config.title else 0
    height = layout.height + title_height
    canvas = _svg_canvas(layout.width, height)
    style = _resolve_style(config)
    style.configure_canvas(canvas, layout.width, height, config)
    if diagram.title and config.title:
        canvas.text(diagram.title, 32, 30, class_="silco-title")

    for group in style.render_group(diagram, layout, title_height, config):
        canvas.add(group)
    for edge in diagram.edges:
        canvas.add(style.render_edge(edge, layout, title_height, config))
    for item in layout.nodes.values():
        canvas.add(style.render_node(item, title_height, config))
    return canvas.to_svg()


def _svg_canvas(width: float, height: float) -> Canvas:
    canvas = Canvas(width, height, {"role": "img"})
    return canvas


def _legacy_stylesheet(config: RenderConfig) -> str:
    return f"""
.silco-bg {{ fill: #f8fafc; }}
.silco-title {{ font: 700 22px {config.font_family}; fill: #0f172a; }}
.silco-node {{ fill: #ffffff; stroke: #334155; stroke-width: 1.5; filter: url(#nodeShadow); }}
.silco-node-shell {{ fill: #ffffff; stroke: #334155; stroke-width: 1.5; }}
.silco-label {{ font: 600 13px {config.font_family}; fill: #0f172a; text-anchor: middle; dominant-baseline: middle; letter-spacing: 0.02em; }}
.silco-kind {{ font: 600 10px {config.font_family}; fill: #334155; text-anchor: middle; letter-spacing: 0.05em; }}
.silco-edge {{ stroke: #334155; stroke-width: 1.6; fill: none; marker-end: url(#umlArrow); }}
.silco-edge-label {{ font: 600 11px {config.font_family}; fill: #0f172a; text-anchor: middle; paint-order: stroke; stroke: #f8fafc; stroke-width: 5; }}
.silco-group {{ fill: url(#packageGradient); stroke: #0284c7; stroke-width: 1.25; }}
.silco-group-label {{ font: 700 12px {config.font_family}; fill: #0f172a; }}
.silco-uml-shape {{ stroke: #334155; fill: #e2e8f0; stroke-width: 1.25; }}
.silco-uml-icon {{ stroke: #334155; fill: #e2e8f0; stroke-width: 1.25; }}
.silco-uml-icon-line {{ stroke: #334155; stroke-width: 1.6; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
""".strip()


def _legacy_definitions(_: RenderConfig) -> tuple[Element, ...]:
    return (
        Element(
            "marker",
            {
                "id": "arrow",
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
            "marker",
            {
                "id": "umlArrow",
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
            "linearGradient",
            {"id": "canvasGradient", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#f8fafc"}),
                Element("stop", {"offset": "100%", "stop-color": "#eef2ff"}),
            ),
        ),
        Element(
            "linearGradient",
            {"id": "packageGradient", "x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#e0f2fe", "stop-opacity": "0.92"}),
                Element("stop", {"offset": "100%", "stop-color": "#e2e8f0", "stop-opacity": "0.82"}),
            ),
        ),
        Element(
            "filter",
            {"id": "nodeShadow", "x": "-15%", "y": "-15%", "width": "130%", "height": "140%"},
            children=(
                Element(
                    "feDropShadow",
                    {
                        "dx": "0",
                        "dy": "8",
                        "stdDeviation": "4",
                        "flood-color": "#0f172a",
                        "flood-opacity": "0.14",
                    },
                ),
            ),
        ),
    )


def _legacy_background(width: float, height: float, _: RenderConfig) -> Element:
    return Element("rect", {"x": 0, "y": 0, "width": width, "height": height, "fill": "url(#canvasGradient)", "class": "silco-bg"})


def _legacy_node(item, y_offset: float, _: RenderConfig) -> Element:
    return _svg_node(item, y_offset)


def _legacy_edge(edge, layout, y_offset: float, _: RenderConfig) -> Element:
    return _svg_edge(edge, layout, y_offset)


def _legacy_group(diagram, layout, y_offset: float, _: RenderConfig) -> Iterable[Element]:
    return group_bounds(diagram, layout, y_offset)


def _legacy_svg_style() -> SvgStyle:
    return SvgStyle(
        name="modern",
        description="Legacy built-in SVG style.",
        stylesheet=_legacy_stylesheet,
        definitions=_legacy_definitions,
        render_node=_legacy_node,
        render_edge=_legacy_edge,
        render_group=_legacy_group,
        render_background=_legacy_background,
    )


_FALLBACK_STYLE = _legacy_svg_style()


def _resolve_style(config: RenderConfig) -> SvgStyle:
    # Load built-in style plugins lazily so `to_svg(style=...)` works out of the box.
    try:
        from silco.plugins.renderers import styles as _styles  # noqa: F401
        del _styles
    except ImportError:
        if config.style != "modern":
            raise ValueError(f"Unknown SVG style: {config.style!r}. Available styles: legacy (modern)")
        return _FALLBACK_STYLE

    if config.style == "modern" and config.style not in kernel.names("styles"):
        return _FALLBACK_STYLE

    if config.style not in kernel.names("styles"):
        available = ", ".join(kernel.names("styles")) or "legacy"
        raise ValueError(f"Unknown SVG style: {config.style!r}. Available styles: {available}")

    style = kernel.get("styles", config.style)
    if not isinstance(style, SvgStyle):
        raise TypeError(f"Style plugin {config.style!r} is not a SvgStyle")
    return style


def _svg_node(item: PositionedNode, y_offset: float) -> Element:
    node = item.node
    x, y = item.x, item.y + y_offset
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
    label = node.display_label
    center_x = x + item.width / 2
    top_slot = y + 18
    body_slot = y + 30
    children = [body]
    children.extend(_svg_node_shape(node.kind, x, y, item.width, item.height))
    children += (
        Element("text", {"class": "silco-kind", "x": center_x, "y": top_slot}, text=f"<<{node.kind}>>"),
        Element("text", {"class": "silco-label", "x": center_x, "y": body_slot}, text=label),
    )
    return Element("g", children=tuple(children))


def _svg_edge(edge: Edge, layout: Layout, y_offset: float) -> Element:
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
    children = [
        Element(
            "path",
            {
                "class": "silco-edge",
                "d": f"M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}",
                "marker-end": "url(#umlArrow)",
                "marker-start": "url(#arrow)" if edge.bidirectional else None,
            },
        )
    ]
    if edge.display_label:
        children.append(Element("text", {"class": "silco-edge-label", "x": mx, "y": (sy + ty) / 2 - 8}, text=edge.display_label))
    return Element("g", children=tuple(children))


def _svg_node_shape(kind: str, x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    if kind == "actor":
        return _svg_actor(x, y, width, height)
    if kind == "database":
        return _svg_database(x, y, width, height)
    if kind == "queue":
        return _svg_queue(x, y, width, height)
    if kind == "cache":
        return _svg_cache(x, y, width, height)
    if kind == "storage":
        return _svg_storage(x, y, width, height)
    if kind == "external":
        return _svg_external(x, y, width, height)
    return _svg_component(x, y, width, height)


def _svg_actor(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
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


def _svg_component(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    top = y + 20
    mid = y + height * 0.5
    return (
        Element("path", {"class": "silco-uml-shape", "d": f"M {x + 14:.1f} {top:.1f} H {x + width - 14:.1f} V {mid:.1f} H {x + width - 7:.1f} V {mid + 16:.1f} H {x + width - 14:.1f} V {y + height - 18:.1f} H {x + 14:.1f} Z"}),
        Element("rect", {"class": "silco-uml-icon", "x": x + 8, "y": y + 22, "width": 10, "height": 12, "rx": 2}),
        Element("rect", {"class": "silco-uml-icon", "x": x + width - 18, "y": y + 22, "width": 10, "height": 12, "rx": 2}),
    )


def _svg_database(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
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


def _svg_queue(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
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
        f"M {p[0]:.1f} {p[1]:.1f} "
        f"L {p[2]:.1f} {p[3]:.1f} "
        f"L {p[4]:.1f} {p[5]:.1f} "
        f"L {p[6]:.1f} {p[7]:.1f} "
        f"L {p[8]:.1f} {p[9]:.1f} "
        f"L {p[10]:.1f} {p[11]:.1f} "
        f"Z"
    )
    return (Element("path", {"class": "silco-uml-icon", "d": d}),)


def _svg_cache(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    return (
        Element(
            "rect",
            {"class": "silco-uml-icon", "x": x + 10, "y": y + 12, "width": width - 20, "height": height - 18, "rx": 5},
        ),
        Element(
            "line",
            {"class": "silco-uml-icon-line", "x1": x + 16, "y1": y + 22, "x2": x + width - 16, "y2": y + 22},
        ),
        Element(
            "line",
            {"class": "silco-uml-icon-line", "x1": x + 16, "y1": y + 36, "x2": x + width - 16, "y2": y + 36},
        ),
    )


def _svg_storage(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
    return (
        Element(
            "path",
            {
                "class": "silco-uml-icon",
                "d": f"M {x+12:.1f} {y+20:.1f} H {x+width-12:.1f} V {y+24:.1f} H {x+width-16:.1f} V {y+50:.1f} H {x+12:.1f} V {y+46:.1f} H {x+16:.1f} V {y+24:.1f} Z",
            },
        ),
        Element("rect", {"class": "silco-uml-icon-line", "x": x + 12, "y": y + 28, "width": width - 24, "height": 14, "rx": 3}),
        Element("rect", {"class": "silco-uml-icon-line", "x": x + 12, "y": y + 44, "width": width - 24, "height": 8, "rx": 3}),
    )


def _svg_external(x: float, y: float, width: float, height: float) -> tuple[Element, ...]:
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
