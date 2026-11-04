import datetime
import random

import pytest

from conftest import make_transcript
from videoxplainer import cli
from videoxplainer.budget import estimate_tokens, fit_groups
from videoxplainer.chapters import detect_sections
from videoxplainer.fetch import FetchError
from videoxplainer.model import Group, Paragraph, Segment, Transcript
from videoxplainer.selfcheck import run_checks
from videoxplainer.textutil import words
from videoxplainer.verify import verify_claims

HINDI = {
    "a": "प्रशिक्षण पैरामीटर डेटा मॉडल अनुकूलन ग्रेडिएंट गणना टोकन सटीकता प्रदर्शन".split(),
    "b": "सुरक्षा हमलावर कमजोरी इंजेक्शन बचाव दुर्भावनापूर्ण सुरक्षित जोखिम अनुमति पहुंच".split(),
    "c": "एजेंट उपकरण योजना स्मृति ब्राउज़र कार्यप्रवाह स्वायत्त समन्वय कार्य सहायक".split(),
}
TAMIL = "வணக்கம் நண்பர்களே இன்று மாதிரி தரவு பயிற்சி பாதுகாப்பு தாக்குதல் முகவர் கருவி".split()


def hindi_paragraphs(per_topic=14, step=30.0, seed=3):
    rng = random.Random(seed)
    out, t = [], 0.0
    for vocab in HINDI.values():
        for _ in range(per_topic):
            out.append(Paragraph(t, " ".join(rng.choice(vocab) for _ in range(40)) + " और इसी तरह आगे।"))
            t += step
    return out


def test_words_are_unicode_and_apostrophe_agnostic():
    assert words("नमस्ते, दोस्तों!") == ["नमस्ते", "दोस्तों"]
    assert words("doesn\u2019t") == words("doesn't") == ["doesn't"]
    assert words("Hello,  WORLD!!") == ["hello", "world"]
    assert words("\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd, \u0ba8\u0ba3\u0bcd\u0baa\u0bb0\u0bcd\u0b95\u0bb3\u0bc7") == ["\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd", "\u0ba8\u0ba3\u0bcd\u0baa\u0bb0\u0bcd\u0b95\u0bb3\u0bc7"]


def test_token_estimate_is_conservative_for_other_scripts():
    latin = "a" * 60
    tamil = "\u0b95" * 60
    assert estimate_tokens(latin) == 15
    assert estimate_tokens(tamil) >= 2.5 * estimate_tokens(latin)  # 1.5 vs 4 chars per token


def test_verify_works_on_hindi():
    text = " ".join(HINDI["a"][:8])
    segs = [Segment(0.0, "शुरुआत की बात"), Segment(12.0, text + " और आगे")]
    ok = verify_claims([{"quote": text}], segs)
    assert ok["items"][0]["status"] == "supported" and ok["items"][0]["matched_at"] == "00:12"
    bad = verify_claims([{"quote": " ".join(reversed(text.split()))}], segs)
    assert bad["items"][0]["status"] != "supported"


def test_budget_and_detection_work_on_hindi():
    paras = hindi_paragraphs()
    kept, stats = fit_groups([Group("", 0.0, paras)], 500)
    assert stats["trimmed"] and stats["kept_tokens"] <= 500 and kept
    sections = detect_sections(paras)
    true = [0, 420, 840]
    assert len(sections) == 3 and all(abs(a[0] - b) <= 60 for a, b in zip(sections, true))


def _long_transcript(vocab_text, video_id="dQw4w9WgXcQ"):
    rng = random.Random(5)
    segs = []
    for i in range(120):
        segs.append(Segment(i * 8.0, " ".join(rng.choice(vocab_text) for _ in range(12))))
    return Transcript(video_id=video_id, title="T", language="xx", segments=segs)


@pytest.mark.parametrize("vocab", [("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima".split()), TAMIL, HINDI["a"] + HINDI["b"]])
def test_selfcheck_passes_across_scripts(vocab):
    results = run_checks(_long_transcript(vocab), 400)
    failed = [r for r in results if r.ok is False]
    assert not failed, failed
    assert any(r.name == "real quotes are supported" and r.ok for r in results)


def test_selfcheck_flags_broken_transcript_and_skips_short():
    tiny = make_transcript(texts=["only", "two"])
    results = run_checks(tiny)
    assert any(r.name == "captions parsed" and r.ok is False for r in results)
    assert any(r.ok is None for r in results)


def test_check_command(home, monkeypatch, capsys):
    tr = _long_transcript("alpha bravo charlie delta echo foxtrot golf hotel india juliet".split())
    monkeypatch.setattr(cli, "fetch_transcript", lambda target, *a: tr)
    assert cli.main(["check", "dQw4w9WgXcQ", "--budget", "300"]) == 0
    out = capsys.readouterr().out
    assert "PASS  budget respected" in out and "1/1 videos passed" in out

    def boom(target, *a):
        raise FetchError("bot_check", "raw")

    monkeypatch.setattr(cli, "fetch_transcript", boom)
    assert cli.main(["check", "aaaaaaaaaaa", "not-a-link"]) == 1
    out = capsys.readouterr().out
    assert "FAIL  aaaaaaaaaaa: bot_check" in out and "FAIL  not-a-link" in out and "0/2 videos passed" in out


def test_ytdlp_age():
    today = datetime.date(2026, 11, 4)
    assert cli.ytdlp_age_days("2026.10.26", today) == 9
    assert cli.ytdlp_age_days("2026.10.26.232815", today) == 9
    assert cli.ytdlp_age_days("2026.02.30", today) is None
    assert cli.ytdlp_age_days("MISSING (pip install yt-dlp)", today) is None


def test_check_benchmarks_autodetect_against_real_chapters():
    from videoxplainer.model import Chapter
    from videoxplainer.selfcheck import boundary_agreement
    from test_chapters import topical_doc

    paras = topical_doc()
    tr = Transcript(video_id="dQw4w9WgXcQ", title="T", language="en",
                    segments=[Segment(p.start, p.text) for p in paras],
                    chapters=[Chapter(0, 420, "A"), Chapter(420, 840, "B"), Chapter(840, 1260, "C")])
    info = [r for r in run_checks(tr, 800) if r.name.startswith("auto-detect vs")]
    assert info and info[0].ok is True and "2 of 2 auto-detected cuts" in info[0].detail and "2 of 2 real chapter starts" in info[0].detail
    assert boundary_agreement([0, 100, 500], [0, 130, 900]) == (1, 2, 1, 2)


def test_no_chapters_flag_uses_detection(home, monkeypatch, capsys):
    from videoxplainer.model import Chapter
    from test_chapters import topical_doc

    paras = topical_doc()
    tr = Transcript(video_id="dQw4w9WgXcQ", title="T", language="en",
                    segments=[Segment(p.start, p.text) for p in paras],
                    chapters=[Chapter(0, 1260, "Whole video")])
    monkeypatch.setattr(cli, "fetch_transcript", lambda *a: tr)
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--full"]) == 0
    assert "## [00:00] Whole video" in capsys.readouterr().out
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--full", "--no-chapters"]) == 0
    out = capsys.readouterr().out
    assert "auto-detected from topic shifts" in out and "Whole video" not in out
