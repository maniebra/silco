from __future__ import annotations

from typing import Any

from silco.core.config import RenderConfig
from silco.core.renderers.graphics import Canvas
from silco.core.kernel import kernel
from silco.core.renderers.style import SvgStyle


def svg_renderer(diagram: Any, **options: Any) -> str:
    renderer_options = {k: v for k, v in options.items() if k in RenderConfig.model_fields}
    config = RenderConfig(direction=diagram.direction, **renderer_options)
    layout_name = options.get("layout", "dag")
    layout = diagram.layout(layout_name, **renderer_options)
    title_height = 44 if diagram.title and config.title else 0
    height = layout.height + title_height

    style = _get_style(config.style)
    canvas = Canvas(layout.width, height, {"role": "img"})
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


def _get_style(name: str) -> SvgStyle:
    normalized = (name or "").strip().lower()
    if not normalized:
        normalized = "modern"
    style = kernel.get("styles", normalized, None)
    if style is None:
        styles = ", ".join(sorted(kernel.names("styles"))) or "<none>"
        raise ValueError(f"unknown svg style: {name!r}. Available styles: {styles}")
    if not isinstance(style, SvgStyle):
        raise TypeError(f"style plugin {normalized!r} is invalid: expected SvgStyle, got {type(style)!r}")
    return style
