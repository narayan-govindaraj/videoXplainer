from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Segment:
    start: float
    text: str


@dataclass
class Paragraph:
    start: float
    text: str


@dataclass
class Chapter:
    start: float
    end: float
    title: str


@dataclass
class Group:
    """A section of the video (a chapter or auto-detected topic) with its paragraphs."""

    title: str
    start: float
    paragraphs: List[Paragraph] = field(default_factory=list)


@dataclass
class Transcript:
    video_id: str
    title: str = ""
    channel: str = ""
    duration: Optional[float] = None
    language: str = ""
    is_auto: bool = False
    segments: List[Segment] = field(default_factory=list)
    # None = unknown (cached before chapters were stored), [] = video has no chapters
    chapters: Optional[List[Chapter]] = None
    # True when the source file had no timestamps and times were estimated from word count
    timestamps_estimated: bool = False

    @property
    def is_local(self) -> bool:
        return self.video_id.startswith("local-")

    @property
    def url(self) -> str:
        return "" if self.is_local else f"https://youtu.be/{self.video_id}"


def fmt_ts(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
