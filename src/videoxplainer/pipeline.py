"""Transcript -> sections (chapters or detected topics), ready for budgeting."""

from __future__ import annotations

from typing import List, Tuple

from .chapters import build_groups, detect_sections
from .model import Group, Segment, Transcript
from .normalize import clean_segments, merge_paragraphs


def build_sections(tr: Transcript, use_video_chapters: bool = True) -> Tuple[List[Segment], List[Group], str]:
    """Returns (cleaned segments, sections, source) with source in video|auto|none."""
    cleaned = clean_segments(tr.segments)
    if tr.chapters and use_video_chapters:
        sections = [(c.start, c.title or f"Chapter {i + 1}") for i, c in enumerate(tr.chapters)]
        source = "video"
    else:
        sections = detect_sections(merge_paragraphs(cleaned))
        source = "auto" if sections else "none"
    return cleaned, build_groups(cleaned, sections), source
