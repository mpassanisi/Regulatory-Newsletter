"""Paramètres centraux du pipeline. Ajuste ici sans toucher au reste."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).parent

# --- Base de données --------------------------------------------------
# En local : SQLite (fichier). En ligne (Render) : Postgres via DATABASE_URL.
# Render fournit DATABASE_URL automatiquement quand une base est liée.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'deals.db'}")

# --- Modèles Claude ---------------------------------------------------
CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "claude-haiku-4-5-20251001")

# --- Seuils de filtrage ----------------------------------------------
MIN_CONFIANCE = float(os.environ.get("MIN_CONFIANCE", "0.6"))
DEDUP_THRESHOLD = int(os.environ.get("DEDUP_THRESHOLD", "88"))  # 0-100
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "14"))
MAX_TEXT_CHARS = int(os.environ.get("MAX_TEXT_CHARS", "1500"))

# --- Fichiers ---------------------------------------------------------
SOURCES_PATH = ROOT / "sources.yaml"

# --- Réseau -----------------------------------------------------------
HTTP_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (compatible; VeilleBiotechBot/1.0; "
    "veille interne levées de fonds)"
)
REQUEST_DELAY = 1.0  # secondes entre deux requêtes de scraping (politesse)


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
