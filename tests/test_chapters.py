import json
import random
import sqlite3

import pytest

from conftest import make_transcript
from videoxplainer import cli
from videoxplainer.budget import fit_groups
from videoxplainer.chapters import build_groups, detect_sections, from_info
from videoxplainer.model import Chapter, Group, Paragraph, Segment
from videoxplainer.pipeline import build_sections
from videoxplainer.store import Store

TOPICS = {
    "scaling": "scaling parameters compute training laws loss optimizer gradient batch tokens".split(),
    "security": "attacker injection exploit jailbreak payload defense malicious suffix adversarial poisoning".split(),
    "agents": "agent tools planning browser memory workflow autonomous orchestrate delegate tasks".split(),
}


def topical_doc(per_topic=14, step=30.0, seed=1):
    rng = random.Random(seed)
    paras, t = [], 0.0
    for words in TOPICS.values():
        for _ in range(per_topic):
            text = " ".join(rng.choice(words) for _ in range(40)) + " and so on and so forth."
            paras.append(Paragraph(t, text))
            t += step
    return paras


def test_from_info_sorted_and_tolerant():
    info = {"chapters": [{"start_time": 60, "end_time": 120, "title": " B "}, {"start_time": 0, "end_time": 60, "title": "A"}, {"bad": 1}]}
    assert [(c.start, c.title) for c in from_info(info)] == [(0.0, "A"), (60.0, "B")]
    assert from_info({}) == []


def test_detect_finds_topic_shifts():
    paras = topical_doc()
    sections = detect_sections(paras)
    assert len(sections) == 3
    starts = [s[0] for s in sections]
    true = [0, 14 * 30, 28 * 30]
    assert starts[0] == 0 and all(abs(a - b) <= 2 * 30 for a, b in zip(starts, true))
    assert "scaling" in sections[0][1] or "training" in sections[0][1] or "parameters" in sections[0][1]
    assert any(w in sections[1][1] for w in TOPICS["security"])


def test_detect_skips_short_videos():
    assert detect_sections([Paragraph(i * 20.0, "word " * 30) for i in range(10)]) == []


def test_build_groups_with_late_first_chapter():
    segs = [Segment(float(t), f"seg {t}") for t in (0, 5, 70, 80)]
    groups = build_groups(segs, [(60.0, "Main")])
    assert [g.title for g in groups] == ["Intro", "Main"]
    assert groups[1].paragraphs[0].start == 70


def _groups(n_groups=4, paras_each=15):
    groups = []
    for g in range(n_groups):
        paras = [
            Paragraph(g * 1000 + i * 20.0, f"Chapter {g} point {i} about subject{g}x{i} matters because reason{g}x{i} follows. " + "filler words here " * 10)
            for i in range(paras_each)
        ]
        groups.append(Group(f"Chapter {g}", g * 1000.0, paras))
    return groups


def test_fit_groups_every_chapter_represented_and_within_budget():
    kept, stats = fit_groups(_groups(), 900, heading_cost=12)
    assert stats["trimmed"] and stats["kept_tokens"] <= 900
    assert [g.title for g in kept] == [f"Chapter {i}" for i in range(4)]
    for g in kept:
        starts = [p.start for p in g.paragraphs]
        assert starts == sorted(starts)


def test_fit_groups_long_chapters_get_more():
    groups = _groups(2, 10) + [Group("Big", 5000.0, _groups(1, 60)[0].paragraphs)]
    kept, _ = fit_groups(groups, 1500)
    size = {g.title: sum(len(p.text) for p in g.paragraphs) for g in kept}
    assert size["Big"] > size["Chapter 0"]


def test_fit_groups_tiny_budget_still_respected():
    kept, stats = fit_groups(_groups(), 150, heading_cost=12)
    assert stats["kept_tokens"] <= 150 and kept


def test_pipeline_prefers_video_chapters():
    tr = make_transcript(texts=[f"line number {i} talking about things" for i in range(6)])
    tr.chapters = [Chapter(0, 15, "Start"), Chapter(15, 30, "End")]
    _, groups, source = build_sections(tr)
    assert source == "video" and [g.title for g in groups] == ["Start", "End"]
    tr.chapters = []
    assert build_sections(tr)[2] == "none"


def test_store_persists_chapters_and_migrates_old_library(home):
    tr = make_transcript()
    tr.chapters = [Chapter(0, 5, "A"), Chapter(5, 10, "B")]
    s = Store()
    s.save(tr)
    assert [c.title for c in s.load(tr.video_id).chapters] == ["A", "B"]
    s.close()
    # a 0.1.x library: same table without the chapters column
    old = home / "old.db"
    db = sqlite3.connect(str(old))
    db.execute("CREATE TABLE videos (video_id TEXT PRIMARY KEY, title TEXT, channel TEXT, language TEXT,"
               " is_auto INTEGER, duration REAL, fetched_at REAL, segments TEXT, body TEXT)")
    db.execute("INSERT INTO videos VALUES ('abcdefghijk','T','C','en',0,9,0,'[[0,\"hi there\"]]','hi there')")
    db.commit()
    db.close()
    s2 = Store(old)
    loaded = s2.load("abcdefghijk")
    assert loaded.chapters is None and loaded.segments[0].text == "hi there"


def _cached(home, chapters, video_id="dQw4w9WgXcQ"):
    texts = [f"minute {i} we discuss topic{i // 4} with detail{i} and example{i} again and again" for i in range(40)]
    tr = make_transcript(video_id=video_id, texts=texts)
    for i, sg in enumerate(tr.segments):
        sg.start = i * 30.0
    tr.chapters = chapters
    s = Store()
    s.save(tr)
    s.close()


