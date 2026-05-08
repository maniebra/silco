from silco.core.renderers.exporter.svg import svg_renderer
from silco.core.kernel import kernel
from silco.core.renderers.base.diagram import mermaid_renderer
from silco.core.renderers.base.layout import dag_layout, grid_layout

kernel.register(
    "layouts",
    "dag",
    dag_layout,
    description="Layered directed-acyclic-graph layout for left-to-right system flows.",
    tags=("builtin", "layout"),
)
kernel.register(
    "layouts",
    "grid",
    grid_layout,
    description="Simple grid layout for unordered component maps.",
    tags=("builtin", "layout"),
)
kernel.register(
    "renderers",
    "svg",
    svg_renderer,
    description="Standalone SVG renderer for notebooks, docs, and exports.",
    tags=("builtin", "renderer", "vector"),
)
kernel.register(
    "renderers",
    "mermaid",
    mermaid_renderer,
    description="Mermaid flowchart text renderer.",
    tags=("builtin", "renderer", "text"),
)

__all__ = ["mermaid_renderer", "svg_renderer"]
