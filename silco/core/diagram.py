from __future__ import annotations

import importlib
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from silco.core.kernel import kernel
from silco.core.models.edge import Edge
from silco.core.models.flow import Flow
from silco.core.models.group import Group
from silco.core.models.node import Node

if TYPE_CHECKING:
    from silco.core.layout import Layout

Direction = Literal["LR", "RL", "TB", "BT"]


class Diagram(BaseModel):
    """Mutable system-design diagram model with kernel-backed rendering."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str | None = None
    direction: Direction = "LR"
    nodes: dict[str, Node] = Field(default_factory=dict)
    edges: list[Edge] = Field(default_factory=list)
    flows: list[Flow] = Field(default_factory=list)
    groups: dict[str, Group] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    _default_renderer: str = PrivateAttr(default="svg")

    @model_validator(mode="after")
    def validate_relations(self) -> "Diagram":
        for collection_name, relations in (("edges", self.edges), ("flows", self.flows)):
            missing = [
                f"{relation.source}->{relation.target}"
                for relation in relations
                if relation.source not in self.nodes or relation.target not in self.nodes
            ]
            if missing:
                joined = ", ".join(missing)
                raise ValueError(f"{collection_name} reference unknown nodes: {joined}")
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
        if node.group and node.group not in self.groups:
            self.add_group(node.group)
        return self

    node = add_node

    def add_group(self, id: str, label: str | None = None, **metadata: Any) -> "Diagram":
        group = Group(id=id, label=label, metadata=metadata)
        current = self.groups.get(group.id)
        if current is None:
            self.groups[group.id] = group
            return self
        if label is not None:
            current.label = label
        current.metadata.update(metadata)
        return self

    group = add_group

    def _append_relation(
        self,
        relation_type: type[Edge] | type[Flow],
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
        relation = relation_type(
            source=source,
            target=target,
            label=label,
            protocol=protocol,
            bidirectional=bidirectional,
            metadata=metadata,
        )
        collection = self.flows if relation_type is Flow else self.edges
        collection.append(relation)
        return self

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
        return self._append_relation(
            Edge,
            source,
            target,
            label,
            protocol=protocol,
            bidirectional=bidirectional,
            **metadata,
        )

    connect = add_edge

    def add_flow(
        self,
        source: str,
        target: str,
        label: str | None = None,
        *,
        protocol: str | None = None,
        bidirectional: bool = False,
        **metadata: Any,
    ) -> "Diagram":
        return self._append_relation(
            Flow,
            source,
            target,
            label,
            protocol=protocol,
            bidirectional=bidirectional,
            **metadata,
        )

    flow = add_flow

    def render(self, renderer: str | None = None, **options: Any) -> Any:
        render_name = renderer or self._default_renderer
        return kernel.get("renderers", render_name)(self, **options)

    def layout(self, layout: str = "dag", **options: Any) -> Layout:
        return kernel.get("layouts", layout)(self, **options)

    def to_svg(self, **options: Any) -> str:
        return self.render("svg", **options)

    def to_mermaid(self, **options: Any) -> str:
        return self.render("mermaid", **options)

    def to_html(self, **options: Any) -> str:
        return f'<div class="silco-diagram">{self.to_svg(**options)}</div>'

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
        return f"<Diagram{name}: {len(self.nodes)} nodes, {len(self.edges) + len(self.flows)} relations>"

    __repr__ = __str__


def diagram(title: str | None = None, *, direction: Direction = "LR") -> Diagram:
    return Diagram(title=title, direction=direction)
