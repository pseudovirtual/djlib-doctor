from __future__ import annotations

from pathlib import Path
import re


def normalize_text(value: str | None) -> str:
    text = (value or "").casefold()
    text = text.replace("&amp;", "&")
    text = re.sub(r"\b(feat|ft|featuring)\b", " ", text)
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.sub(r"\b(radio edit|extended mix|original mix|snippet|free download)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem_key(path: str) -> str:
    stem = Path(path).stem
    stem = re.sub(r"^\d+\s*", "", stem)
    stem = re.sub(r"_old$", "", stem)
    stem = re.sub(r"\.original-[^.]+$", "", stem)
    return normalize_text(stem)
