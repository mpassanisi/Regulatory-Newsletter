from __future__ import annotations
from datetime import date
from jinja2 import Environment, FileSystemLoader, select_autoescape
import config
from models import Deal

_env = Environment(loader=FileSystemLoader(config.ROOT / "templates"),
                   autoescape=select_autoescape(["html", "j2"]))

def render_html(deals):
    return _env.get_template("newsletter.html.j2").render(
        deals=deals, date=date.today().strftime("%d/%m/%Y"))

def render_linkedin(deals) -> str:
    today = date.today().strftime("%d/%m/%Y")
    n = len(deals)
    lines = [f"🚀 What's up in Wallonia? — Les levées de fonds ({today})", ""]
    if not deals:
        lines.append("Semaine calme du côté des levées de fonds wallonnes. "
                     "On revient dès qu'un nouveau tour est bouclé 👀")
        lines += ["", "#Wallonia #startup #venturecapital #Belgium"]
        return "\n".join(lines)
    intro = ("Cette semaine, une société wallonne/belge a bouclé un tour de financement 👇"
             if n == 1 else
             f"Cette semaine, {n} sociétés wallonnes/belges ont bouclé un tour de financement 👇")
    lines += [intro, ""]
    for d in deals:
        montant = f" — {d.montant}" if d.montant else ""
        lines.append(f"💰 {d.societe or 'Société'}{montant}")
        if d.resume:
            lines.append(d.resume)
        details = []
        if d.stade:
            details.append(f"Tour : {d.stade}")
        if d.investisseurs:
            details.append(f"Investisseurs : {', '.join(d.investisseurs)}")
        if details:
            lines.append("↳ " + " · ".join(details))
        lines.append("")
    lines.append("📊 Une veille automatisée de l'écosystème entrepreneurial wallon.")
    lines.append("Un deal manque ? Signalez-le en commentaire.")
    lines.append("")
    lines.append("#Wallonia #startup #venturecapital #Belgium #fundraising #scaleup")
    return "\n".join(lines)
