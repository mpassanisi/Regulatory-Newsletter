"""Étage 1-2 : collecte des sources et normalisation en RawItem."""
from __future__ import annotations

import time
from datetime import datetime
from urllib.parse import urljoin

import feedparser
import httpx
from selectolax.parser import HTMLParser

import config
from models import RawItem


def collect_rss(src: dict) -> list[RawItem]:
    """Collecte via flux RSS/Atom — la voie fiable."""
    feed = feedparser.parse(src["url"])
    items: list[RawItem] = []
    for e in feed.entries:
        published = None
        if getattr(e, "published_parsed", None):
            published = datetime(*e.published_parsed[:6])
        items.append(
            RawItem(
                source_id=src["id"],
                title=getattr(e, "title", "").strip(),
                url=getattr(e, "link", ""),
                text=getattr(e, "summary", ""),
                published=published,
            )
        )
    return items


def collect_scrape(src: dict) -> list[RawItem]:
    """Collecte via scraping HTML — plan B pour les sites sans flux."""
    try:
        resp = httpx.get(
            src["url"],
            timeout=config.HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": config.USER_AGENT},
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"  [!] {src['id']} : échec HTTP ({exc})")
        return []

    tree = HTMLParser(resp.text)
    items: list[RawItem] = []
    for node in tree.css(src["item_selector"]):
        title_node = node.css_first(src["title_selector"])
        link_node = node.css_first(src["link_selector"])
        if not title_node or not link_node:
            continue
        href = link_node.attributes.get("href", "") or ""
        items.append(
            RawItem(
                source_id=src["id"],
                title=title_node.text(strip=True),
                url=urljoin(src["url"], href),
                text=node.text(strip=True)[: config.MAX_TEXT_CHARS],
                published=None,
            )
        )
    return items


def collect_all(sources: list[dict]) -> list[RawItem]:
    """Boucle sur toutes les sources et agrège les RawItem."""
    all_items: list[RawItem] = []
    for src in sources:
        kind = src.get("type")
        print(f"→ Collecte {src['id']} ({kind})")
        try:
            if kind == "rss":
                items = collect_rss(src)
            elif kind == "scrape":
                items = collect_scrape(src)
                time.sleep(config.REQUEST_DELAY)
            else:
                print(f"  [!] type inconnu : {kind}")
                items = []
        except Exception as exc:
            print(f"  [!] {src['id']} : erreur ({exc})")
            items = []
        print(f"  {len(items)} items")
        all_items.extend(items)
    return all_items
