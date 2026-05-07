from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from html import escape
from math import ceil, sqrt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from silco.core.config import RenderConfig
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

    def render(self, renderer: str = "svg", **options: Any) -> str:
        render = kernel.get("renderers", renderer)
        return render(self, **options)

    def layout(self, layout: str = "dag", **options: Any) -> Layout:
        layouter = kernel.get("layouts", layout)
        return layouter(self, **options)

    def to_svg(self, **options: Any) -> str:
        return self.render("svg", **options)

    def to_html(self, **options: Any) -> str:
        svg = self.to_svg(**options)
        return f'<div class="silco-diagram">{svg}</div>'

    def to_mermaid(self, **options: Any) -> str:
        return self.render("mermaid", **options)

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


def svg_renderer(diagram: Diagram, **options: Any) -> str:
    config = RenderConfig(direction=diagram.direction, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    layout_name = options.get("layout", "dag")
    layout = diagram.layout(layout_name, **{k: v for k, v in options.items() if k in RenderConfig.model_fields})
    title_height = 44 if diagram.title and config.title else 0
    height = layout.height + title_height
    parts = [_svg_header(layout.width, height, config)]
    if diagram.title and config.title:
        parts.append(f'<text x="32" y="30" class="silco-title">{escape(diagram.title)}</text>')

    for group in _group_bounds(diagram, layout, title_height):
        parts.append(group)
    for edge in diagram.edges:
        parts.append(_svg_edge(edge, layout, title_height))
    for item in layout.nodes.values():
        parts.append(_svg_node(item, title_height))
    parts.append("</svg>")
    return "\n".join(parts)


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


def _svg_header(width: float, height: float, config: RenderConfig) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" role="img">
<style>
.silco-bg {{ fill: #f8fafc; }}
.silco-title {{ font: 700 20px {config.font_family}; fill: #0f172a; }}
.silco-node {{ stroke: #334155; stroke-width: 1.5; filter: drop-shadow(0 8px 14px rgb(15 23 42 / .12)); }}
.silco-label {{ font: 700 14px {config.font_family}; fill: #0f172a; text-anchor: middle; dominant-baseline: middle; }}
.silco-kind {{ font: 600 10px {config.font_family}; fill: #475569; text-anchor: middle; text-transform: uppercase; }}
.silco-edge {{ stroke: #475569; stroke-width: 1.7; fill: none; marker-end: url(#arrow); }}
.silco-edge-label {{ font: 600 11px {config.font_family}; fill: #334155; text-anchor: middle; paint-order: stroke; stroke: #f8fafc; stroke-width: 5; }}
.silco-group {{ fill: #e0f2fe; stroke: #0284c7; stroke-dasharray: 7 5; stroke-width: 1.2; opacity: .72; }}
.silco-group-label {{ font: 700 12px {config.font_family}; fill: #075985; }}
</style>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/></marker></defs>
<rect class="silco-bg" width="100%" height="100%" rx="18"/>'''


def _svg_node(item: PositionedNode, y_offset: float) -> str:
    node = item.node
    x, y = item.x, item.y + y_offset
    rx = 18 if node.kind in {"actor", "external"} else 12
    fill = {
        "actor": "#fef3c7",
        "service": "#dbeafe",
        "database": "#dcfce7",
        "queue": "#fae8ff",
        "cache": "#ffedd5",
        "storage": "#ccfbf1",
        "external": "#fee2e2",
        "component": "#e2e8f0",
    }.get(node.kind, "#e2e8f0")
    label = escape(node.display_label)
    kind = escape(node.kind.upper())
    cy = y + item.height / 2
    return (
        f'<rect class="silco-node" x="{x:.1f}" y="{y:.1f}" width="{item.width:.1f}" height="{item.height:.1f}" rx="{rx}" fill="{fill}"/>'
        f'<text class="silco-label" x="{x + item.width / 2:.1f}" y="{cy - 6:.1f}">{label}</text>'
        f'<text class="silco-kind" x="{x + item.width / 2:.1f}" y="{cy + 18:.1f}">{kind}</text>'
    )


def _svg_edge(edge: Edge, layout: Layout, y_offset: float) -> str:
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
    label = ""
    if edge.display_label:
        label = f'<text class="silco-edge-label" x="{mx:.1f}" y="{(sy + ty) / 2 - 8:.1f}">{escape(edge.display_label)}</text>'
    reverse = " marker-start=\"url(#arrow)\"" if edge.bidirectional else ""
    return f'<path class="silco-edge" d="M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ty:.1f}, {tx:.1f} {ty:.1f}"{reverse}/>{label}'


def _group_bounds(diagram: Diagram, layout: Layout, y_offset: float) -> Iterable[str]:
    for group_id, group in diagram.groups.items():
        members = [layout.nodes[node.id] for node in diagram.nodes.values() if node.group == group_id and node.id in layout.nodes]
        if not members:
            continue
        x1 = min(item.x for item in members) - 16
        y1 = min(item.y for item in members) + y_offset - 26
        x2 = max(item.x + item.width for item in members) + 16
        y2 = max(item.y + item.height for item in members) + y_offset + 16
        yield (
            f'<rect class="silco-group" x="{x1:.1f}" y="{y1:.1f}" width="{x2 - x1:.1f}" height="{y2 - y1:.1f}" rx="18"/>'
            f'<text class="silco-group-label" x="{x1 + 14:.1f}" y="{y1 + 18:.1f}">{escape(group.display_label)}</text>'
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
