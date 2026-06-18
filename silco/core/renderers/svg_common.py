"""Mermaid text rendering used by the built-in 'mermaid' renderer.

The module name is kept for backwards compatibility with imports such as
``from silco.core.renderers.svg_common import render_mermaid``.
"""

from __future__ import annotations

from silco.core.models.node import Node


def render_mermaid(diagram) -> str:
    """Render a diagram as a Mermaid flowchart string."""

    lines = [f"flowchart {diagram.direction}"]
    rendered_groups: set[str] = set()

    for group_id, group in diagram.groups.items():
        members = [node for node in diagram.nodes.values() if node.group == group_id]
        if not members:
            continue
        rendered_groups.add(group_id)
        lines.append(f'    subgraph {group_id}["{escape_mermaid(group.display_label)}"]')
        lines.extend(mermaid_node(node) for node in members)
        lines.append("    end")

    for node in diagram.nodes.values():
        if node.group not in rendered_groups:
            lines.append(mermaid_node(node))

    for relation in (*diagram.edges, *diagram.flows):
        label = f"|{escape_mermaid(relation.display_label)}|" if relation.display_label else ""
        arrow = "<-->" if relation.bidirectional else "-->"
        lines.append(f"    {relation.source} {arrow}{label} {relation.target}")

    return "\n".join(lines)


def mermaid_node(node: Node) -> str:
    """Render a single node as a Mermaid shape declaration."""

    label = escape_mermaid(node.display_label)
    if node.kind in {"database", "queue", "storage"}:
        return f'    {node.id}[("{label}")]'
    if node.kind == "actor":
        return f'    {node.id}(["{label}"])'
    if node.kind == "external":
        return f'    {node.id}{{"{label}"}}'
    return f'    {node.id}["{label}"]'


def escape_mermaid(value: str | None) -> str:
    """Escape characters that would break a Mermaid string literal."""

    return (value or "").replace('"', "'")
