from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RenderConfig(BaseModel):
    """Rendering knobs shared by built-in renderers."""

    model_config = ConfigDict(extra="forbid")

    direction: str = "LR"
    width: int = Field(default=960, ge=320)
    node_width: int = Field(default=168, ge=80)
    node_height: int = Field(default=84, ge=48)
    rank_gap: int = Field(default=72, ge=40)
    node_gap: int = Field(default=48, ge=20)
    margin: int = Field(default=32, ge=0)
    style: str = Field(default="modern", min_length=1)
    font_family: str = "ui-sans-serif, Segoe UI, sans-serif"
    title: bool = True
