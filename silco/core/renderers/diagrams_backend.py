from __future__ import annotations

import base64
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
from typing import Any

from silco.core.models.node import Node
from silco.core.renderers.base.config import RenderConfig


@dataclass(frozen=True)
class DiagramStyle:
    """Graphviz/Diagrams preset used by the microkernel SVG renderer."""

    name: str
    description: str
    graph_attr: dict[str, str] = field(default_factory=dict)
    node_attr: dict[str, str] = field(default_factory=dict)
    edge_attr: dict[str, str] = field(default_factory=dict)
    boundary_attr: dict[str, str] = field(default_factory=dict)
    node_kind_attr: dict[str, dict[str, str]] = field(default_factory=dict)
    curvestyle: str = "ortho"

    def graph_options(self, config: RenderConfig) -> dict[str, dict[str, str] | str]:
        graph_attr = {
            "pad": "0.3",
            "nodesep": "0.6",
            "ranksep": "0.9",
            "fontname": "Helvetica",
            "labelloc": "t",
            "labeljust": "l",
            "compound": "true",
            "bgcolor": "white",
            **self.graph_attr,
        }
        node_attr = {
            "fontname": "Helvetica",
            "fontsize": "12",
            **self.node_attr,
        }
        edge_attr = {
            "fontname": "Helvetica",
            "fontsize": "11",
            **self.edge_attr,
        }
        if not config.title:
            graph_attr["label"] = ""
        return {
            "graph_attr": graph_attr,
            "node_attr": node_attr,
            "edge_attr": edge_attr,
            "curvestyle": self.curvestyle,
        }

    def boundary_options(self) -> dict[str, str]:
        return {
            "bgcolor": "white",
            "margin": "16",
            "style": "dashed,rounded",
            "pencolor": "#aeb6be",
            **self.boundary_attr,
        }

    def node_options(self, node: Node) -> dict[str, str]:
        return {
            **self.node_kind_attr.get("default", {}),
            **self.node_kind_attr.get(node.kind, {}),
        }


def render_svg(diagram, config: RenderConfig, style: DiagramStyle) -> str:
    try:
        from diagrams import Diagram as DiagramsDiagram
        from diagrams import setcluster, setdiagram
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "SVG rendering requires the optional 'diagrams' and 'graphviz' packages. "
            "Install project dependencies first, for example: `uv sync` or `pip install diagrams graphviz`."
        ) from exc

    options = style.graph_options(config)
    graph = DiagramsDiagram(
        name=diagram.title or "",
        filename="silco-diagram",
        direction=config.direction,
        curvestyle=str(options["curvestyle"]),
        outformat="svg",
        show=False,
        graph_attr=dict(options["graph_attr"]),
        node_attr=dict(options["node_attr"]),
        edge_attr=dict(options["edge_attr"]),
    )
    setdiagram(graph)
    setcluster(None)
    try:
        nodes = _build_nodes(diagram, style)
        _build_edges(diagram, nodes)
        return _inline_local_images(graph.dot.pipe(format="svg", encoding="utf-8"))
    finally:
        setcluster(None)
        setdiagram(None)


def _build_nodes(diagram, style: DiagramStyle) -> dict[str, Any]:
    from diagrams.c4 import SystemBoundary

    grouped: dict[str, list[Node]] = defaultdict(list)
    ungrouped: list[Node] = []
    for node in diagram.nodes.values():
        if node.group:
            grouped[node.group].append(node)
        else:
            ungrouped.append(node)

    created: dict[str, Any] = {}
    for group_id, group in diagram.groups.items():
        members = grouped.get(group_id, [])
        if not members:
            continue
        with SystemBoundary(group.display_label, **style.boundary_options()):
            for node in members:
                created[node.id] = _make_node(node, style)

    for node in ungrouped:
        created[node.id] = _make_node(node, style)

    for group_id, members in grouped.items():
        if group_id in diagram.groups:
            continue
        for node in members:
            created[node.id] = _make_node(node, style)
    return created


