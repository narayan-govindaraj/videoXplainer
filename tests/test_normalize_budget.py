from videoxplainer.budget import estimate_tokens, fit
from videoxplainer.model import Paragraph, Segment
from videoxplainer.normalize import clean_text, dedupe_rolling, merge_paragraphs, normalize


def S(*pairs):
    return [Segment(t, x) for t, x in pairs]


def test_clean_noise_and_fillers():
    assert clean_text("[Music] so um we start uh now \u266a") == "so we start now"
    assert clean_text(">> Hello &amp; welcome") == "Hello & welcome"


def test_clean_keeps_real_brackets_and_words():
    assert clean_text("see section [1] under the umbrella") == "see section [1] under the umbrella"


def test_dedupe_rolling_captions():
    segs = S((0, "we are going to talk"), (2, "going to talk about pricing"), (4, "about pricing today folks"))
    out = dedupe_rolling(segs)
    assert " ".join(s.text for s in out) == "we are going to talk about pricing today folks"


def test_dedupe_drops_exact_repeat_but_keeps_single_word_repeats():
    assert len(dedupe_rolling(S((0, "this is the end"), (1, "this is the end")))) == 1
    assert len(dedupe_rolling(S((0, "yes"), (1, "yes")))) == 2


def test_paragraphs_split_on_pause():
    paras = merge_paragraphs(S((0, "one."), (1, "two."), (10, "three.")))
    assert [(p.start, p.text) for p in paras] == [(0, "one. two."), (10, "three.")]


def test_normalize_pipeline_shrinks_autocaptions():
    raw = S((0, "[Music]"), (1, "so um the key idea"), (3, "the key idea is simple"))
    segs, paras = normalize(raw)
    assert paras[0].text == "so the key idea is simple"
    assert len(segs) == 2


def _doc(n_paras=60):
    return [
        Paragraph(i * 30.0, f"Section {i} covers topic{i} in detail. Remember keyword{i} because keyword{i} drives results. "
                  + "filler words here " * 12)
        for i in range(n_paras)
    ]


def test_fit_noop_when_under_budget():
    paras = _doc(2)
    kept, stats = fit(paras, 10_000)
    assert kept == paras and stats["trimmed"] is False


def test_fit_respects_budget_keeps_order_and_covers_timeline():
    paras = _doc()
    kept, stats = fit(paras, 600)
    assert stats["trimmed"] and stats["kept_tokens"] <= 600 < stats["full_tokens"]
    starts = [p.start for p in kept]
    assert starts == sorted(starts)
    assert starts[0] < 300 and starts[-1] > 1500  # early and late parts both present


def test_fit_zero_budget_means_unlimited():
    paras = _doc()
    assert fit(paras, 0)[0] == paras


def test_estimate_tokens():
    assert estimate_tokens("") == 0 and estimate_tokens("abcd") == 1


def test_fit_never_selects_tiny_fragments():
    paras = _doc()
    paras.insert(10, Paragraph(299.0, "the"))
    paras.insert(20, Paragraph(599.0, "that went viral"))
    kept, stats = fit(paras, 600)
    assert stats["trimmed"]
    assert all(len(p.text.split()) >= 8 for p in kept)
