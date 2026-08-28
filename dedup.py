"""Étage 3a : déduplication. Le même deal apparaît sur plusieurs sources."""
from __future__ import annotations

from rapidfuzz import fuzz

import config
from models import RawItem


def deduplicate(items: list[RawItem]) -> list[RawItem]:
    """Élimine les doublons intra-collecte : URL exacte, puis titre similaire."""
    seen_urls: set[str] = set()
    kept: list[RawItem] = []
    kept_titles: list[str] = []

    for item in items:
        if not item.title:
            continue
        url_key = item.url.rstrip("/").lower()
        if url_key in seen_urls:
            continue
        if _is_fuzzy_duplicate(item.title, kept_titles):
            continue
        seen_urls.add(url_key)
        kept.append(item)
        kept_titles.append(item.title)

    return kept


def _is_fuzzy_duplicate(title: str, existing: list[str]) -> bool:
    return any(
        fuzz.token_sort_ratio(title, t) > config.DEDUP_THRESHOLD
        for t in existing
    )
