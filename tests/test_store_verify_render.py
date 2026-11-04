import sqlite3

import pytest

from conftest import make_transcript
from videoxplainer.model import Paragraph, Segment
from videoxplainer.render import render_brief
from videoxplainer.store import Store
from videoxplainer.verify import verify_claims


def test_store_roundtrip_and_unicode(home):
    tr = make_transcript(texts=["\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd pricing tips", "\u0928\u092e\u0938\u094d\u0924\u0947 hiring tips"])
    s = Store()
    s.save(tr)
    back = s.load(tr.video_id)
    assert back.segments[0].text == tr.segments[0].text and back.title == "Demo"
    assert s.load("zzzzzzzzzzz") is None


def test_store_search_fts(home):
    s = Store()
    s.save(make_transcript())
    hits = s.search("hiring")
    assert hits and hits[0]["video_id"] == "abcdefghijk" and "hiring" in hits[0]["snip"]
    assert s.search("") == [] and s.search("nonexistentword") == []


def test_store_search_fallback_without_fts(home, monkeypatch):
    s = Store()
    s.fts = False
    s.save(make_transcript())
    assert s.search("pricing")[0]["video_id"] == "abcdefghijk"


SEGS = [
    Segment(0, "welcome to the show today we talk about growth"),
    Segment(65, "the first thing you should do is email ten customers every single week"),
    Segment(130, "second always track your churn before you spend on ads"),
]


def test_verify_exact_fuzzy_and_unsupported():
    claims = {
        "actions": [
            {"action": "Email customers", "quote": "email ten customers every single week", "t": 66},
            {"action": "Track churn", "quote": "always track your churn before you spend on ad"},
            {"action": "Paraphrase", "quote": "always track your churn before spending on ads"},
            {"action": "Buy a boat", "quote": "you should definitely purchase a yacht immediately"},
            {"action": "No quote"},
        ]
    }
    rep = verify_claims(claims, SEGS, "abcdefghijk")
    status = [i["status"] for i in rep["items"]]
    # a paraphrase is deliberately only "weak": quotes must be (near-)verbatim
    assert status == ["supported", "supported", "weak", "unsupported", "no_quote"]
    assert rep["items"][0]["matched_at"] == "01:05"
    assert rep["items"][0]["link"].endswith("?t=65")
    assert rep["unsupported"] == 1 and rep["weak"] == 1 and rep["checked"] == 5


def test_verify_flags_wrong_timestamp():
    rep = verify_claims([{"action": "x", "quote": "track your churn before you spend", "t": 5}], SEGS)
    assert rep["items"][0]["note"].startswith("claimed timestamp")


def test_render_brief_modes():
    from videoxplainer.model import Group

    tr = make_transcript()
    groups = [Group("Intro", 0, [Paragraph(0, "hello")]), Group("Pricing", 75, [Paragraph(75, "world")])]
    full = render_brief(tr, groups, {"trimmed": False, "full_tokens": 10, "sections": 2}, "chapters", "text", "video")
    assert "## [01:15] Pricing" in full and "[01:15] world" in full and "YouTube chapters" in full and "TASK" not in full
    flat = render_brief(tr, groups, {"trimmed": False, "full_tokens": 10, "sections": 2}, "excerpts", "text", "video")
    assert "##" not in flat
    trimmed = render_brief(tr, groups, {"trimmed": True, "full_tokens": 900, "kept_tokens": 300, "sections": 2}, "chapters", "actions", "video")
    assert "condensed to ~300 of ~900" in trimmed and "videoxplainer verify abcdefghijk" in trimmed
    summ = render_brief(tr, groups, {"trimmed": True, "full_tokens": 9, "kept_tokens": 3, "sections": 2}, "chapters", "summary", "auto")
    assert 'each "##" heading' in summ and "auto-detected" in summ and "reflects the excerpts only" in summ
    summ_flat = render_brief(tr, groups, {"trimmed": False, "full_tokens": 9, "sections": 2}, "excerpts", "summary", "video")
    assert "5 bullets" in summ_flat


def test_render_raw_is_unfiltered():
    from videoxplainer.render import render_raw

    tr = make_transcript(texts=["[Music] um so", "um so the key"])
    out = render_raw(tr, "summary")
    assert "[00:00] [Music] um so" in out and "[00:05] um so the key" in out and "5 bullets" in out
