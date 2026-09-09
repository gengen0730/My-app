from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryEntry(BaseModel):
    actor: Literal["USER", "AI"]
    bars: list[str] = Field(min_length=1, max_length=4)


class ProcessChunkResponse(BaseModel):
    transcript: str
    bars: list[str] = Field(min_length=4, max_length=4)
    audio_urls: list[str] = Field(min_length=4, max_length=4)
