"""Evidence check: do the quotes an LLM cited actually appear in the video?"""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Tuple

from .model import Segment, fmt_ts
from .textutil import words

SUPPORTED = 0.85
WEAK = 0.60


def _words(text: str) -> List[str]:
    return words(text)


def build_index(segments: List[Segment]) -> Tuple[List[str], List[float]]:
    words: List[str] = []
    times: List[float] = []
    for seg in segments:
        for w in _words(seg.text):
            words.append(w)
            times.append(seg.start)
    return words, times


def _best_match(quote: List[str], words: List[str]) -> Tuple[float, int]:
    n = len(quote)
    if n == 0 or len(words) < 1:
        return 0.0, 0
    for i in range(len(words) - n + 1):  # exact contiguous match first
        if words[i : i + n] == quote:
            return 1.0, i
    qset = set(quote)
    step = max(1, n // 4)
    starts = sorted({max(0, (i // step) * step - step) for i, w in enumerate(words) if w in qset})
    best, best_at = 0.0, 0
    for s in starts:
        for size in (n, n + max(1, n // 5)):
            window = words[s : s + size]
            if not window:
                continue
            ratio = difflib.SequenceMatcher(None, quote, window, autojunk=False).ratio()
            if ratio > best:
                best, best_at = ratio, s
    return best, best_at


def verify_claims(payload: Any, segments: List[Segment], video_id: str = "") -> Dict[str, Any]:
    items = payload.get("actions", []) if isinstance(payload, dict) else list(payload or [])
    words, times = build_index(segments)
    report: List[Dict[str, Any]] = []
    counts = {"supported": 0, "weak": 0, "unsupported": 0, "no_quote": 0}
    for idx, item in enumerate(items):
        quote = _words(str(item.get("quote", ""))) if isinstance(item, dict) else []
        entry: Dict[str, Any] = {"index": idx, "action": (item.get("action") if isinstance(item, dict) else str(item))}
        if len(quote) < 3:
            entry["status"] = "no_quote"
        else:
            score, at = _best_match(quote, words)
            status = "supported" if score >= SUPPORTED else "weak" if score >= WEAK else "unsupported"
            entry.update(status=status, score=round(score, 2))
            if status != "unsupported" and times:
                t = times[min(at, len(times) - 1)]
                entry["matched_at"] = fmt_ts(t)
                if video_id:
                    entry["link"] = f"https://youtu.be/{video_id}?t={int(t)}"
                claimed = item.get("t") if isinstance(item, dict) else None
                if isinstance(claimed, (int, float)) and abs(claimed - t) > 60:
                    entry["note"] = "claimed timestamp differs from where the quote appears"
        counts[entry["status"]] += 1
        report.append(entry)
    return {"checked": len(items), **counts, "items": report}
