from __future__ import annotations

from collections import deque
from math import ceil, sqrt
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from silco.core.positioned_node import PositionedNode
from silco.core.render_config import RenderConfig

if TYPE_CHECKING:
    from silco.core.diagram import Diagram

MAX_COLUMNS_PER_ROW = 4


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

    wrapped_lines: dict[str, int] = {}
    slot_in_line: dict[str, tuple[int, int, int]] = {}
    if horizontal:
        ordered_nodes = _ordered_nodes_for_horizontal_layout(ranks, config.direction, max_rank)
        wrapped_lines = _wrapped_lines(diagram, ordered_nodes)
        slot_in_line = _slot_assignments(ordered_nodes, wrapped_lines)

    for node_id, (rank, index) in ranks.items():
        rank = _flip_rank(rank, config.direction, max_rank)
        if horizontal:
            line, slot, count = slot_in_line[node_id]
            x = _horizontal_slot_x(config, slot, count)
            y = (
                config.margin
                + line * (config.node_height + config.node_gap * 2)
                + index * (config.node_height + config.node_gap)
            )
        else:
            x = config.margin + rank * (config.node_width + config.rank_gap)
            y = config.margin + index * (config.node_height + config.node_gap)
            x, y = y, x
        positions[node_id] = PositionedNode(
            node=diagram.nodes[node_id],
            x=float(x),
            y=float(y),
            width=float(config.node_width),
            height=float(config.node_height),
        )

    _separate_overlapping_groups(diagram, positions)
    width = max(
        (node.x + node.width + config.margin for node in positions.values()),
        default=config.width,
    )
    height = max(
        (node.y + node.height + config.margin for node in positions.values()),
        default=200,
    )
    return Layout(nodes=positions, width=float(max(width, config.width)), height=float(height))


def _line_override(metadata: dict[str, Any]) -> int | None:
    raw = metadata.get("line")
    if raw is None:
        return None
    try:
        line = int(raw)
    except (TypeError, ValueError):
        return None
    return max(line, 0)


def _rank_nodes(diagram: Diagram) -> dict[str, tuple[int, int]]:
    if not diagram.nodes:
        return {}

    incoming = {node_id: 0 for node_id in diagram.nodes}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in diagram.nodes}
    for relation in (*diagram.edges, *diagram.flows):
        outgoing[relation.source].append(relation.target)
        incoming[relation.target] += 1

    queue = deque(node_id for node_id, count in incoming.items() if count == 0)
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

    highest_rank = max(rank.values(), default=0)
    for node_id in diagram.nodes:
        if node_id not in visited:
            highest_rank += 1
            rank[node_id] = highest_rank

    counters: dict[int, int] = {}
    result: dict[str, tuple[int, int]] = {}
    for node_id in diagram.nodes:
        node_rank = rank[node_id]
        result[node_id] = (node_rank, counters.get(node_rank, 0))
        counters[node_rank] = counters.get(node_rank, 0) + 1
    return result


def _ordered_nodes_for_horizontal_layout(
    ranks: dict[str, tuple[int, int]], direction: str, max_rank: int
) -> list[tuple[str, int, int, int]]:
    ordered_nodes = [
        (node_id, _flip_rank(rank, direction, max_rank), index, seq)
        for seq, (node_id, (rank, index)) in enumerate(ranks.items())
    ]
    ordered_nodes.sort(key=lambda item: (item[1], item[2], item[3]))
    return ordered_nodes


def _wrapped_lines(diagram: Diagram, ordered_nodes: list[tuple[str, int, int, int]]) -> dict[str, int]:
    wrapped: dict[str, int] = {}
    auto_line = 0
    auto_in_line = 0
    for node_id, _, _, _ in ordered_nodes:
        forced_line = _line_override(diagram.nodes[node_id].metadata)
        if forced_line is not None:
            wrapped[node_id] = forced_line
            continue
        wrapped[node_id] = auto_line
        auto_in_line += 1
        if auto_in_line >= MAX_COLUMNS_PER_ROW:
            auto_line += 1
            auto_in_line = 0
    return wrapped


def _slot_assignments(
    ordered_nodes: list[tuple[str, int, int, int]], wrapped_lines: dict[str, int]
) -> dict[str, tuple[int, int, int]]:
    line_members: dict[int, list[tuple[str, int, int, int]]] = {}
    for node in ordered_nodes:
        line_members.setdefault(wrapped_lines[node[0]], []).append(node)
    slot_map: dict[str, tuple[int, int, int]] = {}
    for line, members in line_members.items():
        members.sort(key=lambda item: (item[1], item[2], item[3]))
        count = len(members)
        for slot, (node_id, _, _, _) in enumerate(members):
            slot_map[node_id] = (line, slot, count)
    return slot_map


def _flip_rank(rank: int, direction: str, max_rank: int) -> int:
    if direction in {"RL", "BT"}:
        return max_rank - rank
    return rank


def _horizontal_slot_x(config: RenderConfig, slot: int, count: int) -> float:
    usable_width = max(config.width - 2 * config.margin - config.node_width, 0)
    if count <= 1:
        return config.margin + usable_width / 2
    return config.margin + usable_width / (count - 1) * slot


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
    _separate_overlapping_groups(diagram, positions)
    width = max(
        (node.x + node.width + config.margin for node in positions.values()),
        default=config.width,
    )
    height = max(
        (node.y + node.height + config.margin for node in positions.values()),
        default=200,
    )
    return Layout(nodes=positions, width=float(max(width, config.width)), height=float(height))


def _separate_overlapping_groups(
    diagram: Diagram,
    positions: dict[str, PositionedNode],
    padding: float = 22.0,
) -> None:
    group_members: dict[str, list[str]] = {}
    for node_id, node in diagram.nodes.items():
        if node.group and node_id in positions:
            group_members.setdefault(node.group, []).append(node_id)

    if len(group_members) < 2:
        return

    boxes: dict[str, tuple[float, float, float, float]] = {}
    for group_id, member_ids in group_members.items():
        member_positions = [positions[node_id] for node_id in member_ids]
        left = min(item.x for item in member_positions)
        top = min(item.y for item in member_positions)
        right = max(item.x + item.width for item in member_positions)
        bottom = max(item.y + item.height for item in member_positions)
        boxes[group_id] = (left, top, right, bottom)

    ordered_groups = sorted(boxes, key=lambda gid: (boxes[gid][1], boxes[gid][0]))
    placed: list[str] = []

    for group_id in ordered_groups:
        while True:
            current = boxes[group_id]
            shift_needed = 0.0
            for other_id in placed:
                other = boxes[other_id]
                if _rects_overlap(current, other):
                    candidate_shift = other[3] + padding - current[1]
                    shift_needed = max(shift_needed, candidate_shift)
            if shift_needed <= 0:
                break
            for node_id in group_members[group_id]:
                positions[node_id].y += shift_needed
            boxes[group_id] = (
                current[0],
                current[1] + shift_needed,
                current[2],
                current[3] + shift_needed,
            )
        placed.append(group_id)


def _rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    a_left, a_top, a_right, a_bottom = a
    b_left, b_top, b_right, b_bottom = b
    return not (
        a_right <= b_left
        or b_right <= a_left
        or a_bottom <= b_top
        or b_bottom <= a_top
    )
