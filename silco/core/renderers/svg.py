from __future__ import annotations

from typing import Any

from silco.core.diagram import Diagram
from silco.core.kernel import kernel
from silco.core.render_config import RenderConfig
from silco.core.renderers.diagrams_backend import DiagramStyle, render_svg


def svg_renderer(diagram: Diagram, **options: Any) -> str:
    render_options = {
        name: value for name, value in options.items() if name in RenderConfig.model_fields
    }
    config = RenderConfig(direction=diagram.direction, **render_options)
    style = _resolve_style(config)
    return render_svg(diagram, config, style)


def _resolve_style(config: RenderConfig) -> DiagramStyle:
    # Importing the styles package registers its built-in plugins as a side effect.
    import silco.plugins.renderers.styles  # noqa: F401

    available = kernel.names("styles")
    if config.style not in available:
        names = ", ".join(available) or "none"
        raise ValueError(f"Unknown SVG style: {config.style!r}. Available styles: {names}")
    style = kernel.get("styles", config.style)
    if not isinstance(style, DiagramStyle):
        raise TypeError(f"Style plugin {config.style!r} is not a DiagramStyle")
    return style
