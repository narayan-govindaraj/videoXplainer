"""Caption parsing and track selection (pure functions, no network)."""

from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .model import Segment

_TAG = re.compile(r"<[^>]*>")
_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")


def _to_seconds(stamp: str) -> float:
    m = _TS.search(stamp)
    if not m:
        return 0.0
    hours, minutes, secs, millis = (int(m.group(1) or 0), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return hours * 3600 + minutes * 60 + secs + millis / 1000.0


def parse_json3(text: str) -> List[Segment]:
    data = json.loads(text)
    out: List[Segment] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        line = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if line:
            out.append(Segment(event.get("tStartMs", 0) / 1000.0, html.unescape(line)))
    return out


def parse_vtt(text: str) -> List[Segment]:
    out: List[Segment] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        start = _to_seconds(lines[idx].split("-->")[0])
        body = " ".join(_TAG.sub("", ln).strip() for ln in lines[idx + 1 :])
        body = re.sub(r"\s+", " ", html.unescape(body)).strip()
        if body:
            out.append(Segment(start, body))
    return out


def parse(text: str, ext: str = "") -> List[Segment]:
    if ext == "json3" or text.lstrip().startswith("{"):
        try:
            return parse_json3(text)
        except (ValueError, AttributeError):
            pass
    return parse_vtt(text)


Track = Tuple[str, bool, Dict[str, Any]]  # (language code, is_auto, yt-dlp format dict)


def _pick_format(formats: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    by_ext = {f.get("ext"): f for f in formats if f.get("url")}
    for ext in ("json3", "vtt"):
        if ext in by_ext:
            return by_ext[ext]
    return None


def _base(code: str) -> str:
    return code.lower().split("-")[0]


def _find(tracks: Dict[str, Any], predicates) -> Optional[str]:
    for pred in predicates:
        for key in tracks:
            if pred(key.lower()):
                return key
    return None


def choose_track(info: Dict[str, Any], lang: Optional[str] = None) -> Optional[Track]:
    """Pick the best caption track from a yt-dlp info dict.

    Preference: author-uploaded captions, then the video's *original* auto
    captions. Machine translations are never chosen.
    """
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    want = (lang or "").lower()
    vid_lang = (info.get("language") or "").lower()

    if want:  # an explicit request is never answered in another language
        prefs = [lambda k: k == want, lambda k: _base(k) == _base(want)]
    else:
        prefs = []
        if vid_lang:
            prefs += [lambda k: k == vid_lang, lambda k: _base(k) == _base(vid_lang)]
        prefs.append(lambda k: _base(k) == "en")

    key = _find(manual, prefs)
    if key is None and not want:
        key = next(iter(manual), None)  # no preference: take whatever the author uploaded
    if key:
        fmt = _pick_format(manual[key])
        if fmt:
            return key, False, fmt

    if want:  # an explicit request is never silently answered in another language
        # only the speaker's original track: YouTube also lists machine *translations* under plain codes
        auto_prefs = [lambda k: k.endswith("-orig") and _base(k) == _base(want),
                      lambda k: k == want and _base(vid_lang) == _base(want)]
    else:
        auto_prefs = [lambda k: k.endswith("-orig")]
        if vid_lang:
            auto_prefs.append(lambda k: k == vid_lang)
        auto_prefs.append(lambda k: k == "en")
    key = _find(auto, auto_prefs)
    if key:
        fmt = _pick_format(auto[key])
        if fmt:
            return key.replace("-orig", ""), True, fmt
    return None


def available_languages(info: Dict[str, Any]) -> List[str]:
    """Languages we could read: uploaded tracks plus original auto-captions."""
    manual = [k for k, v in (info.get("subtitles") or {}).items() if _pick_format(v)]
    auto = [k.replace("-orig", "") + " (auto)" for k, v in (info.get("automatic_captions") or {}).items() if k.endswith("-orig") and _pick_format(v)]
    return sorted(manual) + sorted(auto)
