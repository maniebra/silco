from __future__ import annotations

import importlib
from collections import deque
from collections.abc import Iterable
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator

from silco.core.models.edge import Edge
from silco.core.models.group import Group
from silco.core.renderers.base.graphics import Element
from silco.core.kernel import kernel
from silco.core.models.node import Node

if TYPE_CHECKING:
    from silco.core.renderers.base.layout import Layout

Direction = Literal["LR", "RL", "TB", "BT"]




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


def group_bounds(diagram: Diagram, layout: Layout, y_offset: float) -> Iterable[Element]:
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
