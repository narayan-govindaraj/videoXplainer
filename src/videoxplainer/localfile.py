"""Load a transcript from a local file: .srt .vtt .json3 .txt .md

Lets you use videoxplainer on anything with text and (ideally) timestamps: meeting
exports, podcast transcripts, subtitles you downloaded yourself. No network.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import List, Tuple

from .captions import parse_json3, parse_vtt
from .fetch import FetchError
from .model import Segment, Transcript

MAX_BYTES = 20 * 1024 * 1024
SUPPORTED = (".srt", ".vtt", ".json3", ".json", ".txt", ".md")
_WORDS_PER_MINUTE = 150  # used to estimate times when a text file has none
_LINE_TS = re.compile(r"^\s*[\[(]?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,]\d{1,3})?[\])]?\s*[-\u2013\u2014:]?\s*(.*)$")


def _read(path: Path) -> str:
    if path.stat().st_size > MAX_BYTES:
        raise FetchError("invalid_input", f"{path.name} is larger than 20 MB.")
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def parse_text(text: str) -> Tuple[List[Segment], bool]:
    """Plain text -> (segments, has_real_timestamps)."""
    text = text.replace("\r\n", "\n")
    nonblank = [ln for ln in text.split("\n") if ln.strip()]
    hits = sum(1 for ln in nonblank if _LINE_TS.match(ln))
    if nonblank and hits >= max(3, len(nonblank) // 4):
        segs: List[Segment] = []
        for ln in nonblank:
            m = _LINE_TS.match(ln)
            if m:
                secs = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                segs.append(Segment(float(secs), m.group(4).strip()))
            elif segs:  # continuation of the previous timestamped line
                segs[-1] = Segment(segs[-1].start, f"{segs[-1].text} {ln.strip()}".strip())
        return [s for s in segs if s.text], True
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 3:
        paras = [re.sub(r"\s+", " ", ln).strip() for ln in nonblank]
    segs, t = [], 0.0
    for para in paras:
        segs.append(Segment(round(t, 1), para))
        t += len(para.split()) * 60.0 / _WORDS_PER_MINUTE
    return segs, False


def load_local(path_str: str) -> Transcript:
    path = Path(path_str).expanduser()
    if not path.is_file():
        raise FetchError("invalid_input", f"No such file: {path_str}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise FetchError("invalid_input", f"Unsupported file type '{suffix}'. Supported: {', '.join(SUPPORTED)}")
    text = _read(path)
    timed = True
    if suffix in (".srt", ".vtt"):
        segs = parse_vtt(text)
    elif suffix in (".json3", ".json"):
        try:
            segs = parse_json3(text)
        except (ValueError, AttributeError):
            raise FetchError("invalid_input", "That JSON isn't YouTube's json3 caption format.") from None
    else:
        segs, timed = parse_text(text)
    if not segs:
        raise FetchError("no_captions", f"No text found in {path.name}.")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return Transcript(
        video_id=f"local-{digest}",
        title=path.stem,
        channel="local file",
        duration=segs[-1].start,
        segments=segs,
        chapters=[],
        timestamps_estimated=not timed,
    )
