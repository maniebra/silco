from pydantic import BaseModel

from silco.core.models.node import Node


class PositionedNode(BaseModel):
    node: Node
    x: float
    y: float
    width: float
    height: float
