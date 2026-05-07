from __future__ import annotations

from typing import Any

from silco.core.renderers.diagram import Diagram, Node
from silco.core.kernel import SilcoKernel, kernel

PLUGIN_CATEGORY = "renderers"
PLUGIN_NAME = "mermaid"
PLUGIN_DESCRIPTION = "Mermaid flowchart text renderer."
PLUGIN_TAGS = ("builtin", "renderer", "text")


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


def _mermaid_escape(value: str | None) -> str:
    return (value or "").replace('"', "'")


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        mermaid_renderer,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


register_plugins(kernel)
