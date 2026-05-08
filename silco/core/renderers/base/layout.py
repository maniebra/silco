from __future__ import annotations

from math import ceil, sqrt
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from silco.core.renderers.base.diagram import _rank_nodes
from silco.core.renderers.base.positioned_node import PositionedNode
from silco.core.renderers.base.config import RenderConfig

if TYPE_CHECKING:
    from silco.core.renderers.base.diagram import Diagram


class Layout(BaseModel):
    nodes: dict[str, PositionedNode]
    width: float
    height: float


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
    row_gap = config.node_gap * 1.5
    positions: dict[str, PositionedNode] = {}
    for idx, node in enumerate(diagram.nodes.values()):
        row, col = divmod(idx, columns)
        x = config.margin + col * (config.node_width + config.node_gap)
        y = config.margin + row * (config.node_height + row_gap)
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
