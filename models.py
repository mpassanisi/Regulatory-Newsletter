"""Structures de données partagées par tout le pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    """Un article brut, quelle que soit sa source. RSS ou scraping produisent
    cet objet identique : le reste du pipeline reste agnostique de l'origine."""
    source_id: str
    title: str
    url: str
    text: str = ""
    published: datetime | None = None


@dataclass
class Deal:
    """Une levée de fonds qualifiée par le LLM, prête à stocker/publier."""
    url: str
    societe: str | None
    montant: str | None
    stade: str | None
    investisseurs: list[str] = field(default_factory=list)
    resume: str = ""
    source: str = ""
    published: datetime | None = None
    confiance: float = 0.0

    @classmethod
    def from_classification(cls, item: RawItem, c: dict) -> "Deal":
        return cls(
            url=item.url,
            societe=c.get("societe"),
            montant=c.get("montant"),
            stade=c.get("stade"),
            investisseurs=c.get("investisseurs") or [],
            resume=c.get("resume", ""),
            source=item.source_id,
            published=item.published,
            confiance=float(c.get("confiance", 0.0)),
        )
