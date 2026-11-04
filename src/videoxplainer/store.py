"""Local SQLite library: cache transcripts and search across everything seen."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model import Chapter, Segment, Transcript


def data_dir() -> Path:
    override = os.environ.get("VIDEOXPLAINER_HOME")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "videoxplainer"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "videoxplainer"


class Store:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else data_dir() / "library.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path))
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS videos (video_id TEXT PRIMARY KEY, title TEXT, channel TEXT,"
            " language TEXT, is_auto INTEGER, duration REAL, fetched_at REAL, segments TEXT, body TEXT,"
            " chapters TEXT, extra TEXT)"
        )
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(videos)")}
        for col in ("chapters", "extra"):  # libraries created by older versions
            if col not in cols:
                self.db.execute(f"ALTER TABLE videos ADD COLUMN {col} TEXT")
        try:
            self.db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(video_id UNINDEXED, title, channel, body)"
            )
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False  # SQLite built without FTS5: fall back to LIKE

    def close(self) -> None:
        self.db.close()

    def save(self, tr: Transcript) -> None:
        body = " ".join(s.text for s in tr.segments)
        segs = json.dumps([[round(s.start, 2), s.text] for s in tr.segments], ensure_ascii=False)
        chapters = None if tr.chapters is None else json.dumps(
            [[c.start, c.end, c.title] for c in tr.chapters], ensure_ascii=False
        )
        extra = json.dumps({"timestamps_estimated": True}) if tr.timestamps_estimated else None
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO videos (video_id, title, channel, language, is_auto, duration,"
                " fetched_at, segments, body, chapters, extra) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (tr.video_id, tr.title, tr.channel, tr.language, int(tr.is_auto), tr.duration, time.time(), segs, body, chapters, extra),
            )
            if self.fts:
                self.db.execute("DELETE FROM docs WHERE video_id = ?", (tr.video_id,))
                self.db.execute(
                    "INSERT INTO docs (video_id, title, channel, body) VALUES (?,?,?,?)",
                    (tr.video_id, tr.title, tr.channel, body),
                )

    def load(self, video_id: str) -> Optional[Transcript]:
        row = self.db.execute("SELECT * FROM videos WHERE video_id = ?", (video_id,)).fetchone()
        if not row:
            return None
        segments = [Segment(float(t), text) for t, text in json.loads(row["segments"])]
        raw_chapters = row["chapters"]
        chapters = None if raw_chapters is None else [Chapter(float(a), float(b), c) for a, b, c in json.loads(raw_chapters)]
        extra = json.loads(row["extra"]) if row["extra"] else {}
        return Transcript(
            video_id=row["video_id"],
            title=row["title"] or "",
            channel=row["channel"] or "",
            duration=row["duration"],
            language=row["language"] or "",
            is_auto=bool(row["is_auto"]),
            segments=segments,
            chapters=chapters,
            timestamps_estimated=bool(extra.get("timestamps_estimated")),
        )

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        words = re.findall(r"\w+", query)
        if not words:
            return []
        if self.fts:
            match = " ".join('"%s"' % w for w in words)
            rows = self.db.execute(
                "SELECT video_id, title, channel, snippet(docs, 3, '[', ']', ' ... ', 12) AS snip "
                "FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT ?",
                (match, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        clause = " AND ".join("(body LIKE ? OR title LIKE ?)" for _ in words)
        args: List[Any] = []
        for w in words:
            args += [f"%{w}%", f"%{w}%"]
        rows = self.db.execute(
            f"SELECT video_id, title, channel, substr(body, 1, 160) AS snip FROM videos WHERE {clause} LIMIT ?",
            args + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