def test_cli_views(home, capsys):
    _cached(home, [Chapter(0, 600, "Warmup"), Chapter(600, 1200, "Deep dive")])
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--view", "chapters", "--mode", "summary", "--budget", "300"]) == 0
    out = capsys.readouterr().out
    assert "## [00:00] Warmup" in out and "## [10:00] Deep dive" in out and "each \"##\" heading" in out
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--view", "excerpts", "--budget", "300"]) == 0
    flat = capsys.readouterr().out
    assert "##" not in flat and "condensed" in flat
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--view", "raw"]) == 0
    raw = capsys.readouterr().out
    assert raw.count("minute ") == 40 and "unfiltered" in raw
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--full", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["sections_source"] == "video" and len(data["sections"]) == 2


def test_cli_hint_when_chapters_unknown(home, capsys):
    _cached(home, None)
    assert cli.main(["fetch", "dQw4w9WgXcQ"]) == 0
    assert "--refresh" in capsys.readouterr().err


def test_section_with_only_junk_is_dropped_not_padded():
    junk = Group("Mumbling", 9000.0, [Paragraph(9000.0, "so um yeah the"), Paragraph(9010.0, "that went viral")])
    kept, stats = fit_groups(_groups(3, 12) + [junk], 400, heading_cost=12)
    assert stats["trimmed"]
    assert "Mumbling" not in [g.title for g in kept]
    assert all(len(p.text.split()) >= 8 for g in kept for p in g.paragraphs)


def _meeting_paragraphs(seed, per=10, step=75.0):
    rng = random.Random(seed)
    vocab = [
        "pricing tiers discount annual plan packaging margin churn upgrade".split(),
        "hiring recruiter interview offer onboarding headcount referral pipeline candidate".split(),
        "launch checklist rollout beta feedback bugs release marketing docs timeline".split(),
    ]
    paras, t = [], 0.0
    for words_ in vocab:
        for _ in range(per):
            paras.append(Paragraph(t, " ".join(rng.choice(words_) for _ in range(30)) + " and we agreed to follow up this week."))
            t += step
    return paras


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_detect_does_not_oversegment_long_topics(seed):
    # 3 topics of 12.5 minutes each: exactly 3 sections, cut at the true boundaries
    sections = detect_sections(_meeting_paragraphs(seed))
    assert [round(s[0]) for s in sections] == [0, 750, 1500]


def test_detect_leaves_uniform_talk_in_one_piece():
    rng = random.Random(1)
    vocab = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar".split()
    flat = [Paragraph(i * 30.0, " ".join(rng.choice(vocab) for _ in range(40))) for i in range(40)]
    assert detect_sections(flat) == []


def test_requested_language_is_never_silently_swapped():
    from videoxplainer.captions import available_languages, choose_track

    fmt = lambda ext: [{"ext": ext, "url": "http://x"}]
    info = {"language": "en", "subtitles": {"en": fmt("vtt"), "ar": fmt("vtt")}, "automatic_captions": {"en-orig": fmt("json3"), "en": fmt("json3")}}
    assert choose_track(info, "hi") is None
    assert choose_track(info, "ar")[0] == "ar"
    assert choose_track(info)[0] == "en"
    assert available_languages(info) == ["ar", "en", "en (auto)"]
    only_auto = {"language": "hi", "automatic_captions": {"hi-orig": fmt("json3"), "en": fmt("json3")}}
    assert choose_track(only_auto, "hi")[:2] == ("hi", True)
    assert choose_track(only_auto, "ta") is None
    translated = {"language": "en", "automatic_captions": {"en-orig": fmt("json3"), "hi": fmt("json3")}}  # "hi" = machine translation
    assert choose_track(translated, "hi") is None and choose_track(translated, "en")[:2] == ("en", True)


def test_fetch_error_lists_available_languages(monkeypatch):
    from test_fetch_cli import FakeYDL, factory
    from videoxplainer.fetch import FetchError, fetch_transcript

    info = {"title": "T", "language": "en", "subtitles": {"en": [{"ext": "vtt", "url": "http://x"}]}}
    with pytest.raises(FetchError) as e:
        fetch_transcript("dQw4w9WgXcQ", lang="hi", ydl_factory=factory(info=info))
    assert e.value.code == "no_captions" and "Available: en" in e.value.message


def test_cache_respects_requested_language(home, monkeypatch, capsys):
    calls = []

    def fake(target, lang, cb, cf):
        calls.append(lang)
        tr = make_transcript(video_id="dQw4w9WgXcQ", texts=[f"text in {lang or 'en'} number {i} with several more words here" for i in range(8)])
        tr.language = lang or "en"
        return tr

    monkeypatch.setattr(cli, "fetch_transcript", fake)
    assert cli.main(["fetch", "dQw4w9WgXcQ"]) == 0
    assert cli.main(["fetch", "dQw4w9WgXcQ"]) == 0          # cached
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--lang", "hi"]) == 0  # different language: refetch
    assert calls == [None, "hi"]
    assert "text in hi" in capsys.readouterr().out.split("text in en")[-1]


def test_auto_labels_skip_contractions_and_filler():
    rng = random.Random(8)
    filler = "you're said she's think thing people going really".split()
    paras, t = [], 0.0
    for words_ in TOPICS.values():
        for _ in range(14):
            body = [rng.choice(words_) for _ in range(30)] + [rng.choice(filler) for _ in range(20)]
            rng.shuffle(body)
            paras.append(Paragraph(t, " ".join(body)))
            t += 30.0
    sections = detect_sections(paras)
    assert len(sections) == 3
    for _, title in sections:
        assert "'" not in title and not (set(title.split(", ")) & {"said", "think", "thing", "people", "going", "really"})
