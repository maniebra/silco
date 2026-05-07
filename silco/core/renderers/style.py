from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from silco.core.config import RenderConfig
from silco.core.renderers.graphics import Canvas, Element

NodeRenderer = Callable[[Any, float, RenderConfig], Element]
EdgeRenderer = Callable[[Any, Any, float, RenderConfig], Element]
GroupRenderer = Callable[[Any, Any, float, RenderConfig], Iterable[Element]]
StyleStylesheet = Callable[[RenderConfig], str]
StyleDefinitions = Callable[[RenderConfig], tuple[Element, ...]]
StyleBackground = Callable[[float, float, RenderConfig], Element]


@dataclass(frozen=True)
class SvgStyle:
    """Composable style description used by the built-in SVG renderer."""

    name: str
    description: str
    stylesheet: StyleStylesheet
    definitions: StyleDefinitions
    render_node: NodeRenderer
    render_edge: EdgeRenderer
    render_group: GroupRenderer
    render_background: StyleBackground

    def configure_canvas(self, canvas: Canvas, width: float, height: float, config: RenderConfig) -> None:
        canvas.style(self.stylesheet(config))
        for definition in self.definitions(config):
            canvas.define(definition)
        canvas.add(self.render_background(width, height, config))
