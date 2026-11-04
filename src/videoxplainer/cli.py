"""videoxplainer command line: fetch / search / verify / check / install-skill / doctor."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .budget import HEADING_COST, fit_groups
from .fetch import FetchError, fetch_transcript
from .ids import extract_video_id
from .localfile import load_local
from .model import Transcript
from .normalize import clean_segments
from .pipeline import build_sections
from .render import render_brief, render_raw
from .selfcheck import run_checks
from .store import Store, data_dir
from .verify import verify_claims

DEFAULT_BUDGET = 8000

HINTS = {
    "bot_check": (
        "YouTube wants proof you're not a bot. Log in to youtube.com in Firefox and retry with "
        "--cookies-from-browser firefox (Chrome/Edge cookie import is unreliable on Windows), "
        "or pass --cookies-file cookies.txt."
    ),
    "rate_limited": "YouTube is rate-limiting this connection. Wait a few minutes and retry.",
    "private": "This video is private or members-only.",
    "unavailable": "This video is unavailable or was removed.",
    "network": "Couldn't reach YouTube. Check your connection or proxy settings.",
}


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load(store: Store, target: str, refresh: bool = False, lang=None, cookies_browser=None, cookies_file=None) -> Transcript:
    """A local transcript file, a cached video, or a fresh download."""
    if os.path.isfile(os.path.expanduser(target)):
        tr = load_local(target)  # files are always re-read: they may have changed
        store.save(tr)
        return tr
    video_id = extract_video_id(target)
    if not video_id:
        raise FetchError("invalid_input", "That doesn't look like a YouTube link, a video id, or a transcript file (.srt, .vtt, .txt).")
    tr = None if refresh else store.load(video_id)
    if tr is not None and lang and tr.language.lower().split("-")[0] != lang.lower().split("-")[0]:
        tr = None  # the library holds another language; fetch the requested one
    if tr is None:
        tr = fetch_transcript(target, lang, cookies_browser, cookies_file)
        store.save(tr)
    return tr


def _message(err: FetchError) -> str:
    return HINTS.get(err.code, err.message)


def _report(err: FetchError) -> int:
    print(f"error: {_message(err)}", file=sys.stderr)
    return 2 if err.code == "invalid_input" else 3 if err.code in HINTS or err.code == "no_captions" else 1


def cmd_fetch(args: argparse.Namespace) -> int:
    store = Store()
    try:
        try:
            tr = _load(store, args.target, args.refresh, args.lang, args.cookies_from_browser, args.cookies_file)
        except FetchError as err:
            return _report(err)
        if args.view == "raw":
            if args.json:
                out = {"video_id": tr.video_id, "title": tr.title, "view": "raw",
                       "segments": [{"t": round(sg.start, 2), "text": sg.text} for sg in tr.segments]}
                print(json.dumps(out, ensure_ascii=False, indent=2))
            else:
                sys.stdout.write(render_raw(tr, args.mode))
            return 0
        _, groups, source = build_sections(tr, not args.no_chapters)
        if tr.chapters is None and source != "video":
            print("hint: re-run with --refresh to also pull YouTube's chapter markers for this video.", file=sys.stderr)
        budget = 0 if args.full else args.budget
        heading = HEADING_COST if args.view == "chapters" and source != "none" else 0
        kept, stats = fit_groups(groups, budget, heading_cost=heading)
        if args.json:
            out = {
                "video_id": tr.video_id,
                "title": tr.title,
                "channel": tr.channel,
                "language": tr.language,
                "is_auto": tr.is_auto,
                "view": args.view,
                "sections_source": source,
                "stats": stats,
                "sections": [
                    {"title": g.title, "start": int(g.start), "paragraphs": [{"t": int(p.start), "text": p.text} for p in g.paragraphs]}
                    for g in kept
                ],
            }
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            sys.stdout.write(render_brief(tr, kept, stats, args.view, args.mode, source))
        return 0
    finally:
        store.close()


def cmd_search(args: argparse.Namespace) -> int:
    store = Store()
    try:
        hits = store.search(args.query, args.limit)
    finally:
        store.close()
    if not hits:
        print("no matches in your library.")
        return 0
    for h in hits:
        print(f"{h['video_id']}  {h['title']}  ({h['channel']})\n    {h['snip']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    store = Store()
    try:
        if os.path.isfile(os.path.expanduser(args.video)):
            try:
                tr = load_local(args.video)
            except FetchError as err:
                return _report(err)
        else:
            tr = store.load(extract_video_id(args.video) or args.video)
    finally:
        store.close()
    if tr is None:
        print("error: that video isn't in your library yet; run `videoxplainer fetch` first.", file=sys.stderr)
        return 3
    raw = sys.stdin.read() if args.claims == "-" else open(args.claims, encoding="utf-8-sig").read()
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        print(f"error: claims file is not valid JSON ({exc}).", file=sys.stderr)
        return 2
    report = verify_claims(payload, clean_segments(tr.segments), "" if tr.is_local else tr.video_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if args.strict and (report["unsupported"] or report["weak"]) else 0


def ytdlp_age_days(version: str, today: "datetime.date") -> "int | None":
    """yt-dlp versions are dates (2026.10.26): how old is this install?"""
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", version or "")
    if not m:
        return None
    try:
        return (today - datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))).days
    except ValueError:
        return None


def cmd_check(args: argparse.Namespace) -> int:
    """Run the self-check on real videos; paste the output into bug reports."""
    store = Store()
    bad = 0
    try:
        for target in args.targets:
            try:
                tr = _load(store, target, args.refresh, args.lang)
            except FetchError as err:
                print(f"FAIL  {target}: {err.code}: {_message(err)}")
                bad += 1
                continue
            print(f"{tr.video_id}  {tr.title}")
            results = run_checks(tr, args.budget)
            for r in results:
                mark = "skip" if r.ok is None else "PASS" if r.ok else "FAIL"
                print(f"  {mark}  {r.name}: {r.detail}")
            if any(r.ok is False for r in results):
                bad += 1
        total = len(args.targets)
        print(f"\n{total - bad}/{total} videos passed all checks")
    finally:
        store.close()
    return 1 if bad else 0


def _skill_text() -> str:
    from importlib.resources import files

    return files("videoxplainer").joinpath("data", "SKILL.md").read_text(encoding="utf-8")


def cmd_install_skill(args: argparse.Namespace) -> int:
    text = _skill_text()
    if args.print:
        sys.stdout.write(text)
        return 0
    root = Path(args.dir).expanduser() if args.dir else Path.home() / ".claude" / "skills"
    dest = root / "videoxplainer" / "SKILL.md"
    if dest.exists():
        if dest.read_text(encoding="utf-8") == text:
            print(f"already installed: {dest}")
            return 0
        if not args.force:
            print(f"error: {dest} exists and differs; re-run with --force to overwrite.", file=sys.stderr)
            return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    print(f"installed skill: {dest}")
    print("Restart Claude Code (or open a new session), then paste a YouTube link.")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    try:
        import yt_dlp

        ytdlp = yt_dlp.version.__version__
    except ImportError:
        ytdlp = "MISSING (pip install yt-dlp)"
    fts = True
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(a)")
    except sqlite3.OperationalError:
        fts = False
    print(f"videoxplainer {__version__}")
    print(f"python   {platform.python_version()} on {platform.system()} {platform.machine()}")
    print(f"yt-dlp   {ytdlp}")
    age = ytdlp_age_days(ytdlp, datetime.date.today())
    if age is not None and age > 90:
        print(f"         warning: this yt-dlp is {age} days old; YouTube changes often, so run: pip install -U yt-dlp")
    print(f"library  {data_dir()}")
    print(f"sqlite   {sqlite3.sqlite_version} (full-text search: {'yes' if fts else 'no, using slower fallback'})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="videoxplainer", description="Token-budgeted, evidence-checked video briefs.")
    p.add_argument("--version", action="version", version=f"videoxplainer {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="get a condensed brief for a video")
    f.add_argument("target", help="YouTube URL, 11-character video id, or a transcript file (.srt .vtt .txt)")
    f.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help=f"max tokens in the brief (default {DEFAULT_BUDGET})")
    f.add_argument("--full", action="store_true", help="no token limit (complete cleaned transcript)")
    f.add_argument("--view", choices=["chapters", "excerpts", "raw"], default="chapters",
                   help="chapters: condensed, grouped by chapter/topic (default); excerpts: condensed, flat; raw: captions as downloaded")
    f.add_argument("--mode", choices=["text", "summary", "actions"], default="text",
                   help="summary/actions append a task for the model to carry out")
    f.add_argument("--lang", help="caption language (strict: never silently swapped)")
    f.add_argument("--no-chapters", action="store_true", help="ignore YouTube's chapters and detect topics from the text instead")
    f.add_argument("--json", action="store_true", help="machine-readable output")
    f.add_argument("--refresh", action="store_true", help="re-download even if cached")
    f.add_argument("--cookies-from-browser", metavar="BROWSER", help="e.g. firefox")
    f.add_argument("--cookies-file", metavar="PATH", help="Netscape-format cookies.txt")
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("search", help="search every video you've fetched")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.set_defaults(func=cmd_search)

    v = sub.add_parser("verify", help="check that an LLM's cited quotes really appear in the video")
    v.add_argument("video", help="URL or video id (already fetched), or the transcript file itself")
    v.add_argument("claims", help="JSON file from the extraction step, or - for stdin")
    v.add_argument("--strict", action="store_true", help="exit 1 if anything is weak/unsupported")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("install-skill", help="install the Claude Code skill (writes one file under ~/.claude/skills)")
    i.add_argument("--dir", metavar="DIR", help="skills folder to use instead of ~/.claude/skills (e.g. a project's .claude/skills)")
    i.add_argument("--force", action="store_true", help="overwrite an existing, different skill file")
    i.add_argument("--print", action="store_true", help="print the skill text instead of installing (for other agents)")
    i.set_defaults(func=cmd_install_skill)

    k = sub.add_parser("check", help="self-test the pipeline on real videos")
    k.add_argument("targets", nargs="+", help="YouTube URLs, ids, or transcript files")
    k.add_argument("--budget", type=int, default=2000)
    k.add_argument("--refresh", action="store_true", help="re-download instead of using the library")
    k.add_argument("--lang", help="caption language to test (e.g. hi, ta)")
    k.set_defaults(func=cmd_check)

    d = sub.add_parser("doctor", help="diagnose the install")
    d.set_defaults(func=cmd_doctor)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    _utf8_stdio()
    args = build_parser().parse_args(argv)
    return args.func(args)
