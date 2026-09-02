from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table, Text,
                        create_engine, func, insert, select, text, update)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
import config
from models import Deal

metadata = MetaData()
deals_table = Table("deals", metadata,
    Column("url", String(1024), primary_key=True),
    Column("societe", String(512)), Column("montant", String(128)),
    Column("stade", String(128)), Column("investisseurs", Text),
    Column("resume", Text), Column("source", String(128)),
    Column("published", DateTime), Column("confiance", Float),
    Column("collected_at", DateTime), Column("sent", Integer, default=0),
    Column("hidden", Integer, default=0))

def _normalize_url(url):
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

def _ensure_hidden_column(engine):
    # Migration : ajoute la colonne 'hidden' si elle n'existe pas encore.
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE deals ADD COLUMN hidden INTEGER DEFAULT 0"))
    except Exception:
        pass  # déjà présente

def connect() -> Engine:
    engine = create_engine(_normalize_url(config.DATABASE_URL))
    metadata.create_all(engine)
    _ensure_hidden_column(engine)
    return engine

def already_known(engine, url):
    with engine.connect() as conn:
        return conn.execute(select(deals_table.c.url).where(deals_table.c.url == url)).first() is not None

def save_deal(engine, deal):
    stmt = insert(deals_table).values(url=deal.url, societe=deal.societe,
        montant=deal.montant, stade=deal.stade,
        investisseurs=", ".join(deal.investisseurs), resume=deal.resume,
        source=deal.source, published=deal.published, confiance=deal.confiance,
        collected_at=datetime.utcnow(), sent=0, hidden=0)
    try:
        with engine.begin() as conn:
            conn.execute(stmt)
    except IntegrityError:
        pass

def _rows_to_deals(rows):
    return [Deal(url=r.url, societe=r.societe, montant=r.montant, stade=r.stade,
        investisseurs=r.investisseurs.split(", ") if r.investisseurs else [],
        resume=r.resume or "", source=r.source or "",
        published=r.published, confiance=r.confiance or 0.0) for r in rows]

_VISIBLE = func.coalesce(deals_table.c.hidden, 0) == 0

def recent_deals(engine, days=7):
    since = datetime.utcnow() - timedelta(days=days)
    with engine.connect() as conn:
        rows = conn.execute(select(deals_table).where(_VISIBLE)
            .where(deals_table.c.collected_at >= since)
            .order_by(deals_table.c.collected_at.desc())).fetchall()
    return _rows_to_deals(rows)

def all_deals(engine, limit=200):
    with engine.connect() as conn:
        rows = conn.execute(select(deals_table).where(_VISIBLE)
            .order_by(deals_table.c.collected_at.desc()).limit(limit)).fetchall()
    return _rows_to_deals(rows)

def hide_deal(engine, url):
    with engine.begin() as conn:
        conn.execute(update(deals_table).where(deals_table.c.url == url).values(hidden=1))
