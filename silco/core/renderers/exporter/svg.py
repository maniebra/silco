from __future__ import annotations

from typing import Any

from silco.core.kernel import kernel
from silco.core.renderers.base.config import RenderConfig
from silco.core.renderers.base.diagram import Diagram
from silco.core.renderers.diagrams_backend import DiagramStyle, render_svg


def svg_renderer(diagram: Diagram, **options: Any) -> str:
    render_options = {name: value for name, value in options.items() if name in RenderConfig.model_fields}
    config = RenderConfig(direction=diagram.direction, **render_options)
    style = _resolve_style(config)
    return render_svg(diagram, config, style)


def _resolve_style(config: RenderConfig) -> DiagramStyle:
    from silco.plugins.renderers import styles as _styles  # noqa: F401

    del _styles
    if config.style not in kernel.names("styles"):
        available = ", ".join(kernel.names("styles")) or "none"
        raise ValueError(f"Unknown SVG style: {config.style!r}. Available styles: {available}")
    style = kernel.get("styles", config.style)
    if not isinstance(style, DiagramStyle):
        raise TypeError(f"Style plugin {config.style!r} is not a DiagramStyle")
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
