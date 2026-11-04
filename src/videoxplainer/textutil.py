"""Script-agnostic word handling (works for Latin, Devanagari, Tamil, Cyrillic...)."""

from __future__ import annotations

import unicodedata
from typing import List

_APOS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})


def words(text: str) -> List[str]:
    """Lowercased words with punctuation/symbols removed.

    Splits on whitespace (so combining marks in Indic scripts stay attached to
    their letters) and treats curly and straight apostrophes the same.
    Languages written without spaces (Chinese, Japanese) are not segmented.
    """
    out: List[str] = []
    for tok in text.translate(_APOS).lower().split():
        tok = "".join(ch for ch in tok if ch == "'" or unicodedata.category(ch)[0] not in "PS").strip("'")
        if tok:
            out.append(tok)
    return out
