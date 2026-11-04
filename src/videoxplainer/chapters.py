"""Sections of a video: YouTube chapters, or topics detected from the text.

Auto-detection is lexical cohesion (TextTiling-style): compare the vocabulary
of the passages before and after each gap and cut where they differ most.
No LLM involved, so it is free and offline.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .budget import STOPWORDS
from .model import Chapter, Group, Paragraph, Segment
from .normalize import merge_paragraphs
from .textutil import words

Section = Tuple[float, str]  # (start seconds, title)

# Conversational filler that makes poor headings. Used for labels only, never for detection.
_LABEL_STOP = frozenset(
    "said says say think thing things people want wants going get gets got make makes made way one two "
    "three four five many much come comes came look looks see saw little lot kind sort actually basically "
    "something anything everything every still around back first even though maybe quite bit time "
    "good great really thing's let's".split()
)


def from_info(info: Dict[str, Any]) -> List[Chapter]:
    out: List[Chapter] = []
    for c in info.get("chapters") or []:
        try:
            out.append(Chapter(float(c["start_time"]), float(c.get("end_time") or 0), str(c.get("title") or "").strip()))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda c: c.start)


def _bag(text: str) -> Counter:
    return Counter(w for w in words(text) if len(w) > 3 and w not in STOPWORDS)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(c * b.get(w, 0) for w, c in a.items())
    na = math.sqrt(sum(c * c for c in a.values()))
    nb = math.sqrt(sum(c * c for c in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def detect_sections(
    paragraphs: List[Paragraph], target: Optional[int] = None, min_seconds: float = 480, min_gap_seconds: float = 90,
    min_z: float = 1.0,
    min_depth: float = 0.3,
) -> List[Section]:
    """Split into topical sections. Returns [] for short videos (not worth it)."""
    n = len(paragraphs)
    if n < 8 or paragraphs[-1].start - paragraphs[0].start < min_seconds:
        return []
    duration = paragraphs[-1].start - paragraphs[0].start
    target = target or max(3, min(12, round(duration / 360)))
    k = max(2, min(4, n // 10))
    bags = [_bag(p.text) for p in paragraphs]
    sims = {}
    for i in range(k, n - k + 1):
        sims[i] = _cosine(sum(bags[i - k : i], Counter()), sum(bags[i : i + k], Counter()))
    if len(sims) < 3:
        return []
    idx = sorted(sims)
    w = 3
    depth = {}
    for pos, i in enumerate(idx):
        left = max(sims[j] for j in idx[max(0, pos - w) : pos + 1])
        right = max(sims[j] for j in idx[pos : pos + w + 1])
        depth[i] = (left - sims[i]) + (right - sims[i])
    sep = max(2 * k, n // (2 * target))
    # Only cut at *significant* topic shifts: a valley must stand out from the typical
    # dip (min_z standard deviations above average), otherwise the video stays in one piece.
    values = list(depth.values())
    mean = sum(values) / len(values)
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    # ...and the vocabulary must really change: an absolute drop in cohesion as well, so a
    # uniform talk is never carved up just because some dips are bigger than others.
    floor = max(mean + min_z * std, min_depth)
    cuts: List[int] = []
    for i in sorted(depth, key=lambda g: depth[g], reverse=True):
        if depth[i] < floor or len(cuts) >= target - 1:
            break
        if all(abs(i - c) >= sep and abs(paragraphs[i].start - paragraphs[c].start) >= min_gap_seconds for c in cuts):
            cuts.append(i)
    if not cuts:
        return []
    cuts.sort()
    starts = [0] + cuts
    ends = cuts + [n]
    section_bags = [sum(bags[a:b], Counter()) for a, b in zip(starts, ends)]
    df: Counter = Counter()
    for sb in section_bags:
        df.update(set(sb))
    m = len(section_bags)
    sections: List[Section] = []
    for a, sb in zip(starts, section_bags):
        usable = [(w, c) for w, c in sb.items() if "'" not in w and w not in _LABEL_STOP]
        ranked = sorted(usable, key=lambda kv: kv[1] * math.log(1 + m / df[kv[0]]) ** 2, reverse=True)
        title = ", ".join(word for word, _ in ranked[:3]) or "section"
        sections.append((0.0 if a == 0 else paragraphs[a].start, title))
    return sections


def build_groups(segments: List[Segment], sections: List[Section]) -> List[Group]:
    """Cut cleaned segments into sections and paragraph-ise each one."""
    if not sections:
        return [Group("", 0.0, merge_paragraphs(segments))]
    sections = sorted(sections)
    if sections[0][0] > 0:
        sections.insert(0, (0.0, "Intro"))
    groups: List[Group] = []
    for i, (start, title) in enumerate(sections):
        end = sections[i + 1][0] if i + 1 < len(sections) else float("inf")
        segs = [s for s in segments if start <= s.start < end]
        if segs:
            groups.append(Group(title, start, merge_paragraphs(segs)))
    return groups