def _make_node(node: Node, style: DiagramStyle) -> Any:
    from diagrams import Node as DiagramNode
    from diagrams.c4 import Container, Database, System

    description = node.description or str(node.metadata.get("description", "") or "")
    technology = str(node.metadata.get("technology", "") or _default_technology(node.kind))
    kwargs = {"nodeid": node.id, **style.node_options(node)}

    if node.kind == "actor":
        actor_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in {"fillcolor", "color", "style", "shape", "fontcolor", "width", "height"}
        }
        actor_image = _ensure_raster_template("actor")
        label = node.display_label if not description else f"{node.display_label}\n{description}"
        if actor_image is not None:
            return DiagramNode(
                label,
                image=str(actor_image),
                shape="none",
                fixedsize="false",
                imagescale="true",
                labelloc="b",
                imagepos="tc",
                imagesize="0.5,0.5!",
                margin="0,0",
                width="0.7",
                height="0.95",
                fillcolor="transparent",
                color="transparent",
                fontcolor="#0f172a",
                **actor_kwargs,
            )
        return DiagramNode(
            f"Actor\n{label}",
            shape="oval",
            style="rounded,filled",
            fillcolor="#bfdbfe",
            fontcolor="#0f172a",
            **actor_kwargs,
        )
    if node.kind == "external":
        return System(node.display_label, description=description or node.display_label, external=True, **kwargs)
    if node.kind == "database":
        return Database(node.display_label, technology=technology or "Database", description=description, **kwargs)

    node_type = {
        "service": "Service",
        "component": "Component",
        "queue": "Queue",
        "cache": "Cache",
        "storage": "Storage",
    }.get(node.kind, "Container")
    return Container(
        node.display_label,
        technology=technology,
        description=description,
        type=node_type,
        **kwargs,
    )


def _build_edges(diagram, nodes: dict[str, Any]) -> None:
    from diagrams.c4 import Relationship

    for relation in (*diagram.edges, *diagram.flows):
        label = relation.display_label or ""
        edge = Relationship(label) if label else Relationship()
        if relation.bidirectional:
            nodes[relation.source] << edge >> nodes[relation.target]
        else:
            nodes[relation.source] >> edge >> nodes[relation.target]


def _default_technology(kind: str) -> str:
    return {
        "service": "Service",
        "component": "Component",
        "queue": "Async Queue",
        "cache": "Cache",
        "storage": "Blob/Object Storage",
        "database": "Database",
        "external": "External System",
        "actor": "User",
    }.get(kind, kind.replace("_", " ").title())


def _template_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "templates" / "shapes" / filename


def _ensure_raster_template(stem: str) -> Path | None:
    png_path = _template_path(f"{stem}.png")
    if png_path.exists():
        return png_path

    svg_path = _template_path(f"{stem}.svg")
    if not svg_path.exists():
        return None

    commands = (
        ("rsvg-convert", "-o", str(png_path), str(svg_path)),
        ("inkscape", str(svg_path), "--export-type=png", f"--export-filename={png_path}"),
        ("magick", str(svg_path), str(png_path)),
        ("convert", str(svg_path), str(png_path)),
    )
    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        if png_path.exists():
            return png_path
    return None


def _inline_local_images(svg: str) -> str:
    pattern = re.compile(r'(xlink:href=")([^"]+)(")')

    def replace(match: re.Match[str]) -> str:
        prefix, raw_path, suffix = match.groups()
        path = Path(raw_path)
        if not path.is_absolute() or not path.exists():
            return match.group(0)
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        except OSError:
            return match.group(0)
        mime = "image/png" if path.suffix.lower() == ".png" else "image/svg+xml"
        return f'{prefix}data:{mime};base64,{encoded}{suffix}'

    return pattern.sub(replace, svg)
