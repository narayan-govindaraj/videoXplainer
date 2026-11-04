"""End-to-end self-check: does the whole pipeline behave on THIS video?

No model involved. We check invariants (budget respected, every section
represented, timestamps in order) and run a round-trip on the verifier:
real passages from the transcript must be "supported", and the same passages
with their words reversed must not be.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .budget import HEADING_COST, fit_groups
from .chapters import detect_sections
from .model import Segment, Transcript
from .normalize import clean_segments, merge_paragraphs
from .pipeline import build_sections
from .verify import verify_claims


@dataclass
class Check:
    name: str
    ok: Optional[bool]  # None = skipped
    detail: str = ""


def boundary_agreement(real: List[float], auto: List[float], tol: float = 60.0) -> Tuple[int, int, int, int]:
    """(auto cuts near a real chapter start, auto cuts, real starts recovered, real starts)."""
    real = [r for r in real if r > 0]
    auto = [a for a in auto if a > 0]
    hit_auto = sum(1 for a in auto if any(abs(a - r) <= tol for r in real))
    hit_real = sum(1 for r in real if any(abs(a - r) <= tol for a in auto))
    return hit_auto, len(auto), hit_real, len(real)


def _passages(segs: List[Segment], n: int = 5, size: int = 14) -> List[str]:
    words = [w for s in segs for w in s.text.split()]
    if len(words) < n * size * 2:
        return []
    step = len(words) // n
    return [" ".join(words[i * step + step // 3 : i * step + step // 3 + size]) for i in range(n)]


def run_checks(tr: Transcript, budget: int = 2000) -> List[Check]:
    checks: List[Check] = []
    kind = "auto" if tr.is_auto else "uploaded"
    checks.append(Check("captions parsed", len(tr.segments) >= 5, f"{len(tr.segments)} cues, {tr.language or '?'} ({kind})"))
    cleaned, groups, source = build_sections(tr)
    checks.append(Check("text survives cleaning", len(cleaned) >= 3, f"{len(cleaned)} segments after cleanup"))
    checks.append(Check("sections found", len(groups) >= 1, f"{len(groups)} section{'' if len(groups) == 1 else 's'} (source: {source})"))
    if tr.chapters and len(tr.chapters) > 1:  # real-data benchmark of topic auto-detection (information only)
        auto = detect_sections(merge_paragraphs(cleaned))
        if auto:
            ha, na, hr, nr = boundary_agreement([c.start for c in tr.chapters], [a[0] for a in auto])
            detail = f"{ha} of {na} auto-detected cuts fall within 60s of a real chapter start; {hr} of {nr} real chapter starts recovered"
        else:
            detail = "auto-detection saw no significant topic shifts and kept the video in one piece"
        checks.append(Check("auto-detect vs YouTube chapters (info only)", True, detail))

    heading = HEADING_COST if source != "none" else 0
    kept, stats = fit_groups(groups, budget, heading_cost=heading)
    kept_tokens = int(stats["kept_tokens"])
    checks.append(Check("budget respected", budget <= 0 or kept_tokens <= budget, f"~{kept_tokens} tokens kept of ~{stats['full_tokens']} (budget {budget})"))
    if stats.get("trimmed"):
        checks.append(
            Check("sections represented", int(stats["sections_kept"]) >= 0.8 * int(stats["sections"]),
                  f"{stats['sections_kept']} of {stats['sections']} sections kept")
        )
    starts = [p.start for g in kept for p in g.paragraphs]
    checks.append(Check("timestamps in order", starts == sorted(starts), f"{len(starts)} passages"))

    passages = _passages(cleaned)
    if not passages:
        checks.append(Check("verify round-trip", None, "transcript too short to sample"))
        return checks
    real = verify_claims([{"quote": q} for q in passages], cleaned, tr.video_id)
    checks.append(Check("real quotes are supported", real["supported"] == len(passages), f"{real['supported']}/{len(passages)} supported"))
    fake = verify_claims([{"quote": " ".join(reversed(q.split()))} for q in passages], cleaned, tr.video_id)
    checks.append(Check("scrambled quotes are rejected", fake["supported"] == 0, f"{fake['supported']}/{len(passages)} wrongly supported"))
    return checks
