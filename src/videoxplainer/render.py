"""Render what goes into the model's context: three views x three modes.

views  raw       captions exactly as downloaded
       excerpts  condensed key passages, flat
       chapters  condensed passages grouped under chapter / topic headings
modes  text      just the content
       summary   + a task: write a summary (per chapter in the chapters view)
       actions   + a task: extract evidence-backed actions
"""

from __future__ import annotations

from typing import Dict, List

from .budget import estimate_tokens
from .model import Group, Segment, Transcript, fmt_ts

ACTIONS_INSTRUCTIONS = """\
TASK: list what the viewer should DO, highest impact first (max 10). Use only the text above; skip intros, sponsor reads and filler.
Reply as JSON: {"actions":[{"action":"imperative sentence","why":"short reason","quote":"verbatim, <=20 words, copied from above","t":seconds}],"tools_resources":["..."],"claims_to_verify":["..."]}
Then check your quotes: save the JSON and run `videoxplainer verify {video_id} <file>`; drop or fix anything flagged unsupported."""

SUMMARY_FLAT = """\
TASK: summarize. One sentence on what the video is, then 5 bullets with the most important points, each ending with its [mm:ss] timestamp. Use only the text above{condensed}."""

SUMMARY_CHAPTERS = """\
TASK: for each "##" heading above write 1-2 sentences on its main point (keep the [mm:ss]), then a 3-bullet overall takeaway.{relabel} Use only the text above{condensed}."""

_CONDENSED = "; the text was condensed, so say the summary reflects the excerpts only"
_RELABEL = " Headings that are keyword lists were auto-detected: replace each with a short descriptive title."


def _header(tr: Transcript, lines_extra: List[str]) -> List[str]:
    if tr.is_local:
        meta = [p for p in (fmt_ts(tr.duration) if tr.duration else "", f"local file{' (' + tr.language + ')' if tr.language else ''}") if p]
        source = "source: local transcript file (no video link)"
        if tr.timestamps_estimated:
            source += "; timestamps are estimated from word count because the file has none"
        return [f"# {tr.title or tr.video_id}", " | ".join(meta), source] + lines_extra
    kind = "auto-captions" if tr.is_auto else "uploaded captions"
    meta = [p for p in (tr.channel, fmt_ts(tr.duration) if tr.duration else "", f"{tr.language or '?'} ({kind})") if p]
    return [f"# {tr.title or tr.video_id}", " | ".join(meta), f"link: {tr.url}  (deep link: {tr.url}?t=<seconds>)"] + lines_extra


def _task(tr: Transcript, mode: str, view: str, stats: Dict[str, object], source: str) -> List[str]:
    if mode == "actions":
        return ["---", ACTIONS_INSTRUCTIONS.replace("{video_id}", tr.video_id)]
    if mode == "summary":
        condensed = _CONDENSED if stats.get("trimmed") else ""
        if view == "chapters" and source != "none":
            relabel = _RELABEL if source == "auto" else ""
            return ["---", SUMMARY_CHAPTERS.format(relabel=relabel, condensed=condensed)]
        return ["---", SUMMARY_FLAT.format(condensed=condensed)]
    return []


def render_raw(tr: Transcript, mode: str = "text") -> str:
    tokens = sum(estimate_tokens(s.text) + 4 for s in tr.segments)
    lines = _header(tr, [f"raw captions exactly as downloaded, unfiltered (~{tokens} tokens; auto-captions repeat lines)", "---"])
    lines.extend(f"[{fmt_ts(s.start)}] {s.text}" for s in tr.segments)
    lines.extend(_task(tr, mode, "raw", {"trimmed": False}, "none"))
    return "\n".join(lines) + "\n"


def render_brief(tr: Transcript, groups: List[Group], stats: Dict[str, object], view: str = "chapters", mode: str = "text", source: str = "none") -> str:
    extra: List[str] = []
    if source != "none" and len(groups) > 0:
        how = "YouTube chapters" if source == "video" else "auto-detected from topic shifts"
        extra.append(f"sections: {stats.get('sections', len(groups))} ({how})")
    if stats.get("trimmed"):
        extra.append(
            f"note: condensed to ~{stats['kept_tokens']} of ~{stats['full_tokens']} tokens "
            f"(extractive, spread across sections); use --full for everything"
        )
    else:
        extra.append(f"tokens: ~{stats['full_tokens']} (complete)")
    lines = _header(tr, extra) + ["---"]
    for g in groups:
        if view == "chapters" and g.title:
            lines.append(f"## [{fmt_ts(g.start)}] {g.title}")
        lines.extend(f"[{fmt_ts(p.start)}] {p.text}" for p in g.paragraphs)
    lines.extend(_task(tr, mode, view, stats, source))
    return "\n".join(lines) + "\n"
