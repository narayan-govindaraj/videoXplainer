from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PATH_KINDS = {"shorts", "embed", "live", "v"}


def extract_video_id(raw: str) -> Optional[str]:
    """Return the 11-char YouTube video id from a URL or bare id, else None."""
    raw = (raw or "").strip()
    if _ID.match(raw):
        return raw
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    candidate = ""
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) > 1 and parts[0] in _PATH_KINDS:
            candidate = parts[1]
        else:
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    return candidate if _ID.match(candidate) else None
