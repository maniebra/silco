from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
