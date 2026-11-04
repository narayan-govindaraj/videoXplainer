import json

import pytest

from videoxplainer.captions import choose_track, parse, parse_json3, parse_vtt
from videoxplainer.ids import extract_video_id

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "raw",
    [
        VID,
        f"https://www.youtube.com/watch?v={VID}",
        f"https://www.youtube.com/watch?v={VID}&t=42s",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"https://www.youtube.com/live/{VID}?feature=share",
        f"youtube.com/watch?v={VID}",
        f"  https://m.youtube.com/watch?v={VID}  ",
    ],
)
def test_extract_ok(raw):
    assert extract_video_id(raw) == VID


@pytest.mark.parametrize("raw", ["", "hello", "https://example.com/watch?v=" + VID, "https://youtu.be/short"])
def test_extract_rejects(raw):
    assert extract_video_id(raw) is None


def test_json3():
    data = {"events": [{"tStartMs": 1500, "segs": [{"utf8": "hello "}, {"utf8": "world"}]}, {"tStartMs": 3000}]}
    segs = parse_json3(json.dumps(data))
    assert [(s.start, s.text) for s in segs] == [(1.5, "hello world")]


def test_vtt_strips_tags_and_joins_lines():
    vtt = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nhello <c>there</c>\nfriend\n\n"
        "00:01:00.500 --> 00:01:02.000 align:start\n&amp; more\n"
    )
    segs = parse_vtt(vtt)
    assert [(s.start, s.text) for s in segs] == [(1.0, "hello there friend"), (60.5, "& more")]


def test_parse_autodetects_json():
    assert parse('{"events":[{"tStartMs":0,"segs":[{"utf8":"x"}]}]}')[0].text == "x"


def fmt(ext):
    return [{"ext": ext, "url": f"http://x/{ext}"}]


def test_track_prefers_manual_over_auto():
    info = {"language": "en", "subtitles": {"en": fmt("vtt")}, "automatic_captions": {"en-orig": fmt("json3")}}
    code, is_auto, f = choose_track(info)
    assert (code, is_auto, f["ext"]) == ("en", False, "vtt")


def test_track_uses_original_auto_never_translation():
    info = {
        "language": "hi",
        "automatic_captions": {"af": fmt("json3"), "hi-orig": fmt("json3"), "hi": fmt("json3"), "en": fmt("json3")},
    }
    code, is_auto, _ = choose_track(info)
    assert (code, is_auto) == ("hi", True)


def test_track_none_when_empty():
    assert choose_track({}) is None


def test_track_respects_lang_request():
    info = {"subtitles": {"en": fmt("vtt"), "ta": fmt("json3")}}
    assert choose_track(info, "ta")[0] == "ta"
