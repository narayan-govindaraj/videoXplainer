"""Token budgeting: fit a transcript into N tokens, spread across sections.

Extractive and lossy by design: when the transcript exceeds the budget we keep
the highest-information passages from every section of the video (TF-IDF
within the transcript), in original order, with their timestamps. Sections are
YouTube chapters when the video has them, otherwise auto-detected topics.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Set, Tuple

from .model import Group, Paragraph
from .textutil import words

STOPWORDS = frozenset(
    "the and but for with from are was were been this that these those you your "
    "our their they them his her its not does did have has had will would can "
    "could just like really very about into than then there here what which who "
    "when how also because going know yeah okay right".split()
)
_TS_OVERHEAD = 4  # tokens for the "[mm:ss] " prefix
_MIN_WORDS = 8  # shorter fragments ("the", "that went viral") are noise
_MIN_INFO = 4  # ...and so are passages with fewer informative words than this
HEADING_COST = 12  # tokens reserved per section heading


def estimate_tokens(text: str) -> int:
    """Cheap, deliberately conservative estimate; fine for budgeting, not billing.

    Latin text is about 4 characters per token. Other scripts (Tamil, Hindi,
    Cyrillic, CJK...) need many more tokens per character, so non-ASCII
    characters are counted at 1.5 per token to stay under a budget.
    """
    if not text:
        return 0
    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    return math.ceil(ascii_chars / 4 + (len(text) - ascii_chars) / 1.5)


def _cost(text: str) -> int:
    return estimate_tokens(text) + _TS_OVERHEAD


def informative_words(text: str) -> List[str]:
    return [w for w in words(text) if len(w) > 2 and w not in STOPWORDS]


def _eligible(text: str) -> bool:
    return len(text.split()) >= _MIN_WORDS and len(informative_words(text)) >= _MIN_INFO


def _units(paragraphs: List[Paragraph], max_words: int = 60) -> List[Paragraph]:
    units: List[Paragraph] = []
    for para in paragraphs:
        buf: List[str] = []
        for sentence in re.split(r"(?<=[.!?])\s+", para.text):
            words = sentence.split()
            if not words:
                continue
            if len(words) > max_words:  # unpunctuated auto-captions
                if buf:
                    units.append(Paragraph(para.start, " ".join(buf)))
                    buf = []
                for i in range(0, len(words), max_words):
                    units.append(Paragraph(para.start, " ".join(words[i : i + max_words])))
                continue
            if buf and len(buf) + len(words) > max_words:
                units.append(Paragraph(para.start, " ".join(buf)))
                buf = []
            buf.extend(words)
        if buf:
            units.append(Paragraph(para.start, " ".join(buf)))
    return units


def _scores(units: List[Paragraph]) -> List[float]:
    tokens = [informative_words(u.text) for u in units]
    df: Counter = Counter()
    for toks in tokens:
        df.update(set(toks))
    n = len(units)
    out = []
    for toks in tokens:
        tf = Counter(toks)
        raw = sum(c * math.log(1 + n / df[w]) for w, c in tf.items())
        out.append(raw / (max(len(toks), 1) ** 0.7))
    return out


def _select(indices: List[int], alloc: float, scores, costs, eligible: Set[int], max_buckets: int) -> Tuple[Set[int], int]:
    """Pick the best units within `alloc` tokens, spread over the index range."""
    # never pad a section with junk: a section with nothing worth quoting is simply dropped
    cand = [i for i in indices if i in eligible]
    if not cand or alloc <= 0:
        return set(), 0
    avg = sum(costs[i] for i in cand) / len(cand)
    # With a small allocation we cannot afford many slices: use as many as fit.
    buckets = max(1, min(max_buckets, int(alloc // max(avg, 1))))
    per = math.ceil(len(cand) / buckets)
    share = alloc / buckets
    chosen: Set[int] = set()
    spent = 0
    for k in range(buckets):
        part = cand[k * per : (k + 1) * per]
        used = 0
        for rank, i in enumerate(sorted(part, key=lambda j: scores[j], reverse=True)):
            # every slice gets its single best unit, so coverage never collapses
            if (rank == 0 or used + costs[i] <= share) and spent + costs[i] <= alloc:
                chosen.add(i)
                used += costs[i]
                spent += costs[i]
    for i in sorted((j for j in cand if j not in chosen), key=lambda j: scores[j], reverse=True):
        if spent + costs[i] <= alloc:
            chosen.add(i)
            spent += costs[i]
    return chosen, spent


def _merge(units: List[Paragraph], chosen_sorted: List[int]) -> List[Paragraph]:
    merged: List[Paragraph] = []
    prev = None
    for i in chosen_sorted:
        if prev is not None and i == prev + 1:
            merged[-1] = Paragraph(merged[-1].start, merged[-1].text + " " + units[i].text)
        else:
            merged.append(Paragraph(units[i].start, units[i].text))
        prev = i
    return merged


def fit_groups(groups: List[Group], budget: int, heading_cost: int = 0, max_buckets: int = 6) -> Tuple[List[Group], Dict[str, object]]:
    """Condense sections to `budget` tokens; each section keeps a share of it."""
    units: List[Paragraph] = []
    owner: List[int] = []
    for gi, g in enumerate(groups):
        for u in _units(g.paragraphs):
            units.append(u)
            owner.append(gi)
    costs = [_cost(u.text) for u in units]
    full = sum(costs) + heading_cost * len(groups)
    stats: Dict[str, object] = {"full_tokens": full, "budget": budget, "trimmed": False, "sections": len(groups)}
    if budget <= 0 or full <= budget:
        stats["kept_tokens"] = full
        return groups, stats

    scores = _scores(units)
    eligible = {i for i, u in enumerate(units) if _eligible(u.text)} or set(range(len(units)))
    members = [[i for i, o in enumerate(owner) if o == gi] for gi in range(len(groups))]
    gcost = [sum(costs[i] for i in m) for m in members]
    avail = budget - heading_cost * len(groups)

    # Floor: roughly one average passage per section, biggest sections first while budget lasts.
    floors = [0] * len(groups)
    remaining = avail
    for gi in sorted(range(len(groups)), key=lambda g: gcost[g], reverse=True):
        if not members[gi]:
            continue
        floor = min(gcost[gi], math.ceil(gcost[gi] / len(members[gi])))
        if floor <= remaining:
            floors[gi] = floor
            remaining -= floor
    live = [gi for gi in range(len(groups)) if floors[gi]]
    live_cost = sum(gcost[g] for g in live) or 1
    chosen: Set[int] = set()
    spent = 0
    for gi in live:
        alloc = floors[gi] + remaining * gcost[gi] / live_cost  # rest is proportional to length
        c, s = _select(members[gi], alloc, scores, costs, eligible, max_buckets)
        chosen |= c
        spent += s
    live_set = set(live)
    for i in sorted((j for j in eligible if j not in chosen and owner[j] in live_set), key=lambda j: scores[j], reverse=True):
        if spent + costs[i] <= avail:
            chosen.add(i)
            spent += costs[i]

    out: List[Group] = []
    for gi in live:
        picked = sorted(i for i in chosen if owner[i] == gi)
        if picked:
            out.append(Group(groups[gi].title, groups[gi].start, _merge(units, picked)))
    stats.update(
        trimmed=True,
        kept_tokens=spent + heading_cost * len(out),
        kept_ratio=round(spent / max(full, 1), 2),
        sections_kept=len(out),
    )
    return out, stats


def fit(paragraphs: List[Paragraph], budget: int, buckets: int = 8) -> Tuple[List[Paragraph], Dict[str, object]]:
    """Flat convenience wrapper: one section spread over the whole timeline."""
    out, stats = fit_groups([Group("", 0.0, paragraphs)], budget, max_buckets=buckets)
    return [p for g in out for p in g.paragraphs], stats
