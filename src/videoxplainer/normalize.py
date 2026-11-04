"""Transcript cleanup: noise, fillers, rolling-caption overlap, paragraphs."""

from __future__ import annotations

import html
import re
from typing import List, Tuple

from .model import Paragraph, Segment

_NOISE = re.compile(r"\[[A-Za-z ,'\-]{1,30}\]|\((?:music|applause|laughter)\)|[\u266a\u266b]+", re.I)
_SPEAKER = re.compile(r"(?:^|\s)>>+\s*")
_FILLER = re.compile(r"\b(?:u+m+|u+h+|er+m?|hmm+|mm+h?m*)\b[,.]?\s*", re.I)
_SPACE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = _NOISE.sub(" ", text)
    text = _SPEAKER.sub(" ", text)
    text = _FILLER.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


def _key(word: str) -> str:
    return word.lower().strip(".,!?;:\"'")


def dedupe_rolling(segments: List[Segment], tail_size: int = 40) -> List[Segment]:
    """Drop words that repeat the end of what was already emitted.

    Auto-captions show each line several times as it scrolls; this removes the
    overlap between consecutive cues (needs >= 2 matching words to count).
    """
    out: List[Segment] = []
    tail: List[str] = []
    for seg in segments:
        words = seg.text.split()
        if not words:
            continue
        cur = [_key(w) for w in words]
        prev = [_key(w) for w in tail]
        skip = 0
        for n in range(min(len(prev), len(cur)), 1, -1):
            if prev[-n:] == cur[:n]:
                skip = n
                break
        rest = words[skip:]
        if not rest:
            continue
        out.append(Segment(seg.start, " ".join(rest)))
        tail = (tail + rest)[-tail_size:]
    return out


def clean_segments(segments: List[Segment]) -> List[Segment]:
    cleaned = [Segment(s.start, clean_text(s.text)) for s in segments]
    return dedupe_rolling([s for s in cleaned if s.text])


def merge_paragraphs(segments: List[Segment], gap: float = 2.5, max_words: int = 80) -> List[Paragraph]:
    paras: List[Paragraph] = []
    buf: List[str] = []
    start = 0.0
    last = None
    count = 0
    for seg in segments:
        long_pause = last is not None and seg.start - last > gap
        sentence_end = bool(buf) and buf[-1][-1:] in ".!?"
        too_long = count >= max_words and (sentence_end or count >= int(max_words * 1.5))
        if buf and (long_pause or too_long):
            paras.append(Paragraph(start, " ".join(buf)))
            buf, count = [], 0
        if not buf:
            start = seg.start
        buf.append(seg.text)
        count += len(seg.text.split())
        last = seg.start
    if buf:
        paras.append(Paragraph(start, " ".join(buf)))
    return paras


def normalize(segments: List[Segment]) -> Tuple[List[Segment], List[Paragraph]]:
    cleaned = clean_segments(segments)
    return cleaned, merge_paragraphs(cleaned)
