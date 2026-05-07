from __future__ import annotations

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


class Edge(BaseModel):
    """A directed relationship between two nodes."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    label: str | None = None
    protocol: str | None = None
    bidirectional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "target")
    @classmethod
    def normalize_endpoint(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("edge endpoint cannot be empty")
        return value

    @property
    def display_label(self) -> str | None:
        if self.label and self.protocol:
            return f"{self.label} ({self.protocol})"
        return self.label or self.protocol


class Group(BaseModel):
    """A visual boundary for a set of related nodes."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("group id cannot be empty")
        return value

    @property
    def display_label(self) -> str:
        return self.label or self.id
