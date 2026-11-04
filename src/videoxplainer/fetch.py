"""Fetch a video's captions through yt-dlp (the only network-touching module)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from .captions import available_languages, choose_track, parse
from .chapters import from_info
from .ids import extract_video_id
from .model import Transcript


class _QuietLogger:
    """yt-dlp prints errors itself even in quiet mode; we report them ourselves."""

    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


class FetchError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def classify_error(message: str) -> FetchError:
    low = message.lower()
    if "not a bot" in low or "sign in to confirm" in low:
        return FetchError("bot_check", message)
    if "private video" in low or "members-only" in low or "join this channel" in low:
        return FetchError("private", message)
    if "429" in low or "too many requests" in low:
        return FetchError("rate_limited", message)
    if "unavailable" in low or "removed" in low or "does not exist" in low:
        return FetchError("unavailable", message)
    if "urlopen error" in low or "timed out" in low or "getaddrinfo" in low:
        return FetchError("network", message)
    return FetchError("error", message)


def fetch_transcript(
    target: str,
    lang: Optional[str] = None,
    cookies_from_browser: Optional[str] = None,
    cookies_file: Optional[str] = None,
    ydl_factory: Optional[Callable[[dict], Any]] = None,
) -> Transcript:
    video_id = extract_video_id(target)
    if not video_id:
        raise FetchError("invalid_input", "That doesn't look like a YouTube link or video id.")
    if ydl_factory is None:
        import yt_dlp

        ydl_factory = yt_dlp.YoutubeDL
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
            "socket_timeout": 30, "logger": _QuietLogger()}
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    if cookies_file:
        opts["cookiefile"] = cookies_file
    try:
        with ydl_factory(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            track = choose_track(info or {}, lang)
            if not track:
                langs = available_languages(info or {})
                if lang and langs:
                    raise FetchError("no_captions", f"No '{lang}' captions on this video. Available: {', '.join(langs)}")
                raise FetchError("no_captions", "This video has no captions to read.")
            code, is_auto, fmt = track
            raw = ydl.urlopen(fmt["url"]).read().decode("utf-8", "replace")
    except FetchError:
        raise
    except Exception as exc:  # yt-dlp raises many exception types
        raise classify_error(str(exc)) from exc
    segments = parse(raw, fmt.get("ext", ""))
    if not segments:
        raise FetchError("no_captions", "The caption track was empty.")
    return Transcript(
        video_id=video_id,
        title=info.get("title") or "",
        channel=info.get("uploader") or info.get("channel") or "",
        duration=info.get("duration"),
        language=code,
        is_auto=is_auto,
        segments=segments,
        chapters=from_info(info),
    )
