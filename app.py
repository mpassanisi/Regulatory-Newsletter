"""Application web : affiche les résultats en direct depuis la base partagée.

Routes :
  /            -> tableau de bord HTML des levées détectées
  /newsletter  -> la newsletter HTML de l'édition en cours (deals non diffusés)
  /linkedin    -> le texte prêt à coller dans LinkedIn (text/plain)
  /health      -> sonde de disponibilité (pour Render)

Le job planifié (pipeline.py) écrit dans la même base ; ici on ne fait que lire.
Démarrage en production : gunicorn app:app
"""
from __future__ import annotations

from datetime import date

from flask import Flask, Response, render_template

import storage
from render import render_html, render_linkedin

app = Flask(__name__)
engine = storage.connect()


@app.route("/")
def dashboard():
    deals = storage.all_deals(engine, limit=200)
    return render_template(
        "dashboard.html.j2",
        deals=deals,
        total=len(deals),
        today=date.today().strftime("%d/%m/%Y"),
    )


@app.route("/newsletter")
def newsletter():
    deals = storage.unsent_deals(engine)
    return render_html(deals)


@app.route("/linkedin")
def linkedin():
    deals = storage.unsent_deals(engine)
    return Response(render_linkedin(deals), mimetype="text/plain; charset=utf-8")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # Développement local uniquement. En prod, Render lance gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=True)
