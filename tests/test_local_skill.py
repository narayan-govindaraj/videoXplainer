import json

import pytest

from videoxplainer import cli
from videoxplainer.fetch import FetchError
from videoxplainer.localfile import load_local, parse_text
from videoxplainer.store import Store

SRT = "1\n00:00:01,000 --> 00:00:04,000\nWelcome to the weekly sync\n\n2\n00:01:30,500 --> 00:01:34,000\nLet us review the launch checklist today\n"
VTT = "WEBVTT\n\n00:00:02.000 --> 00:00:05.000\n<v Dana>Revenue grew twelve percent</v>\n\n00:02:00.000 --> 00:02:03.000\nHiring plan is on track\n"
TIMED = "[00:00:05] Welcome everyone to the call\n[00:01:10] Next we discuss pricing changes\ncarried over onto a second line\n0:02:30 Final thoughts on hiring\n"
UNTIMED = "First paragraph of the talk about growth and churn in detail.\n\nSecond paragraph about hiring plans and onboarding.\n\nThird paragraph about pricing and packaging decisions.\n"


def write(tmp, name, text, encoding="utf-8"):
    p = tmp / name
    p.write_bytes(text.encode(encoding))
    return str(p)


def test_srt_and_vtt(tmp_path):
    srt = load_local(write(tmp_path, "weekly sync.srt", SRT))
    assert srt.title == "weekly sync" and srt.is_local and srt.url == "" and not srt.timestamps_estimated
    assert [(s.start, s.text) for s in srt.segments] == [(1.0, "Welcome to the weekly sync"), (90.5, "Let us review the launch checklist today")]
    vtt = load_local(write(tmp_path, "call.vtt", VTT))
    assert vtt.segments[0].text == "Revenue grew twelve percent" and vtt.segments[1].start == 120.0


def test_text_with_and_without_timestamps():
    segs, timed = parse_text(TIMED)
    assert timed and [s.start for s in segs] == [5.0, 70.0, 150.0]
    assert segs[1].text == "Next we discuss pricing changes carried over onto a second line"
    segs, timed = parse_text(UNTIMED)
    assert not timed and len(segs) == 3 and segs[0].start == 0.0 and segs[1].start > 0 and segs[2].start > segs[1].start


def test_encodings_and_scripts(tmp_path):
    ta = "\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd \u0ba8\u0ba3\u0bcd\u0baa\u0bb0\u0bcd\u0b95\u0bb3\u0bc7 \u0b87\u0ba9\u0bcd\u0bb1\u0bc1 \u0baa\u0bc7\u0b9a\u0bc1\u0bb5\u0bcb\u0bae\u0bcd"
    for enc in ("utf-8", "utf-8-sig", "utf-16"):
        assert load_local(write(tmp_path, f"{enc}.txt", ta, enc)).segments[0].text == ta
    assert load_local(write(tmp_path, "latin.txt", "caf\u00e9 meeting notes today", "cp1252")).segments[0].text == "caf\u00e9 meeting notes today"


def test_json3_and_errors(tmp_path):
    j = json.dumps({"events": [{"tStartMs": 2000, "segs": [{"utf8": "hello there"}]}]})
    assert load_local(write(tmp_path, "c.json3", j)).segments[0].start == 2.0
    for bad, code in [(write(tmp_path, "x.json", "{not json"), "invalid_input"), (write(tmp_path, "x.pdf", "x"), "invalid_input"),
                      (write(tmp_path, "empty.txt", "  \n \n"), "no_captions"), (str(tmp_path / "missing.srt"), "invalid_input")]:
        with pytest.raises(FetchError) as e:
            load_local(bad)
        assert e.value.code == code


def test_same_content_same_id(tmp_path):
    a = load_local(write(tmp_path, "a.txt", UNTIMED)).video_id
    b = load_local(write(tmp_path, "b.txt", UNTIMED)).video_id
    c = load_local(write(tmp_path, "c.txt", UNTIMED + "more")).video_id
    assert a == b != c and a.startswith("local-")


def test_cli_with_local_file_end_to_end(home, tmp_path, capsys):
    f = write(tmp_path, "sync.txt", UNTIMED)
    assert cli.main(["fetch", f, "--mode", "actions"]) == 0
    out = capsys.readouterr().out
    assert "source: local transcript file" in out and "estimated from word count" in out and "youtu.be" not in out
    claims = tmp_path / "c.json"
    claims.write_text(json.dumps({"actions": [{"action": "a", "quote": "Second paragraph about hiring plans and onboarding"}]}))
    assert cli.main(["verify", f, str(claims), "--strict"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["supported"] == 1 and "link" not in report["items"][0]
    assert cli.main(["check", f]) == 1  # only 3 paragraphs: the "captions parsed" check demands 5+ cues
    assert "FAIL  captions parsed" in capsys.readouterr().out
    assert cli.main(["fetch", str(tmp_path / "nope.srt")]) == 2
    s = Store()
    assert s.search("churn") and s.search("churn")[0]["video_id"].startswith("local-")
    s.close()
    tr = Store().load(load_local(f).video_id)
    assert tr.is_local and tr.timestamps_estimated


def test_install_skill(tmp_path, capsys):
    d = tmp_path / "skills"
    assert cli.main(["install-skill", "--dir", str(d)]) == 0
    dest = d / "videoxplainer" / "SKILL.md"
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("---\nname: videoxplainer") and "allowed-tools" in text
    capsys.readouterr()
    assert cli.main(["install-skill", "--dir", str(d)]) == 0 and "already installed" in capsys.readouterr().out
    dest.write_text("local edits", encoding="utf-8")
    assert cli.main(["install-skill", "--dir", str(d)]) == 1 and dest.read_text(encoding="utf-8") == "local edits"
    assert cli.main(["install-skill", "--dir", str(d), "--force"]) == 0 and dest.read_text(encoding="utf-8") == text
    capsys.readouterr()
    assert cli.main(["install-skill", "--print"]) == 0 and capsys.readouterr().out == text
