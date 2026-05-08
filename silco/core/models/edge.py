from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


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

