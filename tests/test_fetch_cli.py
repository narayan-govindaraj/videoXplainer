import json
import os
import subprocess
import sys

import pytest

from conftest import make_transcript
from videoxplainer import cli
from videoxplainer.fetch import FetchError, classify_error, fetch_transcript
from videoxplainer.store import Store

JSON3 = json.dumps({"events": [{"tStartMs": 0, "segs": [{"utf8": "buy low sell high"}]}]})


class FakeYDL:
    def __init__(self, opts, info=None, payload=JSON3, boom=None):
        self.opts, self._info, self._payload, self._boom = opts, info, payload, boom

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        if self._boom:
            raise Exception(self._boom)
        return self._info

    def urlopen(self, url):
        payload = self._payload

        class R:
            def read(self_inner):
                return payload.encode()

        return R()


def factory(**kw):
    return lambda opts: FakeYDL(opts, **kw)


INFO = {"title": "T", "uploader": "U", "duration": 9, "language": "en",
        "subtitles": {"en": [{"ext": "json3", "url": "http://x"}]}}


def test_fetch_happy_path():
    tr = fetch_transcript("dQw4w9WgXcQ", ydl_factory=factory(info=INFO))
    assert tr.title == "T" and tr.segments[0].text == "buy low sell high" and not tr.is_auto


def test_fetch_no_captions_and_invalid():
    with pytest.raises(FetchError) as e:
        fetch_transcript("dQw4w9WgXcQ", ydl_factory=factory(info={"title": "x"}))
    assert e.value.code == "no_captions"
    with pytest.raises(FetchError) as e:
        fetch_transcript("nope")
    assert e.value.code == "invalid_input"


@pytest.mark.parametrize(
    "msg,code",
    [
        ("Sign in to confirm you're not a bot", "bot_check"),
        ("Private video. Sign in if you've been granted access", "private"),
        ("HTTP Error 429: Too Many Requests", "rate_limited"),
        ("Video unavailable", "unavailable"),
        ("<urlopen error [Errno -2] Name or service not known>", "network"),
        ("something odd", "error"),
    ],
)
def test_classify(msg, code):
    assert classify_error(msg).code == code


def test_cli_end_to_end(home, monkeypatch, capsys):
    calls = []

    def fake(target, lang, cb, cf):
        calls.append(target)
        return make_transcript(video_id="dQw4w9WgXcQ", texts=["email ten customers every week", "track churn weekly"])

    monkeypatch.setattr(cli, "fetch_transcript", fake)
    assert cli.main(["fetch", "dQw4w9WgXcQ", "--mode", "actions"]) == 0
    out = capsys.readouterr().out
    assert "email ten customers" in out and "TASK" in out
    cli.main(["fetch", "dQw4w9WgXcQ"])  # second call is served from the library
    assert len(calls) == 1
    capsys.readouterr()
    assert cli.main(["search", "churn"]) == 0
    assert "dQw4w9WgXcQ" in capsys.readouterr().out
    claims = home / "c.json"
    claims.write_text(json.dumps({"actions": [{"action": "a", "quote": "email ten customers every week"}]}))
    assert cli.main(["verify", "dQw4w9WgXcQ", str(claims), "--strict"]) == 0


def test_cli_friendly_error(home, monkeypatch, capsys):
    def boom(*a):
        raise FetchError("bot_check", "raw")

    monkeypatch.setattr(cli, "fetch_transcript", boom)
    assert cli.main(["fetch", "dQw4w9WgXcQ"]) == 3
    assert "cookies-from-browser firefox" in capsys.readouterr().err


def test_cli_rejects_bad_input(home, capsys):
    assert cli.main(["fetch", "not a link"]) == 2


def test_stdout_is_utf8_even_under_legacy_codepage(home):
    """Windows consoles default to cp1252; non-Latin captions must still print."""
    s = Store()
    s.save(make_transcript(video_id="dQw4w9WgXcQ", texts=["\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd \u0928\u092e\u0938\u094d\u0924\u0947 growth tips"]))
    s.close()
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")  # works without installing
    env = dict(os.environ, VIDEOXPLAINER_HOME=str(home), PYTHONIOENCODING="cp1252", PYTHONPATH=src)
    proc = subprocess.run([sys.executable, "-m", "videoxplainer", "fetch", "dQw4w9WgXcQ"], env=env, capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert "\u0bb5\u0ba3\u0b95\u0bcd\u0b95\u0bae\u0bcd" in proc.stdout.decode("utf-8")
