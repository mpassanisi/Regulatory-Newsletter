"""Étage 4 : stockage.

Une seule couche pour deux mondes :
  - en local  -> SQLite (fichier deals.db)
  - sur Render -> PostgreSQL (via DATABASE_URL)
SQLAlchemy gère les deux dialectes ; le reste du code ne voit qu'un "engine".

La base sert aussi de mémoire : on ne republie pas un deal déjà diffusé,
et le job planifié (écriture) et la page web (lecture) partagent ces données.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import (
    Column, DateTime, Float, Integer, MetaData, String, Table, Text,
    create_engine, insert, select, update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

import config
from models import Deal

metadata = MetaData()

deals_table = Table(
    "deals", metadata,
    Column("url", String(1024), primary_key=True),
    Column("societe", String(512)),
    Column("montant", String(128)),
    Column("stade", String(128)),
    Column("investisseurs", Text),
    Column("resume", Text),
    Column("source", String(128)),
    Column("published", DateTime),
    Column("confiance", Float),
    Column("collected_at", DateTime),
    Column("sent", Integer, default=0),
)


def _normalize_url(url: str) -> str:
    """Render fournit parfois 'postgres://' ; SQLAlchemy veut 'postgresql+psycopg://'."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def connect() -> Engine:
    engine = create_engine(_normalize_url(config.DATABASE_URL))
    metadata.create_all(engine)
    return engine


def already_known(engine: Engine, url: str) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            select(deals_table.c.url).where(deals_table.c.url == url)
        ).first()
    return row is not None


def save_deal(engine: Engine, deal: Deal) -> None:
    stmt = insert(deals_table).values(
        url=deal.url,
        societe=deal.societe,
        montant=deal.montant,
        stade=deal.stade,
        investisseurs=", ".join(deal.investisseurs),
        resume=deal.resume,
        source=deal.source,
        published=deal.published,
        confiance=deal.confiance,
        collected_at=datetime.utcnow(),
        sent=0,
    )
    try:
        with engine.begin() as conn:
            conn.execute(stmt)
    except IntegrityError:
        pass  # déjà présent (clé primaire url) — on ignore


def _rows_to_deals(rows) -> list[Deal]:
    deals = []
    for r in rows:
        deals.append(
            Deal(
                url=r.url, societe=r.societe, montant=r.montant, stade=r.stade,
                investisseurs=r.investisseurs.split(", ") if r.investisseurs else [],
                resume=r.resume or "", source=r.source or "",
                published=r.published, confiance=r.confiance or 0.0,
            )
        )
    return deals

def recent_deals(engine: Engine, days: int = 7) -> list[Deal]:
    """Deals collectés sur les N derniers jours — le contenu d'une édition."""
    since = datetime.utcnow() - timedelta(days=days)
    with engine.connect() as conn:
        rows = conn.execute(
            select(deals_table)
            .where(deals_table.c.collected_at >= since)
            .order_by(deals_table.c.collected_at.desc())
        ).fetchall()
    return _rows_to_deals(rows)

def unsent_deals(engine: Engine) -> list[Deal]:
    """Deals pas encore diffusés — le contenu de la prochaine édition."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(deals_table)
            .where(deals_table.c.sent == 0)
            .order_by(deals_table.c.collected_at.desc())
        ).fetchall()
    return _rows_to_deals(rows)


def all_deals(engine: Engine, limit: int = 200) -> list[Deal]:
    """Tous les deals récents — pour l'affichage web."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(deals_table)
            .order_by(deals_table.c.collected_at.desc())
            .limit(limit)
        ).fetchall()
    return _rows_to_deals(rows)


def mark_sent(engine: Engine, urls: list[str]) -> None:
    if not urls:
        return
    with engine.begin() as conn:
        conn.execute(
            update(deals_table)
            .where(deals_table.c.url.in_(urls))
            .values(sent=1)
        )
