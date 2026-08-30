"""Étage 3b : classification LLM — le cœur du système.

On demande à Claude de trancher : vraie levée de fonds ? acteur wallon/belge ?
montant, stade, investisseurs ? Le *tool use* garantit une sortie JSON structurée.
"""
from __future__ import annotations

import anthropic

import config
from models import RawItem

client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY dans l'environnement

SYSTEM = (
    "Tu es un analyste de veille spécialisé en biotech et pharma. "
    "Pour chaque article, détermine trois choses : "
    "(1) s'il s'agit d'une véritable levée de fonds (tour de financement : "
    "seed, série A/B/C, IPO, dette, etc.), et non d'une acquisition, d'une "
    "subvention générique ou d'un simple partenariat ; "
    "(2) si la société financée est basée en Wallonie ou en Belgique ; "
    "(3) si la société relève bien du secteur biotech, pharma, ou des "
    "sciences du vivant (thérapeutique, medtech, diagnostic, santé) — et "
    "NON d'un autre secteur (logiciel généraliste, industrie, immobilier, "
    "commerce, etc.). Appelle toujours l'outil enregistrer_analyse."
)

TOOL = {
    "name": "enregistrer_analyse",
    "description": "Enregistre l'analyse structurée de l'article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "est_levee_de_fonds": {"type": "boolean"},
            "societe": {"type": ["string", "null"]},
            "est_wallon_ou_belge": {"type": "boolean"},
            "montant": {"type": ["string", "null"],
                        "description": "ex : '50 M€', '4 millions EUR'"},
            "stade": {"type": ["string", "null"],
                      "description": "seed, série A/B/C, IPO, dette..."},
            "investisseurs": {"type": "array", "items": {"type": "string"}},
            "resume": {"type": "string",
                       "description": "Une phrase factuelle en français."},
            "confiance": {"type": "number", "description": "Entre 0 et 1."},
        },
        "required": [
            "est_levee_de_fonds", "est_wallon_ou_belge",
            "investisseurs", "resume", "confiance",
            "est_biotech_ou_pharma": {"type": "boolean"},
        ],
    },
}


def classify(item: RawItem) -> dict | None:
    """Renvoie le dict d'analyse, ou None si l'appel échoue."""
    contenu = (
        f"Titre : {item.title}\n\n"
        f"Texte : {item.text[: config.MAX_TEXT_CHARS]}\n\n"
        f"URL : {item.url}"
    )
    try:
        msg = client.messages.create(
            model=config.CLASSIFY_MODEL,
            max_tokens=600,
            system=SYSTEM,
            tools=[TOOL],
            tool_choice={"type": "tool", "name": "enregistrer_analyse"},
            messages=[{"role": "user", "content": contenu}],
        )
    except anthropic.AnthropicError as exc:
        print(f"  [!] classification échouée ({exc})")
        return None

    for block in msg.content:
        if block.type == "tool_use":
            return block.input
    return None


def keep(analysis: dict) -> bool:
    """Filtre final : vraie levée + acteur belge/wallon + confiance suffisante."""
    return (
        bool(analysis.get("est_levee_de_fonds"))
        and bool(analysis.get("est_wallon_ou_belge"))
        and float(analysis.get("confiance", 0)) >= config.MIN_CONFIANCE
    )
