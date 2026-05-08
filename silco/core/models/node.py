from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NodeKind = Literal[
    "actor",
    "service",
    "database",
    "queue",
    "cache",
    "storage",
    "external",
    "component",
]


class Node(BaseModel):
    """A system component that can be rendered in a diagram."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str | None = None
    kind: NodeKind = "component"
    description: str | None = None
    group: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "group")
    @classmethod
    def normalize_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("identifier cannot be empty")
        return value

    @property
    def display_label(self) -> str:
        return self.label or self.id

