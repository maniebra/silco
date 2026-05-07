from __future__ import annotations

import importlib
from collections import deque
from collections.abc import Iterable
from math import ceil, sqrt
from os import PathLike
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from silco.core.config import RenderConfig
from silco.core.renderers.graphics import Canvas, Element
from silco.core.kernel import kernel
from silco.core.models.node import Edge, Group, Node

Direction = Literal["LR", "RL", "TB", "BT"]


class PositionedNode(BaseModel):
    node: Node
    x: float
    y: float
    width: float
    height: float


class Layout(BaseModel):
    nodes: dict[str, PositionedNode]
    width: float
    height: float


class Diagram(BaseModel):
    """Mutable system-design diagram model with built-in rendering helpers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str | None = None
    direction: Direction = "LR"
    nodes: dict[str, Node] = Field(default_factory=dict)
    edges: list[Edge] = Field(default_factory=list)
    groups: dict[str, Group] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    _default_renderer: str = PrivateAttr(default="svg")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in {"LR", "RL", "TB", "BT"}:
            raise ValueError("direction must be one of LR, RL, TB, BT")
        return value

    @model_validator(mode="after")
    def validate_edges(self) -> "Diagram":
        missing = [edge for edge in self.edges if edge.source not in self.nodes or edge.target not in self.nodes]
        if missing:
            labels = ", ".join(f"{edge.source}->{edge.target}" for edge in missing)
            raise ValueError(f"edges reference unknown nodes: {labels}")
        return self

    def add_node(
        self,
        id: str,
        label: str | None = None,
        *,
        kind: str = "component",
        group: str | None = None,
        description: str | None = None,
        **metadata: Any,
    ) -> "Diagram":
        node = Node(id=id, label=label, kind=kind, group=group, description=description, metadata=metadata)
        if node.id in self.nodes:
            raise ValueError(f"node already exists: {node.id}")
        self.nodes[node.id] = node
        if group is not None and group not in self.groups:
            self.add_group(group)
        return self

    node = add_node

    def add_group(self, id: str, label: str | None = None, **metadata: Any) -> "Diagram":
        group = Group(id=id, label=label, metadata=metadata)
        if group.id in self.groups:
            if label is not None:
                self.groups[group.id].label = label
            self.groups[group.id].metadata.update(metadata)
        else:
            self.groups[group.id] = group
        return self

    group = add_group

    def add_edge(
        self,
        source: str,
        target: str,
        label: str | None = None,
        *,
        protocol: str | None = None,
        bidirectional: bool = False,
        **metadata: Any,
    ) -> "Diagram":
        if source not in self.nodes:
            raise ValueError(f"unknown source node: {source}")
        if target not in self.nodes:
            raise ValueError(f"unknown target node: {target}")
        self.edges.append(
            Edge(
                source=source,
                target=target,
                label=label,
                protocol=protocol,
                bidirectional=bidirectional,
                metadata=metadata,
            )
        )
        return self

    connect = add_edge

    def render(self, renderer: str = "svg", **options: Any) -> Any:
        render = kernel.get("renderers", renderer)
        return render(self, **options)

    def layout(self, layout: str = "dag", **options: Any) -> Layout:
        layouter = kernel.get("layouts", layout)
        return layouter(self, **options)

    def to_svg(self, **options: Any) -> str:
        return self.render("svg", **options)

    def to_mermaid(self, **options: Any) -> str:
        return self.render("mermaid", **options)

    def to_html(self, **options: Any) -> str:
        svg = self.to_svg(**options)
        return f'<div class="silco-diagram">{svg}</div>'

    def to_pdf(self, **options: Any) -> bytes:
        if "pdf" not in kernel.names("renderers"):
            importlib.import_module("silco.plugins.pdf")
        return self.render("pdf", **options)

    def save_pdf(self, path: str | PathLike[str], **options: Any) -> Path:
        pdf = importlib.import_module("silco.plugins.pdf")
        return pdf.save_pdf(self, path, **options)

    def _repr_svg_(self) -> str:
        return self.to_svg()

    def _repr_html_(self) -> str:
        return self.to_html()

    def __str__(self) -> str:
        name = f" {self.title!r}" if self.title else ""
        return f"<Diagram{name}: {len(self.nodes)} nodes, {len(self.edges)} edges>"

    __repr__ = __str__


def diagram(title: str | None = None, *, direction: Direction = "LR") -> Diagram:
    return Diagram(title=title, direction=direction)


def dag_layout(diagram: Diagram, **options: Any) -> Layout:
    config = RenderConfig(direction=diagram.direction, **options)
    ranks = _rank_nodes(diagram)
    horizontal = config.direction in {"LR", "RL"}
    positions: dict[str, PositionedNode] = {}

    max_rank = max((rank for rank, _ in ranks.values()), default=0)
    for node_id, (rank, index) in ranks.items():
        if config.direction == "RL":
            rank = max_rank - rank
        if config.direction == "BT":
            rank = max_rank - rank
        x = config.margin + rank * (config.node_width + config.rank_gap)
        y = config.margin + index * (config.node_height + config.node_gap)
        if not horizontal:
            x, y = y, x
        positions[node_id] = PositionedNode(
            node=diagram.nodes[node_id],
            x=float(x),
            y=float(y),
            width=float(config.node_width),
            height=float(config.node_height),
        )

    width = max((node.x + node.width + config.margin for node in positions.values()), default=config.width)
    height = max((node.y + node.height + config.margin for node in positions.values()), default=200)
    return Layout(nodes=positions, width=float(max(width, config.width)), height=float(height))


def grid_layout(diagram: Diagram, **options: Any) -> Layout:
    config = RenderConfig(direction=diagram.direction, **options)
    count = max(len(diagram.nodes), 1)
    columns = max(1, ceil(sqrt(count)))
    positions: dict[str, PositionedNode] = {}
    for idx, node in enumerate(diagram.nodes.values()):
        row, col = divmod(idx, columns)
        x = config.margin + col * (config.node_width + config.node_gap)
        y = config.margin + row * (config.node_height + config.node_gap)
        positions[node.id] = PositionedNode(
            node=node,
            x=float(x),
            y=float(y),
            width=float(config.node_width),
            height=float(config.node_height),
        )
    width = max((node.x + node.width + config.margin for node in positions.values()), default=config.width)
    height = max((node.y + node.height + config.margin for node in positions.values()), default=200)
    return Layout(nodes=positions, width=float(max(width, config.width)), height=float(height))


def svg_renderer(diagram: Diagram, **options: Any) -> str:
    config = RenderConfig(direction=diagram.direction, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    layout_name = options.get("layout", "dag")
    layout = diagram.layout(layout_name, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    title_height = 44 if diagram.title and config.title else 0
    height = layout.height + title_height
    canvas = _svg_canvas(layout.width, height, config)
    if diagram.title and config.title:
        canvas.text(diagram.title, 32, 30, class_="silco-title")

    for group in _group_bounds(diagram, layout, title_height):
        canvas.add(group)
    for edge in diagram.edges:
        canvas.add(_svg_edge(edge, layout, title_height))
    for item in layout.nodes.values():
        canvas.add(_svg_node(item, title_height))
    return canvas.to_svg()


def _rank_nodes(diagram: Diagram) -> dict[str, tuple[int, int]]:
    if not diagram.nodes:
        return {}
    incoming = {node_id: 0 for node_id in diagram.nodes}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in diagram.nodes}
    for edge in diagram.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target] += 1
    queue = deque(node_id for node_id, degree in incoming.items() if degree == 0)
    rank = {node_id: 0 for node_id in diagram.nodes}
    visited: list[str] = []
    while queue:
        current = queue.popleft()
        visited.append(current)
        for target in outgoing[current]:
            rank[target] = max(rank[target], rank[current] + 1)
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
    for node_id in diagram.nodes:
        if node_id not in visited:
            rank[node_id] = max(rank.values(), default=0) + 1
    counters: dict[int, int] = {}
    result: dict[str, tuple[int, int]] = {}
    for node_id in diagram.nodes:
        node_rank = rank[node_id]
        result[node_id] = (node_rank, counters.get(node_rank, 0))
        counters[node_rank] = counters.get(node_rank, 0) + 1
    return result


def mermaid_renderer(diagram: Diagram, **_: Any) -> str:
    lines = [f"flowchart {diagram.direction}"]
    rendered_groups: set[str] = set()

    def node_line(node: Node) -> str:
        label = _mermaid_escape(node.display_label)
        if node.kind == "database":
            return f"    {node.id}[(\"{label}\")]"
        if node.kind in {"queue", "storage"}:
            return f"    {node.id}[(\"{label}\")]"
        if node.kind == "actor":
            return f"    {node.id}([\"{label}\"])"
        if node.kind == "external":
            return f"    {node.id}{{\"{label}\"}}"
        return f"    {node.id}[\"{label}\"]"

    for group_id, group in diagram.groups.items():
        members = [node for node in diagram.nodes.values() if node.group == group_id]
        if not members:
            continue
        rendered_groups.add(group_id)
        lines.append(f"    subgraph {group_id}[\"{_mermaid_escape(group.display_label)}\"]")
        lines.extend(node_line(node) for node in members)
        lines.append("    end")

    for node in diagram.nodes.values():
        if node.group not in rendered_groups:
            lines.append(node_line(node))

    for edge in diagram.edges:
        label = f"|{_mermaid_escape(edge.display_label)}|" if edge.display_label else ""
        arrow = "<-->" if edge.bidirectional else "-->"
        lines.append(f"    {edge.source} {arrow}{label} {edge.target}")
    return "\n".join(lines)


def _svg_canvas(width: float, height: float, config: RenderConfig) -> Canvas:
    canvas = Canvas(width, height, {"role": "img"})
    canvas.style(f"""
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
""".strip())
    canvas.define(
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
        )
    )
    canvas.define(
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
        )
    )
    canvas.define(
        Element(
            "linearGradient",
            {"id": "canvasGradient", "x1": "0%", "y1": "0%", "x2": "0%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#f8fafc"}),
                Element("stop", {"offset": "100%", "stop-color": "#eef2ff"}),
            ),
        )
    )
    canvas.define(
        Element(
            "linearGradient",
            {"id": "packageGradient", "x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%"},
            children=(
                Element("stop", {"offset": "0%", "stop-color": "#e0f2fe", "stop-opacity": "0.92"}),
                Element("stop", {"offset": "100%", "stop-color": "#e2e8f0", "stop-opacity": "0.82"}),
            ),
        )
    )
    canvas.define(
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
        )
    )
    canvas.rect(0, 0, "100%", "100%", fill="url(#canvasGradient)", class_="silco-bg")
    return canvas


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


def _group_bounds(diagram: Diagram, layout: Layout, y_offset: float) -> Iterable[Element]:
    for group_id, group in diagram.groups.items():
        members = [layout.nodes[node.id] for node in diagram.nodes.values() if node.group == group_id and node.id in layout.nodes]
        if not members:
            continue
        x1 = min(item.x for item in members) - 16
        y1 = min(item.y for item in members) + y_offset - 26
        x2 = max(item.x + item.width for item in members) + 16
        y2 = max(item.y + item.height for item in members) + y_offset + 16
        yield (
            Element(
                "g",
                children=(
                    Element(
                        "path",
                        {
                            "class": "silco-group",
                            "d": _group_path(x1, y1, x2 - x1, y2 - y1),
                        },
                    ),
                    Element("text", {"class": "silco-group-label", "x": x1 + 20, "y": y1 + 14}, text=group.display_label),
                ),
            )
        )


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


def _mermaid_escape(value: str | None) -> str:
    return (value or "").replace('"', "'")


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
