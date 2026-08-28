"""Étage 5 : rendu de l'édition en HTML (email) et texte (LinkedIn)."""
from __future__ import annotations

from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from models import Deal

_env = Environment(
    loader=FileSystemLoader(config.ROOT / "templates"),
    autoescape=select_autoescape(["html", "j2"]),
)


def render_html(deals: list[Deal]) -> str:
    template = _env.get_template("newsletter.html.j2")
    return template.render(deals=deals, date=date.today().strftime("%d/%m/%Y"))


def render_linkedin(deals: list[Deal]) -> str:
    """Texte prêt à copier-coller dans l'éditeur LinkedIn."""
    today = date.today().strftime("%d/%m/%Y")
    lines = [
        f"📊 Levées de fonds biotech & pharma — écosystème wallon & belge ({today})",
        "",
    ]
    if not deals:
        lines.append("Semaine calme : aucune levée détectée dans l'écosystème suivi.")
    else:
        for d in deals:
            montant = f" — {d.montant}" if d.montant else ""
            lines.append(f"🔹 {d.societe or 'Société'}{montant}")
            lines.append(f"   {d.resume}")
            if d.stade:
                lines.append(f"   Stade : {d.stade}")
            if d.investisseurs:
                lines.append(f"   Investisseurs : {', '.join(d.investisseurs)}")
            lines.append("")
    lines.append("#biotech #pharma #Wallonie #venturecapital #lifesciences")
    return "\n".join(lines)
