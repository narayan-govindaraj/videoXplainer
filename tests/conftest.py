import pytest

from videoxplainer.model import Segment, Transcript


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEOXPLAINER_HOME", str(tmp_path))
    return tmp_path


def make_transcript(video_id="abcdefghijk", title="Demo", texts=None):
    texts = texts or ["first point about pricing", "second point about hiring"]
    return Transcript(
        video_id=video_id,
        title=title,
        channel="Chan",
        duration=120,
        language="en",
        segments=[Segment(float(i * 5), t) for i, t in enumerate(texts)],
    )
