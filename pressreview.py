"""Revue de presse PDF -> levées biotech/pharma belges.

Entrée OPTIONNELLE et indépendante du cron : on dépose un PDF via /upload,
on en extrait le texte, on demande à Claude d'y repérer TOUTES les levées
de fonds biotech/pharma belges, et on les range comme des deals normaux.
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime

import anthropic
import pdfplumber

import config
from models import Deal

client = anthropic.Anthropic()

CHUNK_SIZE = 45000
CHUNK_OVERLAP = 500

SYSTEM = (
    "Tu es un analyste de veille biotech/pharma. Le texte fourni est un "
    "extrait de revue de presse contenant de nombreux articles. Repère "
    "UNIQUEMENT les véritables levées de fonds (tours de financement : seed, "
    "série A/B/C, IPO, dette) concernant des sociétés biotech, pharma ou "
    "sciences du vivant (thérapeutique, medtech, diagnostic, santé) basées en "
    "Wallonie ou en Belgique. Ignore tout le reste (autres secteurs, autres "
    "pays, acquisitions, subventions, partenariats, actualités générales). "
    "S'il n'y a aucune levée qualifiante, renvoie une liste vide."
)

TOOL = {
    "name": "enregistrer_levees",
    "description": "Enregistre la liste des levées de fonds trouvées.",
    "input_schema": {
        "type": "object",
        "properties": {
            "levees": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "societe": {"type": "string"},
                        "montant": {"type": ["string", "null"]},
                        "stade": {"type": ["string", "null"]},
                        "investisseurs": {"type": "array",
                                          "items": {"type": "string"}},
                        "resume": {"type": "string"},
                        "confiance": {"type": "number"},
                    },
                    "required": ["societe", "resume", "confiance", "investisseurs"],
                },
            }
        },
        "required": ["levees"],
    },
}


def extract_text(pdf_bytes: bytes) -> str:
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            out.append(page.extract_text() or "")
    return "\n".join(out)


def _chunks(text: str):
    i = 0
    while i < len(text):
        yield text[i:i + CHUNK_SIZE]
        i += CHUNK_SIZE - CHUNK_OVERLAP


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def _extract_chunk(text: str) -> list[dict]:
    try:
        msg = client.messages.create(
            model=config.CLASSIFY_MODEL,
            max_tokens=1500,
            system=SYSTEM,
            tools=[TOOL],
            tool_choice={"type": "tool", "name": "enregistrer_levees"},
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.AnthropicError as exc:
        print(f"  [!] extraction revue échouée ({exc})")
        return []
    for block in msg.content:
        if block.type == "tool_use":
            return block.input.get("levees", [])
    return []


def deals_from_pdf(pdf_bytes: bytes) -> list[Deal]:
    text = extract_text(pdf_bytes)
    today = datetime.utcnow()
    stamp = today.date().isoformat()

    raw: list[dict] = []
    for chunk in _chunks(text):
        raw.extend(_extract_chunk(chunk))

    seen: set[str] = set()
    deals: list[Deal] = []
    for x in raw:
        if float(x.get("confiance", 0)) < config.MIN_CONFIANCE:
            continue
        key = _slug(x.get("societe", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        deals.append(
            Deal(
                url=f"revue-presse:{stamp}:{key}",
                societe=x.get("societe"),
                montant=x.get("montant"),
                stade=x.get("stade"),
                investisseurs=x.get("investisseurs") or [],
                resume=x.get("resume", ""),
                source="revue-presse",
                published=today,
                confiance=float(x.get("confiance", 0)),
            )
        )
    return deals
